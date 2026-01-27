"""
数据模型定义
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class PaperSection(BaseModel):
    """论文的一个章节"""
    title: str
    content: str
    start_page: int = Field(description="章节开始页码")
    end_page: int = Field(description="章节结束页码")


class PaperStructure(BaseModel):
    """论文的结构化信息"""
    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: str
    introduction: Optional[str] = None
    introduction_end: Optional[str] = Field(
        None, description="Introduction最后1/3部分"
    )
    conclusion: Optional[str] = None
    methodology: Optional[str] = None
    full_text: str = Field(description="完整论文文本")
    sections: List[PaperSection] = Field(default_factory=list)
    
    # 元数据
    pdf_path: Optional[str] = None
    grobid_xml: Optional[str] = Field(None, description="原始Grobid XML")
    parsed_at: datetime = Field(default_factory=datetime.now)
    pages_count: int = Field(default=0)


class ExtractedText(BaseModel):
    """步骤2：提取的文本数据"""
    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: str
    sections: List[Dict[str, str]] = Field(
        default_factory=list, 
        description="章节列表，每个包含 heading 和 content"
    )
    full_text: str
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="元数据：pdf_path, num_sections, text_length等"
    )


class CleanedText(BaseModel):
    """步骤2：清洗后的文本数据"""
    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: str
    sections: List[Dict[str, str]] = Field(default_factory=list)
    full_text: str
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="包含 cleaned=True, cleaned_text_length 等"
    )
    
    # 清洗统计
    cleaning_stats: Optional[Dict[str, Any]] = Field(
        None,
        description="清洗统计：removed_chars, citations_removed等"
    )


class Contribution(BaseModel):
    """论文的一个贡献点"""
    point: str
    category: str = Field(
        description="贡献类型：architecture/loss_function/dataset/method/discovery等"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="贡献提取的置信度"
    )
    evidence: Optional[str] = Field(None, description="贡献的证据文本")


class ContributionSummary(BaseModel):
    """论文贡献的最终摘要"""
    contributions: List[Contribution] = Field(description="提取的贡献点列表")
    summary: str = Field(description="3-5句话的连贯段落摘要")
    
    # 处理过程信息
    paper_title: str
    paper_id: Optional[str] = None
    processing_steps_completed: List[str] = Field(
        default_factory=list, description="已完成的处理步骤"
    )
    fallback_used: bool = Field(default=False, description="是否使用了fallback")
    processing_time_seconds: float = Field(default=0.0)
    
    # 质量指标
    avg_confidence: float = Field(description="平均置信度")
    processing_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="处理元数据"
    )


class ProcessingResult(BaseModel):
    """完整的处理结果"""
    success: bool
    paper_structure: Optional[PaperStructure] = None
    contribution_summary: Optional[ContributionSummary] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    # 追踪信息
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_time_seconds: float = Field(default=0.0)
