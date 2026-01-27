"""
文件处理工具
"""
import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from src.utils.logger import get_logger


logger = get_logger("CoreMiner")


class FileHandler:
    """文件操作处理类"""
    
    @staticmethod
    def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
        """
        加载YAML配置文件
        
        Args:
            config_path: 配置文件路径
        
        Returns:
            配置字典
        """
        try:
            config_path = Path(config_path)
            if not config_path.exists():
                logger.warning(f"配置文件不存在: {config_path}")
                return {}
            
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                logger.info(f"成功加载配置文件: {config_path}")
                return config or {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    @staticmethod
    def save_json(data: Any, file_path: str, indent: int = 2) -> bool:
        """
        保存JSON文件
        
        Args:
            data: 要保存的数据
            file_path: 文件路径
            indent: JSON缩进
        
        Returns:
            是否保存成功
        """
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            logger.info(f"JSON文件已保存: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
            return False
    
    @staticmethod
    def load_json(file_path: str) -> Optional[Dict[str, Any]]:
        """
        加载JSON文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            JSON数据或None
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.warning(f"JSON文件不存在: {file_path}")
                return None
            
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                logger.info(f"JSON文件已加载: {file_path}")
                return data
        except Exception as e:
            logger.error(f"加载JSON文件失败: {e}")
            return None
    
    @staticmethod
    def save_text(content: str, file_path: str) -> bool:
        """
        保存文本文件
        
        Args:
            content: 文件内容
            file_path: 文件路径
        
        Returns:
            是否保存成功
        """
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"文本文件已保存: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存文本文件失败: {e}")
            return False
    
    @staticmethod
    def load_text(file_path: str) -> Optional[str]:
        """
        加载文本文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            文本内容或None
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.warning(f"文本文件不存在: {file_path}")
                return None
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                logger.info(f"文本文件已加载: {file_path}")
                return content
        except Exception as e:
            logger.error(f"加载文本文件失败: {e}")
            return None
    
    @staticmethod
    def ensure_dir(dir_path: str) -> Path:
        """
        确保目录存在
        
        Args:
            dir_path: 目录路径
        
        Returns:
            Path对象
        """
        dir_path = Path(dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    @staticmethod
    def get_files_by_extension(
        dir_path: str, extension: str = "*.pdf"
    ) -> list:
        """
        获取指定扩展名的所有文件
        
        Args:
            dir_path: 目录路径
            extension: 文件扩展名（如 *.pdf）
        
        Returns:
            文件路径列表
        """
        dir_path = Path(dir_path)
        if not dir_path.exists():
            logger.warning(f"目录不存在: {dir_path}")
            return []
        
        files = list(dir_path.glob(extension))
        logger.info(f"在 {dir_path} 中找到 {len(files)} 个 {extension} 文件")
        return files
