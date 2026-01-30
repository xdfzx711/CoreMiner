"""
Step4 Refine: Refiner 模块
根据Validator的批评意见，重新生成优化后的贡献摘要
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional

# 加载环境变量
env_paths = [
    Path(__file__).parent.parent.parent / '.env',
    Path.cwd() / '.env',
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break
else:
    load_dotenv()


# ============================================================================
# Refine 提示词
# ============================================================================

REFINE_SYSTEM_PROMPT = """You are a professional academic paper editor specializing in refining paper contribution summaries based on reviewer feedback.

Your tasks:
1. Carefully read the original summary and reviewer's critique
2. Remove all hallucinated content not supported by the original text
3. Add all missing core contribution points
4. Ensure every statement can be traced to clear evidence in the original text
5. Rewrite the summary using concise, academic language

Key Principles:
- Strictly based on original text facts; add no speculation
- Prioritize core methodological contributions; remove trivial details
- Maintain a paragraph-style summary format (3-5 sentences)
- Use concise, professional, academic language
- Write the refined summary in English
"""

REFINE_PROMPT = """Please rewrite the paper's contribution summary based on the following feedback.

# Original Summary
{original_summary}

# Original Evidence (Ground Truth)
{ground_truth}

# Reviewer Feedback (Critique)
{critique}

## Content to Remove (Hallucinations Without Original Support)
{unsupported_claims}

## Content to Add (Omitted Core Contributions)
{missing_points}

# Task Requirements
Generate a new, corrected paragraph-style summary (3-5 sentences).

Requirements:
1. Remove all hallucination points listed in "Content to Remove"
2. Add all core contributions listed in "Content to Add"
3. Ensure every sentence has supporting evidence from the original text
4. Use concise, academic language
5. Maintain paragraph format; do not use bullet points
6. Write the refined summary in English

Output the refined summary directly without any additional explanation."""


# ============================================================================
# LLM Client 创建
# ============================================================================

def _create_refine_llm_client() -> OpenAI:
    """
    创建用于Refine的LLM客户端（使用Refine Model配置）
    
    Returns:
        OpenAI: 配置好的OpenAI客户端
        
    Raises:
        ValueError: 缺少必要的环境变量
    """
    api_key = os.getenv("Refine_API_KEY")
    base_url = os.getenv("Refine_API_URL")
    
    if not api_key or not base_url:
        raise ValueError("缺少必要的环境变量: Refine_API_KEY 或 Refine_API_URL")
    
    return OpenAI(
        api_key=api_key,
        base_url=base_url
    )


# ============================================================================
# 核心Refine函数
# ============================================================================

def refine_summary(
    original_summary: str,
    ground_truth_text: str,
    critique: str,
    missing_points: list[str],
    unsupported_claims: list[str],
    llm_client: Optional[OpenAI] = None
) -> str:
    """
    基于校验意见重新生成摘要
    
    Args:
        original_summary: 原始贡献摘要
        ground_truth_text: 原文证据（摘要+引言+结论）
        critique: Validator的修改建议
        missing_points: 需要补充的要点列表
        unsupported_claims: 需要删除的幻觉列表
        llm_client: OpenAI客户端（可选，如不提供则自动创建）
        
    Returns:
        str: 修正后的贡献摘要
    """
    # 如果没有提供client，则创建一个
    if llm_client is None:
        llm_client = _create_refine_llm_client()
    
    # 格式化需要删除和补充的内容
    unsupported_text = "\n".join(f"- {claim}" for claim in unsupported_claims) if unsupported_claims else "无"
    missing_text = "\n".join(f"- {point}" for point in missing_points) if missing_points else "无"
    
    # 构建refine提示词
    refine_prompt = REFINE_PROMPT.format(
        original_summary=original_summary,
        ground_truth=ground_truth_text,
        critique=critique,
        unsupported_claims=unsupported_text,
        missing_points=missing_text
    )
    
    # 调用LLM生成修正后的摘要
    model = os.getenv("Refine_MODEL", "qwen3-next-80b-a3b-instruct")
    
    response = llm_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": REFINE_SYSTEM_PROMPT},
            {"role": "user", "content": refine_prompt}
        ],
        temperature=0.3,  # 较低的temperature以保持事实准确性
    )
    
    refined_summary = response.choices[0].message.content.strip()
    
    return refined_summary
