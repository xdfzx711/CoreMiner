"""
测试 Step4 Refine 模块（完整的Validate + Refine流程）
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
env_file = project_root / '.env'
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
    print(f"[INFO] 已加载环境变量文件: {env_file}\n")

from src.step4_refine import (
    validate_and_refine,
    RefineRecord,
    save_refine_record
)


def load_core_contributions():
    """从core_contributions.json加载核心贡献数据"""
    file_path = project_root / "output" / "core_contributions.json"
    
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


def get_latest_result_file():
    """获取最新的extracted_result文件"""
    results_dir = project_root / "output" / "results"
    
    if not results_dir.exists():
        raise FileNotFoundError(f"目录不存在: {results_dir}")
    
    # 查找所有extracted_result_*.json文件
    result_files = list(results_dir.glob("extracted_result_*.json"))
    
    if not result_files:
        raise FileNotFoundError(f"未找到extracted_result文件: {results_dir}")
    
    # 返回最新的文件
    latest_file = max(result_files, key=lambda p: p.stat().st_mtime)
    return latest_file


def extract_introduction_last_third(introduction_text: str) -> str:
    """提取引言的后1/3部分"""
    if not introduction_text:
        return ""
    
    # 按字符数计算后1/3
    total_chars = len(introduction_text)
    start_pos = int(total_chars * 2 / 3)  # 从2/3位置开始，即后1/3
    
    return introduction_text[start_pos:]


def load_paper_sections():
    """从extracted_result加载论文章节内容"""
    result_file = get_latest_result_file()
    
    with open(result_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 优先使用cleaned数据，如果没有则使用original数据
    sections = data.get('cleaned', {}) or data.get('original', {})
    
    abstract = sections.get('abstract', '')
    introduction_full = sections.get('introduction_1_3', '')  # 这已经是前1/3了
    conclusion = sections.get('conclusion', '')
    
    # 对于introduction，我们需要获取后1/3部分
    # 如果有完整的introduction，提取后1/3；如果只有introduction_1_3，则全部使用
    introduction_last_third = extract_introduction_last_third(introduction_full)
    
    return {
        "abstract": abstract,
        "introduction_last_third": introduction_last_third,
        "conclusion": conclusion,
        "result_file": result_file.name
    }


def test_validate_and_refine():
    """测试完整的Validate + Refine流程"""
    print("=" * 80)
    print("测试 Step4 Refine 完整流程 (Validate + Refine)")
    print("=" * 80)
    print()
    
    try:
        # 1. 加载核心贡献数据
        contribution_data = load_core_contributions()
        paper_title = contribution_data.get('title', '未知标题')
        summary_text = contribution_data.get('contributions_summary', '')
        extract_time = contribution_data.get('extraction_timestamp', '')
        
        print(f"[OK] 已加载核心贡献：{paper_title}")
        print(f"  提取时间：{extract_time}")
        print()
        
        # 2. 加载论文章节内容
        sections = load_paper_sections()
        abstract = sections['abstract']
        introduction_last_third = sections['introduction_last_third']
        conclusion = sections['conclusion']
        
        print(f"[OK] 最新的结果文件：{sections['result_file']}")
        print(f"  - Abstract长度: {len(abstract)} 字符")
        print(f"  - Introduction (后1/3)长度: {len(introduction_last_third)} 字符")
        print(f"  - Conclusion: {'已找到 (' + str(len(conclusion)) + ' 字符)' if conclusion else '未找到'}")
        print()
        
        # 3. 贡献摘要信息
        print(f"[OK] 贡献摘要长度: {len(summary_text)} 字符")
        model_used = contribution_data.get('model_used', '未知')
        prompt_tokens = contribution_data.get('prompt_tokens', 0)
        completion_tokens = contribution_data.get('completion_tokens', 0)
        print(f"  模型: {model_used}")
        print(f"  Tokens: {prompt_tokens} + {completion_tokens}")
        print()
        
        # 4. 执行Validate + Refine流程
        print("[OK] 开始Validate + Refine流程...")
        print(f"  - Refine阈值: score >= 8 且 is_valid = True")
        print(f"  - 最大迭代次数: 3")
        print()
        
        final_summary, final_validation, iterations = validate_and_refine(
            summary_text=summary_text,
            abstract_text=abstract,
            introduction_last_third=introduction_last_third,
            conclusion_text=conclusion,
            refine_threshold=8,
            max_iterations=3
        )
        
        # 5. 输出结果
        print("=" * 80)
        print("验证和Refine结果")
        print("=" * 80)
        print()
        
        # 原始验证结果（第一次迭代的validation）
        if iterations:
            print("[INFO] 原始摘要验证结果:")
            original_val = iterations[0].validation
            print(f"  - is_valid: {original_val.is_valid}")
            print(f"  - score: {original_val.score}/10")
            print(f"  - 遗漏要点: {len(original_val.missing_points)} 个")
            print(f"  - 无依据声称: {len(original_val.unsupported_claims)} 个")
            print()
        
        # Refinement迭代历史
        if iterations:
            print(f"[INFO] 经过 {len(iterations)} 次Refinement迭代:")
            for iteration in iterations:
                print(f"\n  迭代 {iteration.iteration}:")
                print(f"    - 摘要长度: {len(iteration.summary)} 字符")
                print(f"    - 验证分数: {iteration.validation.score}/10")
                print(f"    - is_valid: {iteration.validation.is_valid}")
            print()
        else:
            print("[INFO] 原始摘要已通过验证，无需Refinement")
            print()
        
        # 最终结果
        print("[OK] 最终验证结果:")
        print(f"  - is_valid: {final_validation.is_valid}")
        print(f"  - score: {final_validation.score}/10")
        print(f"  - 遗漏要点: {len(final_validation.missing_points)} 个")
        print(f"  - 无依据声称: {len(final_validation.unsupported_claims)} 个")
        print()
        
        if final_validation.missing_points:
            print("  [WARN] 遗漏的要点:")
            for point in final_validation.missing_points:
                print(f"    - {point}")
            print()
        
        if final_validation.unsupported_claims:
            print("  [WARN] 无依据的声称:")
            for claim in final_validation.unsupported_claims:
                print(f"    - {claim}")
            print()
        
        print("[OK] 修改建议:")
        print(f"  {final_validation.critique}")
        print()
        
        print("[OK] 最终摘要:")
        print(f"  {final_summary}")
        print()
        
        # 6. 保存RefineRecord
        record = RefineRecord(
            paper_title=paper_title,
            validation_time=datetime.now().isoformat(),
            ground_truth={
                "abstract": abstract,
                "introduction_last_third": introduction_last_third,
                "conclusion": conclusion
            },
            original_summary=summary_text,
            original_validation=iterations[0].validation if iterations else final_validation,
            refinement_applied=len(iterations) > 0,
            refinement_iterations=iterations,
            final_summary=final_summary,
            final_validation=final_validation,
            total_iterations=len(iterations),
            metadata={
                "model": model_used,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "refine_threshold": 8,
                "max_iterations": 3,
                "source_file": sections['result_file']
            }
        )
        
        saved_path = save_refine_record(record)
        print(f"[OK] 已保存RefineRecord到: {saved_path}")
        print()
        
        print("=" * 80)
        print("[OK] 测试完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_validate_and_refine()
