import json
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量 - 从项目根目录查找.env文件
# 使用多种方式确保能找到.env文件
env_paths = [
    Path(__file__).parent.parent.parent / '.env',  # 从脚本位置向上找
    Path.cwd() / '.env',  # 从当前工作目录
    Path('/d/pythonproject/CoreMiner/.env'),  # 直接指定路径
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break
else:
    # 如果都不存在，仍然调用一次，从标准位置查找
    load_dotenv()

# ============================================================================
# 数据模型
# ============================================================================

class ValidationResult(BaseModel):
    """验证结果数据模型"""
    is_valid: bool = Field(
        description="是否所有贡献点都有原文支撑"
    )
    missing_points: list[str] = Field(
        default_factory=list,
        description="原文Conclusion中有，但被摘要遗漏的重要点"
    )
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="摘要中提到，但Conclusion不支持的幻觉点"
    )
    critique: str = Field(
        description="给Refiner的具体修改建议"
    )
    score: int = Field(
        description="质量打分 1-10",
        ge=1,
        le=10
    )


class RefinementIteration(BaseModel):
    """单次refinement迭代记录"""
    iteration: int = Field(description="迭代次数 (1-based)")
    summary: str = Field(description="本次迭代的摘要")
    validation: ValidationResult = Field(description="本次迭代的验证结果")


class RefineRecord(BaseModel):
    """完整的验证和Refinement记录数据模型"""
    paper_title: str = Field(description="论文标题")
    validation_time: str = Field(description="验证时间")
    
    # Ground Truth 原文依据
    ground_truth: dict = Field(
        description="原文证据",
        default_factory=dict
    )  # {"abstract": str, "introduction_last_third": str, "conclusion": str}
    
    # 原始提取的贡献
    original_summary: str = Field(description="Step3提取的原始贡献摘要")
    original_validation: ValidationResult = Field(description="原始摘要的验证结果")
    
    # Refinement过程
    refinement_applied: bool = Field(default=False, description="是否经过refinement")
    refinement_iterations: list[RefinementIteration] = Field(
        default_factory=list,
        description="所有refinement迭代历史"
    )
    
    # 最终结果
    final_summary: str = Field(description="最终使用的摘要")
    final_validation: ValidationResult = Field(description="最终验证结果")
    total_iterations: int = Field(default=0, description="总迭代次数")
    
    # 元数据
    metadata: dict = Field(
        description="其他元数据",
        default_factory=dict
    )  # {"model": str, "tokens": dict, "refine_threshold": int, etc}


# ============================================================================
# 验证提示词
# ============================================================================

VALIDATION_SYSTEM_PROMPT = """You are a rigorous paper fact-checker. Your task is to verify whether a "paper contribution summary" accurately reflects the paper's "conclusion" and "abstract" without distortion.

Please examine the following three aspects:

1. **Hallucination Detection**: Can every statement in the summary be traced back to corresponding evidence in the original text? Check for fabricated claims.

2. **Omission Detection**: Are major SOTA results, core architectures, or key innovations emphasized in the original conclusion missing from the summary?

3. **Relevance Assessment**: Does the summary include overly trivial details (e.g., hyperparameter settings, experimental environment) while neglecting methodological contributions?

You must output the evaluation result in strict JSON format with no additional text."""

VALIDATION_PROMPT = """Please verify whether the following paper contribution summary is consistent with the original text (abstract + conclusion).

【Original Evidence】
{ground_truth}

【Contribution Summary to Verify】
{summary}

Please check each point in the summary against the original text, then return in the following JSON format:

{{
    "is_valid": true/false,  // Criteria: true if unsupported_claims is empty AND missing_points ≤ 1; otherwise false
    "missing_points": ["Key point 1 from original text that was omitted", "Key point 2 from original text that was omitted"],  // Only list omissions of core contributions, not details
    "unsupported_claims": ["Hallucinated claim 1 not supported by original text", "Hallucinated claim 2 not supported by original text"],  // Must be clear factual errors
    "critique": "Specific revision suggestions for the Refiner, including what to add, what to remove, and how to adjust phrasing (in English)",
    "score": 8  // Scoring criteria: 9-10=perfect; 7-8=1-2 minor omissions; 5-6=obvious omissions but no hallucinations; 3-4=minor hallucinations; 1-2=severe hallucinations
}}

Important: Output ONLY the JSON, no additional text."""


# ============================================================================
# 核心验证函数
# ============================================================================

