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

REFINE_SYSTEM_PROMPT = """You are a professional academic paper editor specializing in **minimally editing** paper contribution summaries based on reviewer feedback.

Your tasks:
1. Carefully read the original summary and reviewer's critique
2. Make ONLY the necessary corrections - do NOT rewrite the entire summary
3. Remove hallucinated content by deletion, not by rephrasing
4. Add missing points by inserting new sentences, preserving original text
5. Keep the original wording, sentence structure, and terminology as much as possible

Key Principles:
- PRESERVE original text: modify only sentences with errors
- MINIMAL changes: prefer deletion/insertion over rewriting
- KEEP technical terms: do not paraphrase established terminology
- Strictly based on original text facts; add no speculation
- Maintain a paragraph-style summary format (3-5 sentences)
- Write the refined summary in English
"""

REFINE_PROMPT = """Please **minimally edit** the paper's contribution summary based on the following feedback.

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
Make minimal corrections to the original summary (3-5 sentences).

Requirements:
1. **PRESERVE original wording** - only modify sentences that contain errors
2. **KEEP technical terms unchanged** - do not use synonyms or paraphrase
3. Remove hallucinations by DELETING the specific incorrect phrases, not by rewriting entire sentences
4. Add missing points by INSERTING new sentences at appropriate positions
5. Ensure every sentence has supporting evidence from the original text
6. Maintain paragraph format; do not use bullet points
7. Write the refined summary in English

IMPORTANT: The refined summary should be as close to the original as possible. Only change what is explicitly wrong.

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
