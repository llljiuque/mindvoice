"""
知识库服务 - 轻量级 RAG 实现

不使用 LangChain，基于：
- sentence-transformers: 文本向量化
- chromadb: 向量数据库
- 自定义文本分块逻辑
"""
import os
import uuid
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

# 条件导入（如果未安装这些包，会给出友好提示）
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


logger = logging.getLogger(__name__)


class KnowledgeService:
    """知识库服务
    
    功能：
    - 上传文件（.md, .txt）
    - 自动文本分块
    - 向量化存储
    - 语义检索
    - 文件管理（列表/删除/获取）
    """
    
    DEFAULT_CHUNK_SIZE = 500  # 默认分块大小（字符数）
    DEFAULT_CHUNK_OVERLAP = 50  # 默认分块重叠（字符数）
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 最大文件大小：10MB
    
    def __init__(
        self, 
        data_dir: Path,
        knowledge_relative_path: Path,
        embedding_model: str = "all-MiniLM-L6-v2",
        collection_name: str = "mindvoice_knowledge",
        lazy_load: bool = True
    ):
        """初始化知识库服务
        
        Args:
            data_dir: 数据根目录（从配置读取）
            knowledge_relative_path: 知识库相对路径（从配置读取）
            embedding_model: Embedding模型名称
            collection_name: 向量数据库集合名称
            lazy_load: 是否延迟加载模型（默认True，启动时不加载模型）
        """
        self.data_dir = data_dir
        self.knowledge_relative_path = knowledge_relative_path
        self.storage_path = self.data_dir / self.knowledge_relative_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        self.lazy_load = lazy_load
        
        # 检查依赖
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers 未安装。请运行: pip install sentence-transformers"
            )
        
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "chromadb 未安装。请运行: pip install chromadb"
            )
        
        # 初始化 ChromaDB（这个很快，不需要延迟）
        chroma_path = self.storage_path / "chroma"
        chroma_path.mkdir(exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 获取或创建集合
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "MindVoice 知识库"}
        )
        
        # Embedding 模型（延迟加载）
        self.embedding_model = None
        self._model_loading = False
        self._model_loaded = False
        self._load_task = None
        
        if not lazy_load:
            # 立即加载模型
            self._load_model()
            logger.info(f"[KnowledgeService] 初始化完成，集合: {collection_name}")
        else:
            logger.info(f"[KnowledgeService] 初始化完成（延迟加载模式），集合: {collection_name}")
    
    def _load_model(self):
        """加载 Embedding 模型（同步方法）"""
        if self.embedding_model is not None:
            return
        
        logger.info(f"[KnowledgeService] 开始加载 Embedding 模型: {self.embedding_model_name}")
        
        # 禁用进度条（避免在后台线程中访问 stderr 失败）
        import os
        import sys
        
        # 设置环境变量禁用进度条
        os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
        os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
        
        # 配置 HuggingFace 镜像源（如果未设置）
        # 使用国内镜像加速下载
        if not os.getenv('HF_ENDPOINT'):
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            logger.info("[KnowledgeService] 已设置 HuggingFace 镜像源: https://hf-mirror.com")
        
        # 如果设置了代理，也配置给 huggingface_hub
        if os.getenv('HTTP_PROXY') or os.getenv('HTTPS_PROXY'):
            logger.debug(f"[KnowledgeService] 检测到代理设置: HTTP_PROXY={os.getenv('HTTP_PROXY')}, HTTPS_PROXY={os.getenv('HTTPS_PROXY')}")
        
        # 临时重定向 stderr 到 devnull（避免 tqdm 访问失败）
        original_stderr = sys.stderr
        try:
            # 在 Windows 上，使用 devnull 重定向 stderr
            import io
            sys.stderr = io.StringIO()
            
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info(f"[KnowledgeService] Embedding 模型加载完成")
        except Exception as e:
            logger.error(f"[KnowledgeService] Embedding 模型加载失败: {e}", exc_info=True)
            raise
        finally:
            # 恢复 stderr
            sys.stderr = original_stderr
    
    async def _load_model_async(self):
        """异步加载 Embedding 模型"""
        if self._model_loading or self.embedding_model is not None:
            return
        
        self._model_loading = True
        try:
            # 在线程池中执行模型加载（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._load_model)
            self._model_loaded = True
            logger.info(f"[KnowledgeService] Embedding 模型后台加载完成")
        except Exception as e:
            logger.error(f"[KnowledgeService] Embedding 模型加载失败: {e}", exc_info=True)
            raise
        finally:
            self._model_loading = False
    
    async def ensure_model_loaded(self):
        """确保模型已加载（如果正在加载则等待）"""
        if self.embedding_model is not None:
            return
        
        if self._model_loading:
            # 等待正在进行的加载任务
            if self._load_task:
                await self._load_task
            return
        
        # 如果还没有开始加载，立即加载
        await self._load_model_async()
    
    def _chunk_text(
        self, 
        text: str, 
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ) -> List[str]:
        """将文本分块
        
        简单的字符级分块策略，优先在句子边界分割
        
        Args:
            text: 原始文本
            chunk_size: 块大小
            chunk_overlap: 重叠大小
            
        Returns:
            文本块列表
        """
        if len(text) <= chunk_size:
            return [text]
        
        # 确保 chunk_overlap < chunk_size，避免无限循环
        if chunk_overlap >= chunk_size:
            chunk_overlap = chunk_size // 4
        
        chunks = []
        start = 0
        max_iterations = len(text) // max(1, chunk_size - chunk_overlap) + 100  # 安全上限
        iteration_count = 0
        
        while start < len(text):
            iteration_count += 1
            if iteration_count > max_iterations:
                logger.error(f"[KnowledgeService] 分块迭代次数超过上限 ({max_iterations})，可能存在无限循环")
                raise RuntimeError(f"文本分块失败：迭代次数超过上限，可能存在无限循环")
            
            end = start + chunk_size
            
            # 如果不是最后一块，尝试在句子边界分割
            if end < len(text):
                # 查找最近的句子结束符
                for sep in ['。', '！', '？', '\n\n', '. ', '! ', '? ']:
                    last_sep = text.rfind(sep, start, end)
                    if last_sep != -1:
                        end = last_sep + len(sep)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # 下一块的起始位置（考虑重叠）
            next_start = end - chunk_overlap if end < len(text) else end
            
            # 防止无限循环：确保 start 必须前进
            if next_start <= start:
                logger.warning(f"[KnowledgeService] 检测到 start 未前进 (start={start}, next_start={next_start})，强制前进")
                next_start = start + max(1, chunk_size - chunk_overlap)
            
            start = next_start
        
        return chunks
    
    async def upload_file(
        self, 
        filename: str, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """上传文件到知识库
        
        Args:
            filename: 文件名
            content: 文件内容
            metadata: 元数据（可选）
            
        Returns:
            上传结果信息
        """
        try:
            # 检查文件大小（防止 MemoryError）
            content_size = len(content.encode('utf-8'))
            if content_size > self.MAX_FILE_SIZE:
                error_msg = f"文件大小超过限制：{content_size / 1024 / 1024:.2f}MB > {self.MAX_FILE_SIZE / 1024 / 1024}MB"
                logger.error(f"[KnowledgeService] {error_msg}")
                raise ValueError(error_msg)
            
            logger.info(f"[KnowledgeService] 开始上传文件: {filename} (大小: {content_size / 1024:.2f}KB)")
            
            # 确保模型已加载
            await self.ensure_model_loaded()
            
            # 验证文件类型
            file_ext = Path(filename).suffix.lower()
            if file_ext not in ['.md', '.txt']:
                raise ValueError(f"不支持的文件类型: {file_ext}，仅支持 .md 和 .txt")
            
            # 生成文件ID
            file_id = str(uuid.uuid4())
            
            # 保存原始文件
            file_path = self.storage_path / "files" / f"{file_id}_{filename}"
            file_path.parent.mkdir(exist_ok=True)
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.debug(f"[KnowledgeService] 文件已保存到: {file_path}")
            except Exception as e:
                logger.error(f"[KnowledgeService] 保存文件失败: {e}", exc_info=True)
                raise
            
            # 文本分块
            try:
                chunks = self._chunk_text(content)
                logger.info(f"[KnowledgeService] 文件 {filename} 分成 {len(chunks)} 块")
            except Exception as e:
                logger.error(f"[KnowledgeService] 文本分块失败: {e}", exc_info=True)
                raise
            
            # 生成向量（在线程池中执行，避免阻塞）
            try:
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    None,
                    lambda: self.embedding_model.encode(chunks, show_progress_bar=False).tolist()
                )
                logger.debug(f"[KnowledgeService] 向量生成完成，共 {len(embeddings)} 个向量")
            except MemoryError as e:
                error_msg = f"内存不足，无法处理文件 {filename}（大小: {content_size / 1024 / 1024:.2f}MB）"
                logger.error(f"[KnowledgeService] {error_msg}: {e}", exc_info=True)
                # 清理已保存的文件
                if file_path.exists():
                    file_path.unlink()
                raise MemoryError(error_msg) from e
            except Exception as e:
                logger.error(f"[KnowledgeService] 向量生成失败: {e}", exc_info=True)
                raise
            
            # 准备数据
            chunk_ids = [f"{file_id}_chunk_{i}" for i in range(len(chunks))]
            chunk_metadata = [
                {
                    'file_id': file_id,
                    'filename': filename,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    **(metadata or {})
                }
                for i in range(len(chunks))
            ]
            
            # 存储到向量数据库
            try:
                self.collection.add(
                    ids=chunk_ids,
                    embeddings=embeddings,
                    documents=chunks,
                    metadatas=chunk_metadata
                )
                logger.debug(f"[KnowledgeService] 数据已存储到向量数据库")
            except Exception as e:
                logger.error(f"[KnowledgeService] 存储到向量数据库失败: {e}", exc_info=True)
                # 清理已保存的文件
                if file_path.exists():
                    file_path.unlink()
                raise
            
            logger.info(f"[KnowledgeService] 文件 {filename} 上传成功，ID: {file_id}")
            
            return {
                'file_id': file_id,
                'filename': filename,
                'chunks': len(chunks),
                'size': len(content),
                'path': str(file_path)
            }
        except ValueError as e:
            # 重新抛出 ValueError（如文件大小超限、文件类型不支持）
            raise
        except MemoryError as e:
            # 重新抛出 MemoryError
            raise
        except Exception as e:
            # 其他异常，记录详细日志并重新抛出
            logger.error(f"[KnowledgeService] 上传文件失败: {filename}, 错误: {e}", exc_info=True)
            raise
    
    async def search(
        self, 
        query: str, 
        top_k: int = 3,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """语义搜索知识库
        
        Args:
            query: 查询文本
            top_k: 返回前K个结果
            filter_metadata: 过滤条件（可选）
            
        Returns:
            搜索结果列表
        """
        # 确保模型已加载
        await self.ensure_model_loaded()
        
        # 生成查询向量（在线程池中执行，避免阻塞）
        loop = asyncio.get_event_loop()
        query_embedding = await loop.run_in_executor(
            None,
            lambda: self.embedding_model.encode([query], show_progress_bar=False).tolist()
        )
        
        # 查询向量数据库
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where=filter_metadata
        )
        
        # 格式化结果
        formatted_results = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'score': 1 - results['distances'][0][i],  # 转换为相似度分数
                    'source': results['metadatas'][0][i].get('filename', 'unknown')
                })
        
        logger.info(f"[KnowledgeService] 搜索完成，返回 {len(formatted_results)} 个结果")
        return formatted_results
    
    async def delete_file(self, file_id: str) -> bool:
        """删除文件及其所有文本块
        
        Args:
            file_id: 文件ID
            
        Returns:
            是否删除成功
        """
        try:
            # 删除向量数据库中的所有块
            # 先查询该文件的所有块
            all_data = self.collection.get()
            chunk_ids_to_delete = [
                id for id, meta in zip(all_data['ids'], all_data['metadatas'])
                if meta.get('file_id') == file_id
            ]
            
            if chunk_ids_to_delete:
                self.collection.delete(ids=chunk_ids_to_delete)
                logger.info(f"[KnowledgeService] 删除文件 {file_id}，共 {len(chunk_ids_to_delete)} 个块")
            
            # 删除原始文件（如果存在）
            files_dir = self.storage_path / "files"
            for file_path in files_dir.glob(f"{file_id}_*"):
                file_path.unlink()
            
            return True
            
        except Exception as e:
            logger.error(f"[KnowledgeService] 删除文件失败: {e}")
            return False
    
    async def list_files(self) -> List[Dict[str, Any]]:
        """列出所有文件
        
        Returns:
            文件列表
        """
        all_data = self.collection.get()
        
        # 按 file_id 分组
        files_dict = {}
        for meta in all_data['metadatas']:
            file_id = meta.get('file_id')
            if file_id and file_id not in files_dict:
                files_dict[file_id] = {
                    'file_id': file_id,
                    'filename': meta.get('filename', 'unknown'),
                    'chunks': meta.get('total_chunks', 0),
                    'metadata': {k: v for k, v in meta.items() 
                               if k not in ['file_id', 'filename', 'chunk_index', 'total_chunks']}
                }
        
        files_list = list(files_dict.values())
        logger.info(f"[KnowledgeService] 共有 {len(files_list)} 个文件")
        return files_list
    
    async def get_file_content(self, file_id: str) -> Optional[str]:
        """获取文件原始内容
        
        Args:
            file_id: 文件ID
            
        Returns:
            文件内容，如果不存在返回None
        """
        files_dir = self.storage_path / "files"
        for file_path in files_dir.glob(f"{file_id}_*"):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        return None
    
    def is_available(self) -> bool:
        """检查服务是否可用
        
        Returns:
            是否可用（依赖已安装且集合已初始化即可，模型会在需要时自动加载）
        """
        # 在延迟加载模式下，只要依赖安装且集合初始化，就认为服务可用
        # 模型会在 upload_file/search 时通过 ensure_model_loaded() 自动加载
        return (SENTENCE_TRANSFORMERS_AVAILABLE and 
                CHROMADB_AVAILABLE and 
                self.collection is not None)
    
    def start_background_load(self):
        """在后台开始加载模型（非阻塞）
        
        返回一个任务，可以在需要时等待
        """
        if self.embedding_model is not None or self._model_loading:
            return None
        
        loop = asyncio.get_event_loop()
        self._load_task = loop.create_task(self._load_model_async())
        logger.info(f"[KnowledgeService] 已在后台开始加载 Embedding 模型")
        return self._load_task