def validate_contribution(
    summary_text: str,
    conclusion_text: str,
    abstract_text: str,
    introduction_text: str = "",
    llm_client: Optional[OpenAI] = None
) -> ValidationResult:
    """
    检查生成的贡献总结是否与原文(摘要+引言+结论)一致
    
    Args:
        summary_text: 提取出的贡献摘要
        conclusion_text: 论文结论
        abstract_text: 论文摘要
        introduction_text: 论文引言（可选，建议使用后1/3部分）
        llm_client: OpenAI客户端，如果为None则自动创建
        
    Returns:
        ValidationResult: 验证结果对象
    """
    # 如果未提供客户端，则创建一个
    if llm_client is None:
        llm_client = _create_llm_client()
    
    # 构建ground truth（包含引言）
    ground_truth_parts = [f"【摘要】\n{abstract_text}"]
    
    if introduction_text:
        ground_truth_parts.append(f"【引言（后1/3）】\n{introduction_text}")
    
    ground_truth_parts.append(f"【结论】\n{conclusion_text}")
    
    ground_truth = "\n\n".join(ground_truth_parts)
    
    # 构建提示词
    prompt = VALIDATION_PROMPT.format(
        ground_truth=ground_truth,
        summary=summary_text
    )
    
    # 调用LLM进行验证（使用Judge Model）
    response = llm_client.chat.completions.create(
        model=os.getenv("JUDGE_MODEL", "gpt-4o"),
        messages=[
            {"role": "system", "content": VALIDATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3  # 降低温度以增强确定性
    )
    
    # 解析响应
    response_text = response.choices[0].message.content
    
    try:
        result_dict = json.loads(response_text)
        return ValidationResult(**result_dict)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM返回的JSON格式无效: {response_text}") from e


# ============================================================================
# 辅助函数
# ============================================================================

def _create_llm_client() -> OpenAI:
    """
    创建LLM客户端（使用Judge Model进行事实核查）
    
    Returns:
        OpenAI: 配置好的OpenAI客户端
    """
    # 确保环境变量已加载
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / '.env'
    if env_file.exists():
        print(f"[DEBUG] 正在加载环境变量: {env_file}")
        load_dotenv(dotenv_path=env_file, override=True)
    else:
        print(f"[DEBUG] .env文件不存在: {env_file}")
    
    api_key = os.getenv("JUDGE_API_KEY")
    api_url = os.getenv("JUDGE_API_URL")
    
    print(f"[DEBUG] JUDGE_API_KEY: {'已设置' if api_key else '未设置'}")
    print(f"[DEBUG] JUDGE_API_URL: {'已设置' if api_url else '未设置'}")
    
    if not api_key or not api_url:
        raise ValueError("缺少必要的环境变量: JUDGE_API_KEY 或 JUDGE_API_URL")
    
    return OpenAI(
        api_key=api_key,
        base_url=api_url
    )


# ============================================================================
# 整合Workflow: Validate + Refine
# ============================================================================

def validate_and_refine(
    summary_text: str,
    abstract_text: str,
    introduction_last_third: str,
    conclusion_text: str,
    refine_threshold: int = 8,
    max_iterations: int = 3,
    judge_llm_client: Optional[OpenAI] = None,
    refine_llm_client: Optional[OpenAI] = None
) -> tuple[str, ValidationResult, list[RefinementIteration]]:
    """
    完整的验证+优化流程
    
    Args:
        summary_text: 待验证的贡献摘要
        abstract_text: 论文摘要
        introduction_last_third: 引言后1/3部分
        conclusion_text: 论文结论
        refine_threshold: score低于此值或is_valid=False时触发refine (默认8)
        max_iterations: 最大refinement迭代次数 (默认3)
        judge_llm_client: Judge Model客户端（可选）
        refine_llm_client: Refine Model客户端（可选）
        
    Returns:
        final_summary: 最终使用的摘要
        final_validation: 最终验证结果
        iterations: refinement迭代历史
    """
    from .refiner import refine_summary, _create_refine_llm_client
    
    # 准备Ground Truth文本
    ground_truth_text = f"""【摘要 Abstract】
{abstract_text}

【引言（后1/3）Introduction (Last Third)】
{introduction_last_third}

【结论 Conclusion】
{conclusion_text if conclusion_text else '未找到'}"""
    
    # 创建LLM clients
    if judge_llm_client is None:
        judge_llm_client = _create_llm_client()
    if refine_llm_client is None:
        refine_llm_client = _create_refine_llm_client()
    
    # 第一次验证
    current_summary = summary_text
    iterations = []
    
    for i in range(max_iterations):
        # 验证当前摘要
        validation = validate_contribution(
            summary_text=current_summary,
            conclusion_text=conclusion_text,
            abstract_text=abstract_text,
            introduction_text=introduction_last_third,
            llm_client=judge_llm_client
        )
        
        # 检查是否通过（使用and逻辑）
        if validation.is_valid and validation.score >= refine_threshold:
            # 验证通过，返回结果
            return current_summary, validation, iterations
        
        # 如果已经是最后一次迭代，不再refine
        if i == max_iterations - 1:
            return current_summary, validation, iterations
        
        # 执行refinement
        refined_summary = refine_summary(
            original_summary=current_summary,
            ground_truth_text=ground_truth_text,
            critique=validation.critique,
            missing_points=validation.missing_points,
            unsupported_claims=validation.unsupported_claims,
            llm_client=refine_llm_client
        )
        
        # 记录本次迭代
        iterations.append(RefinementIteration(
            iteration=i + 1,
            summary=refined_summary,
            validation=validation
        ))
        
        # 更新当前摘要，继续下一轮
        current_summary = refined_summary
    
    # 最后一次验证（max_iterations次refine后）
    final_validation = validate_contribution(
        summary_text=current_summary,
        conclusion_text=conclusion_text,
        abstract_text=abstract_text,
        introduction_text=introduction_last_third,
        llm_client=judge_llm_client
    )
    
    return current_summary, final_validation, iterations


def save_refine_record(
    record: RefineRecord,
    output_dir: str = "output/refine_results",
    paper_title: str = None
) -> Path:
    """
    保存验证记录到JSON文件
    
    Args:
        record: RefineRecord对象
        output_dir: 输出目录路径
        paper_title: 论文标题(可选,用于生成文件名)
        
    Returns:
        Path: 保存的文件路径
    """
    from src.utils.file_handler import FileHandler
    
    # 创建输出目录
    project_root = Path(__file__).parent.parent.parent
    output_path = project_root / output_dir
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名 - 优先使用论文标题
    sanitized_title = FileHandler.sanitize_title(paper_title) if paper_title else None
    
    if sanitized_title:
        filename = f"refine_record_{sanitized_title}.json"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"refine_record_{timestamp}.json"
    
    file_path = output_path / filename
    
    # 保存JSON
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(
            record.model_dump(),
            f,
            ensure_ascii=False,
            indent=2
        )
    
    return file_path



