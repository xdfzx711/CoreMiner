"""
Step 5: 评估模块主程序
运行ROUGE评估并生成报告
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.step5_evaluation.data_loader import EvaluationDataLoader
from src.step5_evaluation.rouge_evaluator import ROUGEEvaluator
from src.step5_evaluation.visualizer import EvaluationVisualizer
from src.utils.logger import get_logger

logger = get_logger("CoreMiner.Step5.Main")


def main():
    """主评估流程"""
    logger.info("=" * 80)
    logger.info("CoreMiner Step 5: 评估模块启动")
    logger.info("=" * 80)
    
    # 配置路径
    base_dir = project_root
    manual_summary_path = base_dir / "Manual_Summary_Generation.json"
    llm_results_dir = base_dir / "output" / "llm_results"
    refine_results_dir = base_dir / "output" / "refine_results"
    
    # 输出目录
    evaluation_output_dir = base_dir / "output" / "evaluation_results"
    data_prep_dir = evaluation_output_dir / "data_preparation"
    rouge_scores_dir = evaluation_output_dir / "rouge_scores"
    comparison_dir = evaluation_output_dir / "comparison"
    visualization_dir = evaluation_output_dir / "visualization"
    
    # ========== Step 1: 加载和匹配数据 ==========
    logger.info("\n" + "=" * 80)
    logger.info("Step 1: 数据加载与匹配")
    logger.info("=" * 80)
    
    data_loader = EvaluationDataLoader(
        manual_summary_path=str(manual_summary_path),
        llm_results_dir=str(llm_results_dir),
        refine_results_dir=str(refine_results_dir),
        similarity_threshold=0.85  # 标题匹配阈值
    )
    
    # 加载所有数据
    data_loader.load_all_data()
    
    # 获取统计信息
    stats = data_loader.get_statistics()
    logger.info("\n数据统计:")
    logger.info(f"  参考摘要总数: {stats['total_reference_summaries']}")
    logger.info(f"  LLM结果总数: {stats['total_llm_results']}")
    logger.info(f"  Refine结果总数: {stats['total_refine_results']}")
    logger.info(f"  成功匹配对数: {stats['matched_pairs']}")
    logger.info(f"  匹配率: {stats['match_rate']:.2%}")
    
    # 保存匹配结果
    data_loader.save_evaluation_pairs(
        str(data_prep_dir / f"evaluation_pairs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    )
    
    # 获取评估对
    evaluation_pairs = data_loader.get_evaluation_pairs()
    
    if not evaluation_pairs:
        logger.error("没有找到可评估的数据对，程序退出")
        return
    
    # ========== Step 2: ROUGE评估 ==========
    logger.info("\n" + "=" * 80)
    logger.info("Step 2: ROUGE评估")
    logger.info("=" * 80)
    
    rouge_evaluator = ROUGEEvaluator(use_stemmer=True)
    
    # 评估所有论文
    results = rouge_evaluator.evaluate_all(evaluation_pairs)
    
    # 计算汇总统计
    aggregate_stats = rouge_evaluator.calculate_aggregate_statistics()
    
    # 打印汇总结果
    logger.info("\n汇总统计结果:")
    logger.info(f"  评估论文总数: {aggregate_stats['total_papers']}")
    
    logger.info("\n  Original vs Reference:")
    for metric in ['rouge1', 'rouge2', 'rougeL']:
        mean_f1 = aggregate_stats['original_vs_reference'][metric]['fmeasure']['mean']
        logger.info(f"    {metric.upper()} F1: {mean_f1:.4f}")
    
    logger.info("\n  Final vs Reference:")
    for metric in ['rouge1', 'rouge2', 'rougeL']:
        mean_f1 = aggregate_stats['final_vs_reference'][metric]['fmeasure']['mean']
        logger.info(f"    {metric.upper()} F1: {mean_f1:.4f}")
    
    logger.info("\n  改进情况:")
    for metric in ['rouge1', 'rouge2', 'rougeL']:
        improvement = aggregate_stats['improvement_summary'][metric]
        logger.info(f"    {metric.upper()}:")
        logger.info(f"      平均改进: {improvement['absolute_delta']['mean']:.4f} ({improvement['relative_improvement_percent']['mean']:.2f}%)")
        logger.info(f"      改进论文数: {improvement['papers_improved']}")
        logger.info(f"      退化论文数: {improvement['papers_degraded']}")
    
    # ========== Step 3: 保存结果 ==========
    logger.info("\n" + "=" * 80)
    logger.info("Step 3: 保存评估结果")
    logger.info("=" * 80)
    
    # 保存JSON结果
    rouge_evaluator.save_results(str(rouge_scores_dir))
    
    # 保存CSV对比表
    rouge_evaluator.save_comparison_csv(str(comparison_dir))
    
    # ========== Step 4: 生成可视化 ==========
    logger.info("\n" + "=" * 80)
    logger.info("Step 4: 生成可视化图表")
    logger.info("=" * 80)
    
    visualizer = EvaluationVisualizer(str(visualization_dir))
    visualizer.generate_all_plots(results, aggregate_stats)
    
    # ========== 完成 ==========
    logger.info("\n" + "=" * 80)
    logger.info("评估完成！")
    logger.info("=" * 80)
    logger.info(f"\n结果保存位置:")
    logger.info(f"  数据准备: {data_prep_dir}")
    logger.info(f"  ROUGE分数: {rouge_scores_dir}")
    logger.info(f"  对比表格: {comparison_dir}")
    logger.info(f"  可视化图表: {visualization_dir}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n用户中断程序")
    except Exception as e:
        logger.error(f"程序执行出错: {e}", exc_info=True)
        raise
