"""
数据模型
定义Step3中使用的数据结构
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class PaperContent:
    """论文内容数据模型"""
    title: str
    abstract: str
    introduction_1_3: str
    conclusion: Optional[str] = None
    
    def __post_init__(self):
        """初始化后的验证"""
        if not self.title:
            raise ValueError("论文标题不能为空")
        if not self.abstract:
            raise ValueError("摘要不能为空")
        if not self.introduction_1_3:
            raise ValueError("引言后三分之一不能为空")


@dataclass
class CoreContribution:
    """核心贡献提取结果"""
    source_file: str
    title: str
    contributions_summary: str
    extraction_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    model_used: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source_file": self.source_file,
            "title": self.title,
            "contributions_summary": self.contributions_summary,
            "extraction_timestamp": self.extraction_timestamp,
            "model_used": self.model_used,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens
        }


@dataclass
class ExtractionConfig:
    """提取配置"""
    api_key: str
    api_url: str
    model_name: str
    max_tokens: int = 2000
    temperature: float = 0.7
    
    def validate(self):
        """验证配置"""
        if not self.api_key:
            raise ValueError("API_KEY不能为空")
        if not self.api_url:
            raise ValueError("API_URL不能为空")
        if not self.model_name:
            raise ValueError("模型名称不能为空")
