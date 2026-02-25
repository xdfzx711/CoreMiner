"""
可视化模块
生成ROUGE评估结果的可视化图表
"""

import json
from pathlib import Path
from typing import Dict, List
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

from src.utils.logger import get_logger

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

logger = get_logger("CoreMiner.Step5.Visualizer")


class EvaluationVisualizer:
    """评估结果可视化器"""
    
    def __init__(self, output_dir: str):
        """
        初始化可视化器
        
        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def plot_rouge_comparison(
        self,
        results: List[Dict],
        save_name: str = "rouge_comparison.png"
    ) -> None:
        """
        绘制ROUGE分数对比图
        
        Args:
            results: 评估结果列表
            save_name: 保存文件名
        """
        logger.info("生成ROUGE对比图...")
        
        # 提取数据
        papers = [r['paper_title'][:30] + '...' if len(r['paper_title']) > 30 else r['paper_title'] for r in results]
        
        # ROUGE-1 F1分数
        rouge1_orig = [r['scores']['original_vs_reference']['rouge1']['fmeasure'] for r in results]
        rouge1_final = [r['scores']['final_vs_reference']['rouge1']['fmeasure'] for r in results]
        
        # ROUGE-2 F1分数
        rouge2_orig = [r['scores']['original_vs_reference']['rouge2']['fmeasure'] for r in results]
        rouge2_final = [r['scores']['final_vs_reference']['rouge2']['fmeasure'] for r in results]
        
        # ROUGE-L F1分数
        rougeL_orig = [r['scores']['original_vs_reference']['rougeL']['fmeasure'] for r in results]
        rougeL_final = [r['scores']['final_vs_reference']['rougeL']['fmeasure'] for r in results]
        
        # 创建图表
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        
        x = np.arange(len(papers))
        width = 0.35
        
        # ROUGE-1
        axes[0].bar(x - width/2, rouge1_orig, width, label='Original Summary', alpha=0.8)
        axes[0].bar(x + width/2, rouge1_final, width, label='Final Summary', alpha=0.8)
        axes[0].set_ylabel('F1 Score')
        axes[0].set_title('ROUGE-1 Comparison')
        axes[0].set_xticks(x)
        axes[0].set_xticklabels(papers, rotation=45, ha='right', fontsize=8)
        axes[0].legend()
        axes[0].grid(axis='y', alpha=0.3)
        
        # ROUGE-2
        axes[1].bar(x - width/2, rouge2_orig, width, label='Original Summary', alpha=0.8)
        axes[1].bar(x + width/2, rouge2_final, width, label='Final Summary', alpha=0.8)
        axes[1].set_ylabel('F1 Score')
        axes[1].set_title('ROUGE-2 Comparison')
        axes[1].set_xticks(x)
        axes[1].set_xticklabels(papers, rotation=45, ha='right', fontsize=8)
        axes[1].legend()
        axes[1].grid(axis='y', alpha=0.3)
        
        # ROUGE-L
        axes[2].bar(x - width/2, rougeL_orig, width, label='Original Summary', alpha=0.8)
        axes[2].bar(x + width/2, rougeL_final, width, label='Final Summary', alpha=0.8)
        axes[2].set_ylabel('F1 Score')
        axes[2].set_title('ROUGE-L Comparison')
        axes[2].set_xticks(x)
        axes[2].set_xticklabels(papers, rotation=45, ha='right', fontsize=8)
        axes[2].legend()
        axes[2].grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        save_path = self.output_dir / save_name
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"ROUGE对比图已保存: {save_path}")
    
    def plot_improvement_bars(
        self,
        results: List[Dict],
        save_name: str = "improvement_bars.png"
    ) -> None:
        """
        绘制改进幅度柱状图
        
        Args:
            results: 评估结果列表
            save_name: 保存文件名
        """
        logger.info("生成改进幅度图...")
        
        papers = [r['paper_title'][:30] + '...' if len(r['paper_title']) > 30 else r['paper_title'] for r in results]
        
        # 提取改进百分比
        rouge1_improvement = [r['improvement']['rouge1']['relative_improvement_percent'] for r in results]
        rouge2_improvement = [r['improvement']['rouge2']['relative_improvement_percent'] for r in results]
        rougeL_improvement = [r['improvement']['rougeL']['relative_improvement_percent'] for r in results]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = np.arange(len(papers))
        width = 0.25
        
        # 绘制柱状图
        bars1 = ax.bar(x - width, rouge1_improvement, width, label='ROUGE-1', alpha=0.8)
        bars2 = ax.bar(x, rouge2_improvement, width, label='ROUGE-2', alpha=0.8)
        bars3 = ax.bar(x + width, rougeL_improvement, width, label='ROUGE-L', alpha=0.8)
        
        # 添加零线
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        ax.set_xlabel('Papers')
        ax.set_ylabel('Improvement (%)')
        ax.set_title('ROUGE Score Improvement (Final vs Original)')
        ax.set_xticks(x)
        ax.set_xticklabels(papers, rotation=45, ha='right', fontsize=8)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        # 为正负值使用不同颜色
        for bars in [bars1, bars2, bars3]:
            for bar in bars:
                if bar.get_height() < 0:
                    bar.set_color('red')
                    bar.set_alpha(0.6)
        
        plt.tight_layout()
        
        save_path = self.output_dir / save_name
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"改进幅度图已保存: {save_path}")
    
    def plot_heatmap(
        self,
        results: List[Dict],
        metric: str = 'fmeasure',
        save_name: str = "rouge_heatmap.png"
    ) -> None:
        """
        绘制ROUGE分数热力图
        
        Args:
            results: 评估结果列表
            metric: 要显示的指标（precision, recall, fmeasure）
            save_name: 保存文件名
        """
        logger.info(f"生成ROUGE热力图 (metric: {metric})...")
        
        papers = [r['paper_title'][:20] + '...' if len(r['paper_title']) > 20 else r['paper_title'] for r in results]
        
        # 构建数据矩阵
        # 行：论文，列：ROUGE-1/2/L (Original, Final)
        data = []
        for result in results:
            row = [
                result['scores']['original_vs_reference']['rouge1'][metric],
                result['scores']['final_vs_reference']['rouge1'][metric],
                result['scores']['original_vs_reference']['rouge2'][metric],
                result['scores']['final_vs_reference']['rouge2'][metric],
                result['scores']['original_vs_reference']['rougeL'][metric],
                result['scores']['final_vs_reference']['rougeL'][metric]
            ]
            data.append(row)
        
        data = np.array(data)
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(10, max(6, len(papers) * 0.5)))
        
        im = ax.imshow(data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
        
        # 设置刻度
        ax.set_xticks(np.arange(6))
        ax.set_yticks(np.arange(len(papers)))
        ax.set_xticklabels([
            'R-1\nOrig', 'R-1\nFinal',
            'R-2\nOrig', 'R-2\nFinal',
            'R-L\nOrig', 'R-L\nFinal'
        ])
        ax.set_yticklabels(papers, fontsize=8)
        
        # 添加数值标注
        for i in range(len(papers)):
            for j in range(6):
                text = ax.text(j, i, f'{data[i, j]:.2f}',
                             ha="center", va="center", color="black", fontsize=7)
        
        ax.set_title(f'ROUGE {metric.capitalize()} Scores Heatmap')
        
        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label(f'{metric.capitalize()} Score', rotation=270, labelpad=15)
        
        plt.tight_layout()
        
        save_path = self.output_dir / save_name
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"热力图已保存: {save_path}")
    
    def plot_score_distribution(
        self,
        aggregate_stats: Dict,
        save_name: str = "score_distribution.png"
    ) -> None:
        """
        绘制分数分布箱线图
        
        Args:
            aggregate_stats: 汇总统计数据
            save_name: 保存文件名
        """
        logger.info("生成分数分布图...")
        
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        metrics = ['rouge1', 'rouge2', 'rougeL']
        titles = ['ROUGE-1', 'ROUGE-2', 'ROUGE-L']
        
        for idx, (metric, title) in enumerate(zip(metrics, titles)):
            # 提取数据
            orig_mean = aggregate_stats['original_vs_reference'][metric]['fmeasure']['mean']
            orig_std = aggregate_stats['original_vs_reference'][metric]['fmeasure']['std']
            final_mean = aggregate_stats['final_vs_reference'][metric]['fmeasure']['mean']
            final_std = aggregate_stats['final_vs_reference'][metric]['fmeasure']['std']
            
            # 绘制柱状图
            x = [0, 1]
            means = [orig_mean, final_mean]
            stds = [orig_std, final_std]
            
            bars = axes[idx].bar(x, means, yerr=stds, capsize=5, alpha=0.7,
                                color=['#1f77b4', '#ff7f0e'])
            axes[idx].set_xticks(x)
            axes[idx].set_xticklabels(['Original', 'Final'])
            axes[idx].set_ylabel('F1 Score')
            axes[idx].set_title(f'{title} (Mean ± Std)')
            axes[idx].set_ylim([0, 1])
            axes[idx].grid(axis='y', alpha=0.3)
            
            # 添加数值标注
            for i, (mean, std) in enumerate(zip(means, stds)):
                axes[idx].text(i, mean + std + 0.02, f'{mean:.3f}±{std:.3f}',
                             ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        
        save_path = self.output_dir / save_name
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"分数分布图已保存: {save_path}")
    
    def generate_all_plots(self, results: List[Dict], aggregate_stats: Dict) -> None:
        """
        生成所有可视化图表
        
        Args:
            results: 评估结果列表
            aggregate_stats: 汇总统计数据
        """
        logger.info("开始生成所有可视化图表...")
        
        self.plot_rouge_comparison(results)
        self.plot_improvement_bars(results)
        self.plot_heatmap(results, metric='fmeasure')
        self.plot_score_distribution(aggregate_stats)
        
        logger.info("所有可视化图表生成完成")
