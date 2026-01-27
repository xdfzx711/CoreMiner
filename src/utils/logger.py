"""
日志配置模块
"""
import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional


class LoggerConfig:
    """日志配置类"""
    
    _loggers = {}
    _configured = False
    
    @classmethod
    def setup(
        cls,
        name: str = "CoreMiner",
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        console: bool = True,
        max_file_size: int = 10485760,  # 10MB
        backup_count: int = 5,
    ) -> logging.Logger:
        """
        设置日志配置
        
        Args:
            name: 日志记录器名称
            log_level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
            log_file: 日志文件路径
            console: 是否输出到控制台
            max_file_size: 日志文件最大大小（字节）
            backup_count: 保留的日志文件数量
        
        Returns:
            logger实例
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, log_level.upper()))
        
        # 清除已有的处理器
        logger.handlers.clear()
        
        # 日志格式
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        
        # 控制台处理器
        if console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(getattr(logging, log_level.upper()))
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # 文件处理器
        if log_file:
            log_dir = Path(log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(getattr(logging, log_level.upper()))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def get_logger(cls, name: str = "CoreMiner") -> logging.Logger:
        """获取日志记录器"""
        if name not in cls._loggers:
            return cls.setup(name=name)
        return cls._loggers[name]


def get_logger(name: str = "CoreMiner") -> logging.Logger:
    """便捷函数：获取日志记录器"""
    return LoggerConfig.get_logger(name)
