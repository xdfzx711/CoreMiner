"""
全文直接提取模块
完全独立的模块，用于对比实验
"""
from .fulltext_extractor import FullTextExtractor
from .data_models import FullTextResult

__all__ = ['FullTextExtractor', 'FullTextResult']
