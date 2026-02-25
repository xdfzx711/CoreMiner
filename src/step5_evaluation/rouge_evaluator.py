"""
ROUGE评估器模块
使用ROUGE-1, ROUGE-2, ROUGE-L评估摘要质量
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from rouge_score import rouge_scorer
from src.utils.logger import get_logger

logger = get_logger("CoreMiner.Step5.ROUGEEvaluator")


class ROUGEEvaluator:
    """ROUGE评估器"""
    
    def __init__(self, use_stemmer: bool = True, lang: str = 'english'):
        """
        初始化ROUGE评估器
        
        Args:
            use_stemmer: 是否使用词干提取
            lang: 语言设置
        """
        self.scorer = rouge_scorer.RougeScorer(
            ['rouge1', 'rouge2', 'rougeL'],
            use_stemmer=use_stemmer
        )
        self.lang = lang
        
        # 评估结果存储
        self.results: List[Dict] = []
    
    def evaluate_pair(
        self,
        reference: str,
        candidate: str,
        pair_id: str = None
    ) -> Dict:
        """
        评估单对候选-参考摘要
        
        Args:
            reference: 参考摘要
            candidate: 候选摘要
            pair_id: 评估对标识
            
        Returns:
            ROUGE评分字典
        """
        scores = self.scorer.score(reference, candidate)
        
        # 转换为更易读的格式
        result = {
            'pair_id': pair_id,
            'rouge1': {
                'precision': scores['rouge1'].precision,
                'recall': scores['rouge1'].recall,
                'fmeasure': scores['rouge1'].fmeasure
            },
            'rouge2': {
                'precision': scores['rouge2'].precision,
                'recall': scores['rouge2'].recall,
                'fmeasure': scores['rouge2'].fmeasure
            },
            'rougeL': {
                'precision': scores['rougeL'].precision,
                'recall': scores['rougeL'].recall,
                'fmeasure': scores['rougeL'].fmeasure
            }
        }
        
        return result
    
    def evaluate_paper(self, evaluation_pair: Dict) -> Dict:
        """
        评估单篇论文的所有摘要对比
        
        Args:
            evaluation_pair: 包含reference, original, final的数据字典
            
        Returns:
            完整的评估结果
        """
        paper_title = evaluation_pair.get('paper_title', 'Unknown')
        reference = evaluation_pair.get('reference_summary', '')
        original = evaluation_pair.get('original_summary', '')
        final = evaluation_pair.get('final_summary', '')
        
        logger.info(f"评估论文: {paper_title[:60]}...")
        
        # 1. Original vs Reference
        scores_orig_vs_ref = self.evaluate_pair(
            reference=reference,
            candidate=original,
            pair_id=f"{paper_title}_original_vs_reference"
        )
        
        # 2. Final vs Reference
        scores_final_vs_ref = self.evaluate_pair(
            reference=reference,
            candidate=final,
            pair_id=f"{paper_title}_final_vs_reference"
        )
        
        # 3. Final vs Original (改进分析)
        scores_final_vs_orig = self.evaluate_pair(
            reference=original,
            candidate=final,
            pair_id=f"{paper_title}_final_vs_original"
        )
        
        # 4. 计算改进幅度
        improvement = self._calculate_improvement(
            scores_orig_vs_ref,
            scores_final_vs_ref
        )
        
        # 构建完整结果
        result = {
            'paper_title': paper_title,
            'matched_reference_title': evaluation_pair.get('matched_reference_title'),
            'timestamp': datetime.now().isoformat(),
            'scores': {
                'original_vs_reference': scores_orig_vs_ref,
                'final_vs_reference': scores_final_vs_ref,
                'final_vs_original': scores_final_vs_orig
            },
            'improvement': improvement,
            'metadata': evaluation_pair.get('metadata', {}),
            'source_files': evaluation_pair.get('source_files', {})
        }
        
        self.results.append(result)
        logger.info(f"评估完成: {paper_title[:60]}...")
        
        return result
    
    def _calculate_improvement(
        self,
        orig_scores: Dict,
        final_scores: Dict
    ) -> Dict:
        """
        计算改进幅度
        
        Args:
            orig_scores: 原始摘要的评分
            final_scores: 优化后摘要的评分
            
        Returns:
            改进幅度字典
        """
        improvement = {}
        
        for metric in ['rouge1', 'rouge2', 'rougeL']:
            orig_f1 = orig_scores[metric]['fmeasure']
            final_f1 = final_scores[metric]['fmeasure']
            
            # 绝对改进
            absolute_delta = final_f1 - orig_f1
            
            # 相对改进率
            if orig_f1 > 0:
                relative_improvement = (absolute_delta / orig_f1) * 100
            else:
                relative_improvement = 0.0
            
            improvement[metric] = {
                'absolute_delta': absolute_delta,
                'relative_improvement_percent': relative_improvement,
                'original_f1': orig_f1,
                'final_f1': final_f1
            }
        
        return improvement
    
    def evaluate_all(self, evaluation_pairs: List[Dict]) -> List[Dict]:
        """
        评估所有论文
        
        Args:
            evaluation_pairs: 评估数据对列表
            
        Returns:
            所有评估结果列表
        """
        logger.info(f"开始评估 {len(evaluation_pairs)} 篇论文...")
        
        self.results = []
        
        for i, pair in enumerate(evaluation_pairs, 1):
            logger.info(f"进度: {i}/{len(evaluation_pairs)}")
            try:
                self.evaluate_paper(pair)
            except Exception as e:
                logger.error(f"评估失败: {pair.get('paper_title', 'Unknown')} - {e}")
                continue
        
        logger.info("所有论文评估完成")
        return self.results
    
    def calculate_aggregate_statistics(self) -> Dict:
        """
        计算汇总统计数据
        
        Returns:
            汇总统计字典
        """
        if not self.results:
            logger.warning("没有可用的评估结果")
            return {}
        
        logger.info("计算汇总统计...")
        
        # 初始化统计容器
        stats = {
            'total_papers': len(self.results),
            'original_vs_reference': self._calculate_metric_stats('original_vs_reference'),
            'final_vs_reference': self._calculate_metric_stats('final_vs_reference'),
            'final_vs_original': self._calculate_metric_stats('final_vs_original'),
            'improvement_summary': self._calculate_improvement_stats()
        }
        
        return stats
    
    def _calculate_metric_stats(self, comparison_type: str) -> Dict:
        """
        计算特定对比类型的统计数据
        
        Args:
            comparison_type: 对比类型（original_vs_reference等）
            
        Returns:
            统计数据字典
        """
        stats = {}
        
        for metric in ['rouge1', 'rouge2', 'rougeL']:
            precision_values = []
            recall_values = []
            fmeasure_values = []
            
            for result in self.results:
                scores = result['scores'][comparison_type][metric]
                precision_values.append(scores['precision'])
                recall_values.append(scores['recall'])
                fmeasure_values.append(scores['fmeasure'])
            
            stats[metric] = {
                'precision': {
                    'mean': sum(precision_values) / len(precision_values),
                    'min': min(precision_values),
                    'max': max(precision_values),
                    'std': self._calculate_std(precision_values)
                },
                'recall': {
                    'mean': sum(recall_values) / len(recall_values),
                    'min': min(recall_values),
                    'max': max(recall_values),
                    'std': self._calculate_std(recall_values)
                },
                'fmeasure': {
                    'mean': sum(fmeasure_values) / len(fmeasure_values),
                    'min': min(fmeasure_values),
                    'max': max(fmeasure_values),
                    'std': self._calculate_std(fmeasure_values)
                }
            }
        
        return stats
    
    def _calculate_improvement_stats(self) -> Dict:
        """计算改进统计"""
        stats = {}
        
        for metric in ['rouge1', 'rouge2', 'rougeL']:
            absolute_deltas = []
            relative_improvements = []
            
            for result in self.results:
                improvement = result['improvement'][metric]
                absolute_deltas.append(improvement['absolute_delta'])
                relative_improvements.append(improvement['relative_improvement_percent'])
            
            stats[metric] = {
                'absolute_delta': {
                    'mean': sum(absolute_deltas) / len(absolute_deltas),
                    'min': min(absolute_deltas),
                    'max': max(absolute_deltas)
                },
                'relative_improvement_percent': {
                    'mean': sum(relative_improvements) / len(relative_improvements),
                    'min': min(relative_improvements),
                    'max': max(relative_improvements)
                },
                'papers_improved': sum(1 for d in absolute_deltas if d > 0),
                'papers_degraded': sum(1 for d in absolute_deltas if d < 0),
                'papers_unchanged': sum(1 for d in absolute_deltas if d == 0)
            }
        
        return stats
    
    def _calculate_std(self, values: List[float]) -> float:
        """计算标准差"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def save_results(self, output_dir: str) -> None:
        """
        保存评估结果
        
        Args:
            output_dir: 输出目录路径
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存详细结果
        detailed_file = output_path / f"detailed_scores_{timestamp}.json"
        with open(detailed_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        logger.info(f"详细结果已保存: {detailed_file}")
        
        # 保存汇总统计
        stats = self.calculate_aggregate_statistics()
        stats_file = output_path / f"aggregate_statistics_{timestamp}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        logger.info(f"汇总统计已保存: {stats_file}")
    
    def save_comparison_csv(self, output_dir: str) -> None:
        """
        保存对比CSV文件
        
        Args:
            output_dir: 输出目录路径
        """
        import csv
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存Original vs Reference对比
        self._save_comparison_csv_single(
            output_path / f"original_vs_reference_{timestamp}.csv",
            'original_vs_reference'
        )
        
        # 保存Final vs Reference对比
        self._save_comparison_csv_single(
            output_path / f"final_vs_reference_{timestamp}.csv",
            'final_vs_reference'
        )
        
        # 保存改进分析
        self._save_improvement_csv(
            output_path / f"improvement_analysis_{timestamp}.csv"
        )
    
    def _save_comparison_csv_single(self, file_path: Path, comparison_type: str) -> None:
        """保存单个对比类型的CSV"""
        import csv
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 写入表头
            writer.writerow([
                'Paper Title',
                'ROUGE-1 Precision', 'ROUGE-1 Recall', 'ROUGE-1 F1',
                'ROUGE-2 Precision', 'ROUGE-2 Recall', 'ROUGE-2 F1',
                'ROUGE-L Precision', 'ROUGE-L Recall', 'ROUGE-L F1'
            ])
            
            # 写入数据
            for result in self.results:
                scores = result['scores'][comparison_type]
                writer.writerow([
                    result['paper_title'],
                    f"{scores['rouge1']['precision']:.4f}",
                    f"{scores['rouge1']['recall']:.4f}",
                    f"{scores['rouge1']['fmeasure']:.4f}",
                    f"{scores['rouge2']['precision']:.4f}",
                    f"{scores['rouge2']['recall']:.4f}",
                    f"{scores['rouge2']['fmeasure']:.4f}",
                    f"{scores['rougeL']['precision']:.4f}",
                    f"{scores['rougeL']['recall']:.4f}",
                    f"{scores['rougeL']['fmeasure']:.4f}"
                ])
        
        logger.info(f"CSV已保存: {file_path}")
    
    def _save_improvement_csv(self, file_path: Path) -> None:
        """保存改进分析CSV"""
        import csv
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 写入表头
            writer.writerow([
                'Paper Title',
                'ROUGE-1 Delta', 'ROUGE-1 Improvement%',
                'ROUGE-2 Delta', 'ROUGE-2 Improvement%',
                'ROUGE-L Delta', 'ROUGE-L Improvement%'
            ])
            
            # 写入数据
            for result in self.results:
                improvement = result['improvement']
                writer.writerow([
                    result['paper_title'],
                    f"{improvement['rouge1']['absolute_delta']:.4f}",
                    f"{improvement['rouge1']['relative_improvement_percent']:.2f}%",
                    f"{improvement['rouge2']['absolute_delta']:.4f}",
                    f"{improvement['rouge2']['relative_improvement_percent']:.2f}%",
                    f"{improvement['rougeL']['absolute_delta']:.4f}",
                    f"{improvement['rougeL']['relative_improvement_percent']:.2f}%"
                ])
        
        logger.info(f"改进分析CSV已保存: {file_path}")
