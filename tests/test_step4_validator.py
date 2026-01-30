"""
测试Step4 Refine Validator模块
从output/core_contributions.json读取已提取的数据进行验证
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 显式加载.env文件
env_file = os.path.join(project_root, '.env')
if os.path.exists(env_file):
    load_dotenv(dotenv_path=env_file)
    print(f"[INFO] 已加载环境变量文件: {env_file}")
else:
    print(f"[WARN] 环境变量文件不存在: {env_file}")

from src.step4_refine import validate_contribution, RefineRecord, save_refine_record


def load_core_contributions(json_path: str) -> dict:
    """加载核心贡献提取结果"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_latest_result_file(results_dir: str) -> str:
    """获取最新的提取结果文件"""
    results_path = Path(results_dir)
    json_files = list(results_path.glob("extracted_result_*.json"))
    if not json_files:
        raise FileNotFoundError(f"在{results_dir}中未找到结果文件")
    latest_file = sorted(json_files, key=lambda x: x.name)[-1]
    return str(latest_file)


def load_paper_sections(json_path: str) -> dict:
    """从提取结果文件中加载论文的各个部分"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cleaned = data.get('cleaned', {})
    original = data.get('original', {})
    
    return {
        'abstract': cleaned.get('abstract') or original.get('abstract', ''),
        'introduction_1_3': cleaned.get('introduction_1_3') or original.get('introduction_1_3', ''),
        'conclusion': cleaned.get('conclusion') or original.get('conclusion'),
    }


def test_validator():
    """测试validator功能"""
    
    print("\n" + "=" * 80)
    print("测试 Step4 Refine Validator 模块")
    print("=" * 80)
    
    try:
        # 1. 加载核心贡献提取结果
        core_contrib_path = os.path.join(project_root, 'output', 'core_contributions.json')
        core_contrib = load_core_contributions(core_contrib_path)
        
        print(f"\n[OK] 已加载核心贡献：{core_contrib.get('title', 'Unknown')}")
        print(f"  提取时间：{core_contrib.get('extraction_timestamp')}")
        
        # 2. 获取最新的提取结果文件并加载论文各部分
        results_dir = os.path.join(project_root, 'output', 'results')
        latest_result_file = get_latest_result_file(results_dir)
        
        print(f"\n[OK] 最新的结果文件：{os.path.basename(latest_result_file)}")
        
        paper_sections = load_paper_sections(latest_result_file)
        
        abstract = paper_sections['abstract']
        introduction_1_3 = paper_sections['introduction_1_3']
        conclusion = paper_sections['conclusion']
        
        print(f"  - Abstract长度: {len(abstract)} 字符")
        print(f"  - Introduction (1/3)长度: {len(introduction_1_3)} 字符")
        if conclusion:
            print(f"  - Conclusion长度: {len(conclusion)} 字符")
        else:
            print(f"  - Conclusion: 未找到")
        
        # 3. 调用validator进行验证
        summary_text = core_contrib.get('contributions_summary', '')
        
        print(f"\n[OK] 贡献摘要长度: {len(summary_text)} 字符")
        print(f"  模型: {core_contrib.get('model_used')}")
        print(f"  Tokens: {core_contrib.get('prompt_tokens')} + {core_contrib.get('completion_tokens')}")
        
        print("\n【开始验证...】")
        result = validate_contribution(
            summary_text=summary_text,
            conclusion_text=conclusion if conclusion else '',
            abstract_text=abstract
        )
        
        # 4. 创建RefineRecord并保存
        record = RefineRecord(
            paper_title=core_contrib.get('paper_title', ''),
            validation_time=datetime.now().isoformat(),
            ground_truth={
                "abstract": abstract,
                "introduction_1_3": introduction_1_3,
                "conclusion": conclusion if conclusion else ""
            },
            contribution_summary=summary_text,
            validation_result=result,
            metadata={
                "model_used": core_contrib.get('model_used'),
                "prompt_tokens": core_contrib.get('prompt_tokens'),
                "completion_tokens": core_contrib.get('completion_tokens'),
                "extraction_time": core_contrib.get('extraction_time')
            }
        )
        
        # 保存记录
        saved_path = save_refine_record(record)
        
        # 5. 输出验证结果
        print("\n" + "=" * 80)
        print("【验证结果】")
        print("=" * 80)
        
        status = "[PASS]" if result.is_valid else "[FAIL]"
        print(f"总体状态: {status}")
        print(f"质量评分: {result.score}/10")
        
        if result.missing_points:
            print("\n【遗漏的要点】")
            for i, point in enumerate(result.missing_points, 1):
                print(f"  {i}. {point}")
        
        if result.unsupported_claims:
            print("\n【无原文支持的声称】")
            for i, claim in enumerate(result.unsupported_claims, 1):
                print(f"  {i}. {claim}")
        
        print("\n【修改建议】")
        print(result.critique)
        print("=" * 80 + "\n")
        
        # 6. 显示保存路径
        print(f"[OK] 验证记录已保存: {saved_path}")
        
    except FileNotFoundError as e:
        print(f"\n[ERROR] 文件未找到: {str(e)}")
        raise
    except Exception as e:
        print(f"\n[ERROR] 验证过程出错: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        test_validator()
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
