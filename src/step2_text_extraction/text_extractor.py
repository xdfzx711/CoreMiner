"""
文本提取器

从步骤1的解析结果中提取关键文本内容，包括标题、摘要、正文等。
"""

import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from ..utils.logger import get_logger

logger = get_logger("CoreMiner.TextExtractor")


class TextExtractor:
    """文本提取器，从Grobid解析结果中提取结构化文本"""
    
    def __init__(self):
        """初始化文本提取器"""
        # 改进的章节标题模式
        self.section_pattern = re.compile(
            r'^(?:\d+\.?\s*|\([a-z]\)\s*|[IVXLCDM]+\.?\s*|[A-Z]\.?\s*)?[A-Z][a-zA-Z\s]*(?:Overview|Introduction|Background|Related Work|Methodology|Method|Approach|Experiments?|Results?|Evaluation|Discussion|Conclusion|Future Work|Acknowledgment|References?)?',
            re.MULTILINE | re.IGNORECASE
        )
        
        # 常见的章节关键词
        self.section_keywords = {
            'introduction', 'background', 'related work', 'methodology', 'method', 'approach',
            'experiment', 'result', 'evaluation', 'discussion', 'conclusion', 'future work',
            'acknowledgment', 'reference', 'abstract', 'summary', 'overview', 'motivation',
            'problem statement', 'threat model', 'attack', 'security', 'defense', 'mitigation'
        }
    
    def extract(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从步骤1的解析结果中提取文本
        
        Args:
            parsed_data: 步骤1的解析结果字典
            
        Returns:
            提取的文本数据
            {
                "title": str,
                "authors": List[str],
                "abstract": str,
                "sections": List[Dict[str, str]],  # 只包含Introduction、Conclusion
                "full_text": str,
                "metadata": Dict
            }
        """
        if not parsed_data.get("success", False):
            logger.error(f"输入数据解析失败: {parsed_data.get('error', '未知错误')}")
            return {
                "success": False,
                "error": "输入数据无效"
            }
        
        try:
            # 提取基础信息
            title = parsed_data.get("title", "").strip()
            authors = parsed_data.get("authors", [])
            abstract = parsed_data.get("abstract", "").strip()
            full_text = parsed_data.get("text", "").strip()
            
            # 分割并筛选特定章节
            # 注意:由于文本可能未按行分割好章节标题,我们直接传入full_text
            all_sections = self._split_sections(full_text)
            # 使用正则表达式直接从文本中提取关键章节
            filtered_sections = self._filter_key_sections_from_text(full_text, abstract)
            
            result = {
                "success": True,
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "sections": filtered_sections,
                "full_text": full_text,
                "metadata": {
                    "pdf_path": parsed_data.get("pdf_path", ""),
                    "num_sections": len(filtered_sections),
                    "text_length": len(full_text),
                    "has_abstract": len(abstract) > 0,
                    "filtered_sections": ["Abstract", "Introduction", "Conclusion"]
                }
            }
            
            logger.info(
                f"文本提取成功: {title[:50]}..., "
                f"筛选出 {len(filtered_sections)} 个关键章节"
            )
            return result
            
        except Exception as e:
            logger.error(f"文本提取失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _split_sections(self, text: str) -> List[Dict[str, str]]:
        """
        将文本分割为章节
        使用正则表达式直接匹配章节标题,支持章节标题和内容连在一起的情况
        
        Args:
            text: 全文文本
            
        Returns:
            章节列表 [{"heading": "", "content": ""}]
        """
        if not text:
            return []
        
        sections = []
        
        # 匹配常见的章节标题模式(单词边界处的关键词)
        section_regex = re.compile(
            r'\b(Introduction|Background|Related Work|Methodology|Method|Methods|'
            r'Approach|Experiment|Experiments|Results|Result|Evaluation|Discussion|'
            r'Conclusion|Conclusions|Future Work|Acknowledgment|Acknowledgments|'
            r'References|Abstract|Summary|Overview|Motivation)\b',
            re.IGNORECASE
        )
        
        # 查找所有章节标题位置
        matches = list(section_regex.finditer(text))
        
        if not matches:
            logger.debug("未找到章节标题,返回空列表")
            return []
        
        # 提取每个章节的内容
        for i, match in enumerate(matches):
            heading = match.group(1).capitalize()
            start_pos = match.end()
            
            # 确定内容结束位置(下一个章节标题的开始,或文本结尾)
            if i < len(matches) - 1:
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)
            
            content = text[start_pos:end_pos].strip()
            
            # 只保存有实际内容的章节
            if content:
                sections.append({
                    "heading": heading,
                    "content": content
                })
        
        logger.debug(f"文本分割为 {len(sections)} 个章节")
        return sections
    
    def _filter_key_sections_from_text(self, full_text: str, abstract: str) -> List[Dict[str, str]]:
        """
        直接从完整文本中提取关键章节：Abstract、Introduction、Conclusion
        
        使用正则表达式直接从文本中提取关键章节,而不依赖换行符分割
        
        Args:
            full_text: 完整文本
            abstract: 摘要文本
            
        Returns:
            筛选后的章节列表
        """
        key_sections = []
        
        # 如果有摘要，添加到结果中
        if abstract.strip():
            key_sections.append({
                "heading": "Abstract",
                "content": abstract.strip()
            })
        
        # 使用正则表达式直接提取Introduction和Conclusion
        # 匹配 "Introduction" 到下一个大章节或"Conclusion"之间的内容
        intro_pattern = r'Introduction(.*?)(?=(?:\d+\.?\s*[A-Z][a-z]+|Conclusion|$))'
        conclusion_pattern = r'Conclusion(.*?)(?=(?:\d+\.?\s*[A-Z][a-z]+|References?|Acknowledgment|$))'
        
        intro_match = re.search(intro_pattern, full_text, re.DOTALL | re.IGNORECASE)
        if intro_match:
            intro_content = intro_match.group(1).strip()
            if intro_content:  # 确保不是空内容
                key_sections.append({
                    "heading": "Introduction",
                    "content": intro_content
                })
                logger.debug(f"提取Introduction成功: {len(intro_content)} 字符")
        
        conclusion_match = re.search(conclusion_pattern, full_text, re.DOTALL | re.IGNORECASE)
        if conclusion_match:
            conclusion_content = conclusion_match.group(1).strip()
            if conclusion_content:  # 确保不是空内容
                key_sections.append({
                    "heading": "Conclusion",
                    "content": conclusion_content
                })
                logger.debug(f"提取Conclusion成功: {len(conclusion_content)} 字符")
        
        logger.info(f"筛选出 {len(key_sections)} 个关键章节: {[s['heading'] for s in key_sections]}")
        return key_sections
    
    def _filter_key_sections(self, sections: List[Dict[str, str]], abstract: str) -> List[Dict[str, str]]:
        """
        筛选出关键章节：Abstract、Introduction、Conclusion
        
        使用正则表达式直接从文本中提取关键章节,而不依赖换行符分割
        
        Args:
            sections: 所有章节列表(可能未被正确分割)
            abstract: 摘要文本
            
        Returns:
            筛选后的章节列表
        """
        key_sections = []
        
        # 如果有摘要，添加到结果中
        if abstract.strip():
            key_sections.append({
                "heading": "Abstract",
                "content": abstract.strip()
            })
        
        # 从所有章节中重新组合完整文本
        full_text = "\n".join([s.get("content", "") for s in sections if s.get("content")])
        if not full_text:
            # 如果分割后的章节内容为空,尝试直接从第一个章节获取
            full_text = sections[0].get("content", "") if sections else ""
        
        # 使用正则表达式直接提取Introduction和Conclusion
        # 匹配 "Introduction" 到下一个大章节或"Conclusion"之间的内容
        intro_pattern = r'Introduction(.*?)(?=(?:\d+\.?\s*[A-Z][a-z]+|Conclusion|$))'
        conclusion_pattern = r'Conclusion(.*?)(?=(?:\d+\.?\s*[A-Z][a-z]+|References?|Acknowledgment|$))'
        
        intro_match = re.search(intro_pattern, full_text, re.DOTALL | re.IGNORECASE)
        if intro_match:
            intro_content = intro_match.group(1).strip()
            if intro_content:  # 确保不是空内容
                key_sections.append({
                    "heading": "Introduction",
                    "content": intro_content
                })
                logger.debug(f"提取Introduction成功: {len(intro_content)} 字符")
        
        conclusion_match = re.search(conclusion_pattern, full_text, re.DOTALL | re.IGNORECASE)
        if conclusion_match:
            conclusion_content = conclusion_match.group(1).strip()
            if conclusion_content:  # 确保不是空内容
                key_sections.append({
                    "heading": "Conclusion",
                    "content": conclusion_content
                })
                logger.debug(f"提取Conclusion成功: {len(conclusion_content)} 字符")
        
        logger.info(f"筛选出 {len(key_sections)} 个关键章节: {[s['heading'] for s in key_sections]}")
        return key_sections
    
    def _is_section_heading(self, line: str) -> bool:
        """
        判断是否为章节标题
        
        Args:
            line: 文本行
            
        Returns:
            是否为章节标题
        """
        # 标题通常较短且不是完整的句子
        if len(line) > 80:  # 进一步缩短长度限制
            return False
        
        # 跳过明显的句子（包含多个句子特征）
        if line.count('.') > 1 or line.count(',') > 2:
            return False
        
        # 移除常见的前缀和后缀
        clean_line = re.sub(r'^[\d\.\(\)\-\s]*', '', line).strip()
        clean_line = re.sub(r'[\.\s]*$', '', clean_line).strip()
        
        # 检查是否匹配章节模式
        if self.section_pattern.match(line):
            return True
        
        # 检查是否包含章节关键词
        line_lower = line.lower()
        if any(kw in line_lower for kw in self.section_keywords):
            # 确保不是句子中的关键词，且长度合理
            if len(line.split()) <= 6 and not line.endswith('.'):
                return True
        
        # 检查格式特征
        # 1. 全大写且较短
        if line.isupper() and 3 <= len(line) <= 30:
            return True
        
        # 2. 首字母大写，包含数字编号
        if re.match(r'^\d+\.?\s+[A-Z]', line):
            return True
        
        # 3. 罗马数字编号
        if re.match(r'^[IVXLCDM]+\.?\s+[A-Z]', line):
            return True
        
        # 4. 字母编号
        if re.match(r'^[a-zA-Z]\.?\s+[A-Z]', line):
            return True
        
        return False
    
    def extract_specific_section(
        self,
        parsed_data: Dict[str, Any],
        section_keywords: List[str]
    ) -> Optional[str]:
        """
        提取特定章节的内容
        
        Args:
            parsed_data: 步骤1的解析结果
            section_keywords: 章节关键词列表（如 ["introduction", "background"]）
            
        Returns:
            匹配的章节内容，如果未找到返回 None
        """
        extracted = self.extract(parsed_data)
        if not extracted.get("success"):
            return None
        
        # 搜索匹配的章节
        for section in extracted.get("sections", []):
            heading = section.get("heading", "").lower()
            if any(kw.lower() in heading for kw in section_keywords):
                logger.info(f"找到匹配章节: {section['heading']}")
                return section.get("content", "")
        
        logger.warning(f"未找到匹配章节，关键词: {section_keywords}")
        return None
