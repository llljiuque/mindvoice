"""
提示词加载器

提供统一的提示词加载和管理功能
"""
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PromptLoader:
    """提示词加载器
    
    功能：
    - 从YAML文件加载提示词配置
    - 验证提示词格式
    - 支持提示词变量替换
    - 缓存已加载的提示词
    """
    
    # 提示词文件目录
    PROMPTS_DIR = Path(__file__).parent
    
    # 缓存已加载的提示词
    _cache: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def load(cls, agent_name: str, variant: Optional[str] = None, use_cache: bool = True) -> Dict[str, Any]:
        """加载提示词配置
        
        Args:
            agent_name: Agent名称（不含.yml后缀）
            variant: 变体名称（可选）
            use_cache: 是否使用缓存，默认True
            
        Returns:
            提示词配置字典
            
        Raises:
            FileNotFoundError: 提示词文件不存在
            ValueError: YAML格式错误或缺少必需字段
        """
        cache_key = f"{agent_name}:{variant or 'default'}"
        
        # 检查缓存
        if use_cache and cache_key in cls._cache:
            logger.debug(f"[PromptLoader] 从缓存加载: {cache_key}")
            return cls._cache[cache_key]
        
        # 加载文件
        file_path = cls.PROMPTS_DIR / f"{agent_name}.yml"
        
        if not file_path.exists():
            raise FileNotFoundError(f"提示词文件不存在: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                raise ValueError(f"提示词文件为空: {file_path}")
            
            # 验证必需字段
            cls._validate_config(config, agent_name)
            
            # 如果指定了变体，使用变体的提示词
            if variant and 'variants' in config and variant in config['variants']:
                variant_config = config['variants'][variant]
                # 合并变体配置（变体配置覆盖默认配置）
                config = {**config, **variant_config}
                logger.info(f"[PromptLoader] 使用变体: {variant}")
            
            # 添加加载时间戳
            config['_loaded_at'] = datetime.now().isoformat()
            config['_file_path'] = str(file_path)
            
            # 缓存配置
            if use_cache:
                cls._cache[cache_key] = config
            
            logger.info(f"[PromptLoader] 加载成功: {agent_name} (version: {config['metadata']['version']})")
            return config
            
        except yaml.YAMLError as e:
            raise ValueError(f"YAML格式错误: {file_path}\n{e}")
        except Exception as e:
            logger.error(f"[PromptLoader] 加载失败: {agent_name}, 错误: {e}")
            raise
    
    @classmethod
    def _validate_config(cls, config: Dict[str, Any], agent_name: str) -> None:
        """验证配置格式
        
        Args:
            config: 配置字典
            agent_name: Agent名称
            
        Raises:
            ValueError: 缺少必需字段
        """
        # 检查必需的顶层字段
        required_fields = ['metadata', 'system_prompt']
        missing_fields = [field for field in required_fields if field not in config]
        
        if missing_fields:
            raise ValueError(f"提示词配置缺少必需字段: {missing_fields}")
        
        # 检查metadata必需字段
        required_metadata = ['name', 'version', 'description']
        missing_metadata = [field for field in required_metadata 
                           if field not in config['metadata']]
        
        if missing_metadata:
            raise ValueError(f"metadata缺少必需字段: {missing_metadata}")
        
        # 验证system_prompt不为空
        if not config['system_prompt'] or not config['system_prompt'].strip():
            raise ValueError("system_prompt不能为空")
    
    @classmethod
    def reload(cls, agent_name: str, variant: Optional[str] = None) -> Dict[str, Any]:
        """重新加载提示词（忽略缓存）
        
        Args:
            agent_name: Agent名称
            variant: 变体名称
            
        Returns:
            提示词配置字典
        """
        cache_key = f"{agent_name}:{variant or 'default'}"
        
        # 清除缓存
        if cache_key in cls._cache:
            del cls._cache[cache_key]
        
        logger.info(f"[PromptLoader] 重新加载: {cache_key}")
        return cls.load(agent_name, variant, use_cache=False)
    
    @classmethod
    def clear_cache(cls) -> None:
        """清除所有缓存"""
        cls._cache.clear()
        logger.info("[PromptLoader] 缓存已清除")
    
    @classmethod
    def list_available(cls) -> list[str]:
        """列出所有可用的提示词文件
        
        Returns:
            提示词文件名列表（不含.yml后缀）
        """
        prompt_files = cls.PROMPTS_DIR.glob("*.yml")
        return [f.stem for f in prompt_files if f.stem != 'template']
    
    @classmethod
    def get_metadata(cls, agent_name: str) -> Dict[str, Any]:
        """获取提示词元数据（不加载完整配置）
        
        Args:
            agent_name: Agent名称
            
        Returns:
            元数据字典
        """
        config = cls.load(agent_name)
        return config['metadata']
    
    @staticmethod
    def format_prompt(template: str, **variables) -> str:
        """格式化提示词模板
        
        将提示词中的变量占位符替换为实际值
        
        Args:
            template: 提示词模板（包含{var}格式的占位符）
            **variables: 变量键值对
            
        Returns:
            格式化后的提示词
            
        Example:
            >>> prompt = "你好，{name}。今天是{date}。"
            >>> PromptLoader.format_prompt(prompt, name="小明", date="2026-01-02")
            "你好，小明。今天是2026-01-02。"
        """
        try:
            return template.format(**variables)
        except KeyError as e:
            logger.warning(f"[PromptLoader] 缺少变量: {e}")
            return template
    
    @staticmethod
    def validate_file(file_path: Path) -> tuple[bool, Optional[str]]:
        """验证YAML文件格式
        
        Args:
            file_path: YAML文件路径
            
        Returns:
            (是否有效, 错误信息)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                return False, "文件为空"
            
            # 验证必需字段
            PromptLoader._validate_config(config, file_path.stem)
            
            return True, None
            
        except yaml.YAMLError as e:
            return False, f"YAML格式错误: {e}"
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            return False, f"未知错误: {e}"


class PromptTemplate:
    """提示词模板工具类
    
    提供常用的提示词模板和模式
    """
    
    @staticmethod
    def role_task_format(role: str, task: str, requirements: list[str], 
                        examples: Optional[list[str]] = None) -> str:
        """生成"角色-任务-要求-示例"格式的提示词
        
        Args:
            role: 角色描述
            task: 任务描述
            requirements: 要求列表
            examples: 示例列表（可选）
            
        Returns:
            格式化的提示词
        """
        prompt_parts = [
            f"你是{role}。你的任务是{task}。",
            "",
            "要求：",
        ]
        
        for i, req in enumerate(requirements, 1):
            prompt_parts.append(f"{i}. {req}")
        
        if examples:
            prompt_parts.extend(["", "示例："])
            for example in examples:
                prompt_parts.append(f"- {example}")
        
        prompt_parts.extend(["", "请直接输出结果，不要有其他说明。"])
        
        return "\n".join(prompt_parts)
    
    @staticmethod
    def few_shot_template(instruction: str, examples: list[tuple[str, str]], 
                         query: str = "{query}") -> str:
        """生成Few-shot学习格式的提示词
        
        Args:
            instruction: 指令说明
            examples: (输入, 输出) 元组列表
            query: 查询占位符
            
        Returns:
            Few-shot提示词模板
        """
        prompt_parts = [instruction, ""]
        
        for i, (input_ex, output_ex) in enumerate(examples, 1):
            prompt_parts.extend([
                f"示例 {i}:",
                f"输入: {input_ex}",
                f"输出: {output_ex}",
                ""
            ])
        
        prompt_parts.extend([
            "现在请处理：",
            f"输入: {query}",
            "输出:"
        ])
        
        return "\n".join(prompt_parts)

