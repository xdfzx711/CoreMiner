"""
全文提取数据模型
"""
from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime


@dataclass
class FullTextResult:
    """全文提取结果"""
    source_file: str
    title: str
    contributions_summary: str
    extraction_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    model_used: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    input_length: int = 0  # 输入文本长度（字符数）
    preprocessing_mode: str = "none"  # 预处理模式
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source_file": self.source_file,
            "title": self.title,
            "contributions_summary": self.contributions_summary,
            "extraction_timestamp": self.extraction_timestamp,
            "model_used": self.model_used,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "input_length": self.input_length,
            "preprocessing_mode": self.preprocessing_mode
        }


@dataclass
class ExtractionConfig:
    """提取配置"""
    api_key: str
    api_url: str
    model_name: str
    max_tokens: int = 2000
    temperature: float = 0.7
    preprocessing_mode: str = "none"  # "none", "minimal", "medium"
    
    def validate(self):
        """验证配置"""
        if not self.api_key:
            raise ValueError("API_KEY不能为空")
        if not self.api_url:
            raise ValueError("API_URL不能为空")
        if not self.model_name:
            raise ValueError("模型名称不能为空")
