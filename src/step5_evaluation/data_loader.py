"""
数据加载器模块
负责加载和匹配参考摘要、原始摘要和优化后的摘要
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
from datetime import datetime

from src.utils.logger import get_logger

logger = get_logger("CoreMiner.Step5.DataLoader")


class EvaluationDataLoader:
    """评估数据加载器"""
    
    def __init__(
        self,
        manual_summary_path: str,
        llm_results_dir: str,
        refine_results_dir: str,
        similarity_threshold: float = 0.85
    ):
        """
        初始化数据加载器
        
        Args:
            manual_summary_path: Manual_Summary_Generation.json的路径
            llm_results_dir: llm_results目录路径
            refine_results_dir: refine_results目录路径
            similarity_threshold: 标题匹配的相似度阈值
        """
        self.manual_summary_path = Path(manual_summary_path)
        self.llm_results_dir = Path(llm_results_dir)
        self.refine_results_dir = Path(refine_results_dir)
        self.similarity_threshold = similarity_threshold
        
        # 数据缓存
        self.manual_summaries: Dict[str, str] = {}
        self.llm_results: List[Dict] = []
        self.refine_results: List[Dict] = []
        self.evaluation_pairs: List[Dict] = []
    
    def load_all_data(self) -> None:
        """加载所有数据"""
        logger.info("开始加载评估数据...")
        
        # 加载参考摘要
        self._load_manual_summaries()
        
        # 加载LLM结果
        self._load_llm_results()
        
        # 加载Refine结果
        self._load_refine_results()
        
        # 匹配数据
        self._match_summaries()
        
        logger.info(f"数据加载完成。共匹配到 {len(self.evaluation_pairs)} 对数据")
    
    def _load_manual_summaries(self) -> None:
        """加载人工标注的参考摘要"""
        logger.info(f"加载参考摘要: {self.manual_summary_path}")
        
        try:
            with open(self.manual_summary_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 解析JSON结构
            if isinstance(data, list):
                for item in data:
                    title = item.get('title', '')
                    summary = item.get('summary', '')
                    if title and summary:
                        self.manual_summaries[title] = summary
            elif isinstance(data, dict):
                # 如果是嵌套字典结构
                for item in data.values():
                    if isinstance(item, dict):
                        title = item.get('title', '')
                        summary = item.get('summary', '')
                        if title and summary:
                            self.manual_summaries[title] = summary
            
            logger.info(f"成功加载 {len(self.manual_summaries)} 篇参考摘要")
            
        except Exception as e:
            logger.error(f"加载参考摘要失败: {e}")
            raise
    
    def _load_llm_results(self) -> None:
        """加载LLM提取结果"""
        logger.info(f"扫描LLM结果目录: {self.llm_results_dir}")
        
        try:
            llm_files = list(self.llm_results_dir.glob("core_contributions_*.json"))
            
            for file_path in llm_files:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data['_source_file'] = str(file_path)
                    self.llm_results.append(data)
            
            logger.info(f"成功加载 {len(self.llm_results)} 个LLM结果文件")
            
        except Exception as e:
            logger.error(f"加载LLM结果失败: {e}")
            raise
    
    def _load_refine_results(self) -> None:
        """加载Refine优化结果"""
        logger.info(f"扫描Refine结果目录: {self.refine_results_dir}")
        
        try:
            refine_files = list(self.refine_results_dir.glob("refine_record_*.json"))
            
            for file_path in refine_files:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data['_source_file'] = str(file_path)
                    self.refine_results.append(data)
            
            logger.info(f"成功加载 {len(self.refine_results)} 个Refine结果文件")
            
        except Exception as e:
            logger.error(f"加载Refine结果失败: {e}")
            raise
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        计算两个标题的相似度
        
        Args:
            title1: 标题1
            title2: 标题2
            
        Returns:
            相似度分数 (0-1)
        """
        # 标准化处理
        t1 = title1.lower().strip()
        t2 = title2.lower().strip()
        
        # 使用SequenceMatcher计算相似度
        similarity = SequenceMatcher(None, t1, t2).ratio()
        
        return similarity
    
    def _find_matching_manual_summary(self, paper_title: str) -> Optional[Tuple[str, str]]:
        """
        为给定的论文标题找到最匹配的参考摘要
        
        Args:
            paper_title: 论文标题
            
        Returns:
            (匹配的标题, 摘要) 或 None
        """
        best_match = None
        best_similarity = 0.0
        
        for ref_title, ref_summary in self.manual_summaries.items():
            similarity = self._calculate_title_similarity(paper_title, ref_title)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = (ref_title, ref_summary)
        
        # 只返回超过阈值的匹配
        if best_similarity >= self.similarity_threshold:
            logger.debug(f"匹配成功: '{paper_title[:50]}...' <-> '{best_match[0][:50]}...' (相似度: {best_similarity:.2f})")
            return best_match
        else:
            logger.warning(f"未找到匹配: '{paper_title[:50]}...' (最高相似度: {best_similarity:.2f})")
            return None
    
    def _match_summaries(self) -> None:
        """匹配所有摘要数据"""
        logger.info("开始匹配摘要数据...")
        
        for refine_data in self.refine_results:
            paper_title = refine_data.get('paper_title', '')
            
            # 查找匹配的参考摘要
            match_result = self._find_matching_manual_summary(paper_title)
            
            if match_result is None:
                logger.warning(f"跳过未匹配的论文: {paper_title}")
                continue
            
            matched_title, reference_summary = match_result
            
            # 查找对应的LLM结果
            original_summary = None
            llm_source_file = None
            
            for llm_data in self.llm_results:
                llm_title = llm_data.get('title', '')
                if self._calculate_title_similarity(paper_title, llm_title) >= self.similarity_threshold:
                    original_summary = llm_data.get('contributions_summary', '')
                    llm_source_file = llm_data.get('_source_file')
                    break
            
            if original_summary is None:
                logger.warning(f"未找到对应的LLM结果: {paper_title}")
                continue
            
            # 构建评估对
            evaluation_pair = {
                'paper_title': paper_title,
                'matched_reference_title': matched_title,
                'reference_summary': reference_summary,
                'original_summary': original_summary,
                'final_summary': refine_data.get('final_summary', ''),
                'source_files': {
                    'llm_result': llm_source_file,
                    'refine_result': refine_data.get('_source_file')
                },
                'metadata': {
                    'validation_time': refine_data.get('validation_time'),
                    'model_used': None  # 从llm_data中提取
                }
            }
            
            # 添加模型信息
            for llm_data in self.llm_results:
                if llm_data.get('_source_file') == llm_source_file:
                    evaluation_pair['metadata']['model_used'] = llm_data.get('model_used')
                    break
            
            self.evaluation_pairs.append(evaluation_pair)
        
        logger.info(f"匹配完成，共生成 {len(self.evaluation_pairs)} 对评估数据")
    
    def save_evaluation_pairs(self, output_path: str) -> None:
        """
        保存匹配好的评估数据对
        
        Args:
            output_path: 输出文件路径
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.evaluation_pairs, f, indent=2, ensure_ascii=False)
        
        logger.info(f"评估数据对已保存到: {output_file}")
    
    def get_evaluation_pairs(self) -> List[Dict]:
        """获取评估数据对"""
        return self.evaluation_pairs
    
    def get_statistics(self) -> Dict:
        """获取数据统计信息"""
        return {
            'total_reference_summaries': len(self.manual_summaries),
            'total_llm_results': len(self.llm_results),
            'total_refine_results': len(self.refine_results),
            'matched_pairs': len(self.evaluation_pairs),
            'match_rate': len(self.evaluation_pairs) / len(self.refine_results) if self.refine_results else 0
        }
