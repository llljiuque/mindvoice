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
    
    def __init__(
        self, 
        storage_path: str = "./data/knowledge",
        embedding_model: str = "all-MiniLM-L6-v2",
        collection_name: str = "mindvoice_knowledge",
        lazy_load: bool = True
    ):
        """初始化知识库服务
        
        Args:
            storage_path: 存储路径
            embedding_model: Embedding模型名称
            collection_name: 向量数据库集合名称
            lazy_load: 是否延迟加载模型（默认True，启动时不加载模型）
        """
        self.storage_path = Path(storage_path)
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
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        logger.info(f"[KnowledgeService] Embedding 模型加载完成")
    
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
        
        chunks = []
        start = 0
        
        while start < len(text):
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
            start = end - chunk_overlap if end < len(text) else end
        
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
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 文本分块
        chunks = self._chunk_text(content)
        logger.info(f"[KnowledgeService] 文件 {filename} 分成 {len(chunks)} 块")
        
        # 生成向量（在线程池中执行，避免阻塞）
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self.embedding_model.encode(chunks, show_progress_bar=False).tolist()
        )
        
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
        self.collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=chunk_metadata
        )
        
        logger.info(f"[KnowledgeService] 文件 {filename} 上传成功，ID: {file_id}")
        
        return {
            'file_id': file_id,
            'filename': filename,
            'chunks': len(chunks),
            'size': len(content),
            'path': str(file_path)
        }
    
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
            是否可用（包括模型已加载或正在加载）
        """
        return (SENTENCE_TRANSFORMERS_AVAILABLE and 
                CHROMADB_AVAILABLE and 
                self.collection is not None and
                (self.embedding_model is not None or self._model_loading))
    
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

