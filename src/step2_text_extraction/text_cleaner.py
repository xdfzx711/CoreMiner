"""
文本清洗器

去除文本中的引用、公式、特殊符号等噪声，返回干净的纯文本。
"""

import re
from typing import Dict, Any, List, Optional
import logging

from ..utils.logger import get_logger

logger = get_logger("CoreMiner.TextCleaner")


class TextCleaner:
    """文本清洗器，去除引用、公式、特殊符号等噪声"""
    
    # 引用模式：[1], [1,2], [1-3], (Smith et al., 2020), etc.
    CITATION_PATTERNS = [
        r'\[\d+(?:[-,]\d+)*\]',  # [1], [1,2], [1-3]
        r'\(\s*[A-Z][a-z]+\s+et\s+al\.?,?\s*\d{4}\s*\)',  # (Smith et al., 2020)
        r'\(\s*[A-Z][a-z]+\s+and\s+[A-Z][a-z]+,?\s*\d{4}\s*\)',  # (Smith and Jones, 2020)
        r'\(\s*[A-Z][a-z]+,?\s*\d{4}\s*\)',  # (Smith, 2020)
    ]
    
    # LaTeX 公式模式
    FORMULA_PATTERNS = [
        r'\$\$[^$]+\$\$',  # $$...$$
        r'\$[^$]+\$',  # $...$
        r'\\begin\{equation\}.*?\\end\{equation\}',  # \begin{equation}...\end{equation}
        r'\\begin\{align\*?\}.*?\\end\{align\*?\}',  # \begin{align}...\end{align}
        r'\\[a-zA-Z]+\{[^}]*\}',  # \command{...}
    ]
    
    # 特殊符号和控制字符
    SPECIAL_CHARS = [
        r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]',  # 控制字符
        r'[�]',  # 替换字符
    ]
    
    def __init__(
        self,
        remove_citations: bool = True,
        remove_formulas: bool = True,
        remove_special_chars: bool = True,
        remove_urls: bool = True,
        normalize_whitespace: bool = True,
    ):
        """
        初始化文本清洗器
        
        Args:
            remove_citations: 是否去除引用
            remove_formulas: 是否去除公式
            remove_special_chars: 是否去除特殊字符
            remove_urls: 是否去除URL
            normalize_whitespace: 是否规范化空白字符
        """
        self.remove_citations = remove_citations
        self.remove_formulas = remove_formulas
        self.remove_special_chars = remove_special_chars
        self.remove_urls = remove_urls
        self.normalize_whitespace = normalize_whitespace
        
        # 编译正则表达式以提高性能
        self._compile_patterns()
    
    def _compile_patterns(self):
        """编译正则表达式模式"""
        self.citation_regex = [re.compile(p, re.DOTALL) for p in self.CITATION_PATTERNS]
        self.formula_regex = [re.compile(p, re.DOTALL) for p in self.FORMULA_PATTERNS]
        self.special_char_regex = [re.compile(p) for p in self.SPECIAL_CHARS]
        self.url_regex = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
    
    def clean(self, text: str) -> str:
        """
        清洗文本
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的文本
        """
        if not text:
            return ""
        
        original_length = len(text)
        cleaned = text
        
        # 去除引用
        if self.remove_citations:
            cleaned = self._remove_citations(cleaned)
        
        # 去除公式
        if self.remove_formulas:
            cleaned = self._remove_formulas(cleaned)
        
        # 去除URL
        if self.remove_urls:
            cleaned = self._remove_urls(cleaned)
        
        # 去除特殊字符
        if self.remove_special_chars:
            cleaned = self._remove_special_characters(cleaned)
        
        # 规范化空白字符
        if self.normalize_whitespace:
            cleaned = self._normalize_whitespace(cleaned)
        
        removed_chars = original_length - len(cleaned)
        logger.debug(f"文本清洗完成: {original_length} -> {len(cleaned)} 字符 (移除 {removed_chars})")
        
        return cleaned.strip()
    
    def clean_extracted_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        清洗提取的数据
        
        Args:
            extracted_data: 文本提取器的输出
            
        Returns:
            清洗后的数据
        """
        if not extracted_data.get("success", False):
            logger.warning("输入数据无效，跳过清洗")
            return extracted_data
        
        try:
            result = extracted_data.copy()
            
            # 清洗标题
            if "title" in result:
                result["title"] = self.clean(result["title"])
            
            # 清洗摘要
            if "abstract" in result:
                result["abstract"] = self.clean(result["abstract"])
            
            # 清洗全文
            if "full_text" in result:
                result["full_text"] = self.clean(result["full_text"])
            
            # 清洗各章节
            if "sections" in result:
                cleaned_sections = []
                for section in result["sections"]:
                    cleaned_sections.append({
                        "heading": self.clean(section.get("heading", "")),
                        "content": self.clean(section.get("content", ""))
                    })
                result["sections"] = cleaned_sections
            
            # 更新元数据
            if "metadata" in result:
                result["metadata"]["cleaned"] = True
                result["metadata"]["cleaned_text_length"] = len(result.get("full_text", ""))
            
            logger.info(f"数据清洗成功: {result.get('title', '')[:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"数据清洗失败: {e}")
            return {
                "success": False,
                "error": f"清洗失败: {str(e)}"
            }
    
    def _remove_citations(self, text: str) -> str:
        """去除引用"""
        for regex in self.citation_regex:
            text = regex.sub(' ', text)
        return text
    
    def _remove_formulas(self, text: str) -> str:
        """去除公式"""
        for regex in self.formula_regex:
            text = regex.sub(' [FORMULA] ', text)
        return text
    
    def _remove_urls(self, text: str) -> str:
        """去除URL"""
        return self.url_regex.sub(' ', text)
    
    def _remove_special_characters(self, text: str) -> str:
        """去除特殊字符"""
        for regex in self.special_char_regex:
            text = regex.sub('', text)
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """规范化空白字符"""
        # 将多个空格替换为单个空格
        text = re.sub(r' +', ' ', text)
        # 将多个换行替换为最多两个换行
        text = re.sub(r'\n\n+', '\n\n', text)
        # 移除行首行尾空格
        lines = [line.strip() for line in text.split('\n')]
        return '\n'.join(lines)
    
    def get_cleaning_stats(self, original: str, cleaned: str) -> Dict[str, Any]:
        """
        获取清洗统计信息
        
        Args:
            original: 原始文本
            cleaned: 清洗后的文本
            
        Returns:
            统计信息字典
        """
        original_length = len(original)
        cleaned_length = len(cleaned)
        
        # 计算移除的引用数量
        citation_count = sum(
            len(regex.findall(original))
            for regex in self.citation_regex
        )
        
        # 计算移除的公式数量
        formula_count = sum(
            len(regex.findall(original))
            for regex in self.formula_regex
        )
        
        # 计算移除的URL数量
        url_count = len(self.url_regex.findall(original))
        
        return {
            "original_length": original_length,
            "cleaned_length": cleaned_length,
            "removed_chars": original_length - cleaned_length,
            "removal_rate": (original_length - cleaned_length) / original_length if original_length > 0 else 0,
            "citations_removed": citation_count,
            "formulas_removed": formula_count,
            "urls_removed": url_count,
        }
