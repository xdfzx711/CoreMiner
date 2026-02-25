"""
测试评估模块的基本功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.step5_evaluation.data_loader import EvaluationDataLoader
from src.step5_evaluation.rouge_evaluator import ROUGEEvaluator


def test_data_loader():
    """测试数据加载器"""
    print("=" * 80)
    print("测试数据加载器")
    print("=" * 80)
    
    manual_summary_path = project_root / "Manual_Summary_Generation.json"
    llm_results_dir = project_root / "output" / "llm_results"
    refine_results_dir = project_root / "output" / "refine_results"
    
    loader = EvaluationDataLoader(
        manual_summary_path=str(manual_summary_path),
        llm_results_dir=str(llm_results_dir),
        refine_results_dir=str(refine_results_dir),
        similarity_threshold=0.85
    )
    
    try:
        loader.load_all_data()
        stats = loader.get_statistics()
        
        print(f"\n✓ 数据加载成功")
        print(f"  参考摘要: {stats['total_reference_summaries']}")
        print(f"  LLM结果: {stats['total_llm_results']}")
        print(f"  Refine结果: {stats['total_refine_results']}")
        print(f"  匹配对数: {stats['matched_pairs']}")
        
        if stats['matched_pairs'] > 0:
            pairs = loader.get_evaluation_pairs()
            print(f"\n第一对数据样例:")
            print(f"  标题: {pairs[0]['paper_title'][:60]}...")
            print(f"  参考摘要长度: {len(pairs[0]['reference_summary'])}")
            print(f"  原始摘要长度: {len(pairs[0]['original_summary'])}")
            print(f"  优化摘要长度: {len(pairs[0]['final_summary'])}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 数据加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rouge_evaluator():
    """测试ROUGE评估器"""
    print("\n" + "=" * 80)
    print("测试ROUGE评估器")
    print("=" * 80)
    
    evaluator = ROUGEEvaluator(use_stemmer=True)
    
    # 测试数据
    reference = "The paper introduces a novel attack paradigm using Unicode characters."
    candidate1 = "This paper presents a new attack using Unicode."
    candidate2 = "The study proposes innovative Unicode-based attacks."
    
    try:
        scores1 = evaluator.evaluate_pair(reference, candidate1, "test_1")
        scores2 = evaluator.evaluate_pair(reference, candidate2, "test_2")
        
        print(f"\n✓ ROUGE评估成功")
        print(f"\nCandidate 1 vs Reference:")
        print(f"  ROUGE-1 F1: {scores1['rouge1']['fmeasure']:.4f}")
        print(f"  ROUGE-2 F1: {scores1['rouge2']['fmeasure']:.4f}")
        print(f"  ROUGE-L F1: {scores1['rougeL']['fmeasure']:.4f}")
        
        print(f"\nCandidate 2 vs Reference:")
        print(f"  ROUGE-1 F1: {scores2['rouge1']['fmeasure']:.4f}")
        print(f"  ROUGE-2 F1: {scores2['rouge2']['fmeasure']:.4f}")
        print(f"  ROUGE-L F1: {scores2['rougeL']['fmeasure']:.4f}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ROUGE评估失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_title_similarity():
    """测试标题匹配算法"""
    print("\n" + "=" * 80)
    print("测试标题匹配")
    print("=" * 80)
    
    loader = EvaluationDataLoader(
        manual_summary_path="dummy",
        llm_results_dir="dummy",
        refine_results_dir="dummy"
    )
    
    test_cases = [
        ("AgentDojo: A Dynamic Environment", "AgentDojo: A Dynamic Environment", 1.0),
        ("AgentDojo: Dynamic Environment", "AgentDojo: A Dynamic Environment", 0.9),
        ("AGENTHARM: A BENCHMARK", "AgentHarm: A Benchmark", 0.85),
        ("Completely Different Title", "AgentDojo: Dynamic", 0.3)
    ]
    
    print("\n标题匹配测试:")
    for title1, title2, expected_min in test_cases:
        similarity = loader._calculate_title_similarity(title1, title2)
        status = "✓" if similarity >= expected_min * 0.9 else "✗"
        print(f"  {status} '{title1}' <-> '{title2}'")
        print(f"     相似度: {similarity:.3f} (预期 ≥ {expected_min:.3f})")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("CoreMiner Step 5 评估模块测试")
    print("=" * 80 + "\n")
    
    # 运行测试
    test_results = []
    
    test_results.append(("标题匹配", test_title_similarity()))
    test_results.append(("ROUGE评估", test_rouge_evaluator()))
    test_results.append(("数据加载", test_data_loader()))
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    
    for test_name, result in test_results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status}: {test_name}")
    
    all_passed = all(result for _, result in test_results)
    
    if all_passed:
        print("\n✓ 所有测试通过！可以运行完整评估。")
        sys.exit(0)
    else:
        print("\n✗ 部分测试失败，请检查错误信息。")
        sys.exit(1)
