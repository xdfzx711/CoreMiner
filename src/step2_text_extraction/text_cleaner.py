"""
文本清洗器
从markdown文本中清洗噪声，包括移除/替换引用、公式、图表等
"""
import re
from typing import Dict, Optional, Tuple
from src.utils.logger import get_logger

logger = get_logger("CoreMiner.TextCleaner")




class TextCleaner:
    """文本清洗器，移除和替换各种特殊元素"""
    
    def __init__(self):
        """初始化清洁器"""
        # 引用符号模式 [1], [12], [1,2], [1-3]
        self.citation_pattern = r'\[\d+(?:[,\-]\d+)*\]'
        
        # LaTeX公式模式
        self.latex_inline_pattern = r'\\\(.*?\\\)'  # \(...\)
        self.latex_block_pattern = r'\\\\\(.*?\\\\\)'  # \\(...\\)
        self.math_pattern = r'\$\$?[^\$]+\$\$?'  # $...$ 或 $$...$$
        self.equation_pattern = r'\\begin\{[^}]*\}.*?\\end\{[^}]*\}'  # \begin{eq}...\end{eq}
        
        # 图片和表格模式
        self.image_pattern = r'!\[.*?\]\(.*?\)'  # ![...](...)
        self.table_pattern = r'<table>.*?</table>'  # <table>...</table>
        self.figure_text_pattern = r'(Figure|Fig\.)\s+\d+[a-z]?'  # Figure X, Fig. X
        self.table_text_pattern = r'(Table|Tab\.)\s+\d+[a-z]?'  # Table X, Tab. X
        
        # 其他特殊元素
        self.html_tag_pattern = r'<[^>]+>'  # HTML标签
        self.page_split_pattern = r'<---\s+Page Split\s+-+>'  # 页分割标记
        self.center_pattern = r'<center>(.*?)</center>'  # <center>...</center>
    
    def clean(self, text: str) -> Dict[str, any]:
        """
        清洁文本（按顺序处理各种特殊元素）
        
        Args:
            text: 原始文本
        
        Returns:
            包含清洁后文本和统计信息的字典
        """
        logger.info(f"开始清洁文本，原始长度: {len(text)}")
        
        cleaned = text
        stats = {
            "original_length": len(text),
            "citations_removed": 0,
            "formulas_removed": 0,
            "figures_removed": 0,
            "tables_removed": 0,
            "html_tags_removed": 0,
        }
        
        # 1. 移除引用符号
        cleaned, cite_count = self._clean_citations(cleaned)
        stats["citations_removed"] = cite_count
        
        # 2. 移除/替换LaTeX公式
        cleaned, formula_count = self._clean_formulas(cleaned)
        stats["formulas_removed"] = formula_count
        
        # 3. 移除"Figure X"和"Table X"文本引用
        cleaned, fig_count = self._clean_figure_references(cleaned)
        stats["figures_removed"] = fig_count
        
        # 4. 移除图片和表格
        cleaned, table_count = self._clean_tables(cleaned)
        stats["tables_removed"] = table_count
        cleaned, image_count = self._clean_images(cleaned)
        stats["figures_removed"] += image_count
        
        # 5. 移除HTML标签和特殊标记
        cleaned, html_count = self._clean_html_tags(cleaned)
        stats["html_tags_removed"] = html_count
        
        # 6. 移除页分割标记
        cleaned = self._clean_page_splits(cleaned)
        
        # 7. 规范化空格和换行
        cleaned = self._normalize_whitespace(cleaned)
        
        # 8. 处理特殊Unicode字符
        cleaned = self._clean_unicode_chars(cleaned)
        
        stats["final_length"] = len(cleaned)
        stats["reduction_rate"] = round((1 - len(cleaned) / len(text)) * 100, 2) if len(text) > 0 else 0
        
        logger.info(f"清洁完成，最终长度: {len(cleaned)}")
        logger.info(f"  移除引用: {stats['citations_removed']} 个")
        logger.info(f"  移除公式: {stats['formulas_removed']} 个")
        logger.info(f"  移除图表引用: {stats['figures_removed']} 个")
        logger.info(f"  移除表格: {stats['tables_removed']} 个")
        logger.info(f"  移除HTML标签: {stats['html_tags_removed']} 个")
        logger.info(f"  文本缩减: {stats['reduction_rate']}%")
        
        return {
            "cleaned_text": cleaned,
            "stats": stats,
        }
    
    def _clean_citations(self, text: str) -> Tuple[str, int]:
        """
        移除引用符号 [1], [12] → 移除
        如果需要保留为<REF>，可以修改这里
        """
        matches = list(re.finditer(self.citation_pattern, text))
        count = len(matches)
        
        # 直接移除（不留痕迹）
        cleaned = re.sub(self.citation_pattern, '', text)
        
        return cleaned, count
    
    def _clean_formulas(self, text: str) -> Tuple[str, int]:
        """移除LaTeX公式"""
        count = 0
        cleaned = text
        
        # 移除 \(...\) 格式
        matches = list(re.finditer(self.latex_inline_pattern, cleaned, re.DOTALL))
        count += len(matches)
        cleaned = re.sub(self.latex_inline_pattern, '<EQ>', cleaned, flags=re.DOTALL)
        
        # 移除 \\(...\\) 格式
        matches = list(re.finditer(self.latex_block_pattern, cleaned, re.DOTALL))
        count += len(matches)
        cleaned = re.sub(self.latex_block_pattern, '<EQ>', cleaned, flags=re.DOTALL)
        
        # 移除 $...$ 或 $$...$$ 格式
        matches = list(re.finditer(self.math_pattern, cleaned, re.DOTALL))
        count += len(matches)
        cleaned = re.sub(self.math_pattern, '<EQ>', cleaned, flags=re.DOTALL)
        
        # 移除 \begin{equation}...\end{equation} 格式
        matches = list(re.finditer(self.equation_pattern, cleaned, re.DOTALL | re.IGNORECASE))
        count += len(matches)
        cleaned = re.sub(self.equation_pattern, '<EQ>', cleaned, flags=re.DOTALL | re.IGNORECASE)
        
        return cleaned, count
    
    def _clean_figure_references(self, text: str) -> Tuple[str, int]:
        """移除"Figure X"和"Table X"文本引用"""
        # 移除 "Figure 1", "Fig. 1" 等
        cleaned = re.sub(self.figure_text_pattern, '<FIG>', text, flags=re.IGNORECASE)
        count = len(re.findall(self.figure_text_pattern, text, flags=re.IGNORECASE))
        
        # 移除 "Table 1", "Tab. 1" 等
        cleaned = re.sub(self.table_text_pattern, '<FIG>', cleaned, flags=re.IGNORECASE)
        count += len(re.findall(self.table_text_pattern, text, flags=re.IGNORECASE))
        
        return cleaned, count
    
    def _clean_tables(self, text: str) -> Tuple[str, int]:
        """移除HTML表格"""
        matches = list(re.finditer(self.table_pattern, text, re.DOTALL | re.IGNORECASE))
        count = len(matches)
        
        cleaned = re.sub(self.table_pattern, '<FIG>', text, flags=re.DOTALL | re.IGNORECASE)
        
        return cleaned, count
    
    def _clean_images(self, text: str) -> Tuple[str, int]:
        """移除图片引用"""
        matches = list(re.finditer(self.image_pattern, text))
        count = len(matches)
        
        cleaned = re.sub(self.image_pattern, '<FIG>', text)
        
        return cleaned, count
    
    def _clean_html_tags(self, text: str) -> Tuple[str, int]:
        """移除HTML标签"""
        # 先处理 <center> 标签的内容
        cleaned = re.sub(self.center_pattern, r'\1', text, flags=re.DOTALL)
        
        # 移除所有其他HTML标签
        matches = list(re.finditer(self.html_tag_pattern, cleaned))
        count = len(matches)
        
        cleaned = re.sub(self.html_tag_pattern, '', cleaned)
        
        return cleaned, count
    
    def _clean_page_splits(self, text: str) -> str:
        """移除页分割标记"""
        return re.sub(self.page_split_pattern, '', text, flags=re.IGNORECASE)
    
    def _normalize_whitespace(self, text: str) -> str:
        """规范化空格和换行"""
        # 将多个换行符合并为两个
        text = re.sub(r'\n\n\n+', '\n\n', text)
        
        # 将多个空格合并为一个
        text = re.sub(r'[ \t]{2,}', ' ', text)
        
        # 移除行尾的空格
        text = re.sub(r' +\n', '\n', text)
        
        # 移除行首的空格
        text = re.sub(r'\n +', '\n', text)
        
        return text.strip()
    
    def _clean_unicode_chars(self, text: str) -> str:
        """处理特殊的Unicode字符"""
        # 移除零宽字符
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
        
        # 移除其他特殊控制字符（但保留正常的Unicode文本）
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
        
        return text


def clean_text(text: str) -> Dict[str, any]:
    """
    便捷函数：清洁文本
    
    Args:
        text: 原始文本
    
    Returns:
        清洁后的文本和统计信息
    """
    cleaner = TextCleaner()
    return cleaner.clean(text)
