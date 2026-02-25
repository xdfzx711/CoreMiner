"""
结构提取器
从markdown文件中解析和提取文档结构，包括Abstract、Introduction、Conclusion等
"""
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
from src.utils.logger import get_logger

logger = get_logger("CoreMiner.StructureExtractor")


class StructureExtractor:
    """从markdown文件中提取文档结构"""
    
    def __init__(self):
        """初始化提取器"""
        pass
    
    def extract_from_file(self, file_path: str) -> Dict[str, any]:
        """
        从markdown文件中提取文档结构
        
        Args:
            file_path: markdown文件路径
        
        Returns:
            包含提取结果的字典
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.info(f"成功读取文件: {file_path}")
        logger.info(f"文件大小: {len(content)} 字符")
        
        return self.extract_from_text(content)
    
    def extract_from_text(self, text: str) -> Dict[str, any]:
        """
        从文本内容中提取文档结构
        
        Args:
            text: markdown文本内容
        
        Returns:
            包含提取结果的字典
        """
        # 提取标题
        title = self._extract_title(text)
        
        # 提取各个部分
        abstract = self._extract_section(text, r"^#+\s+Abstract", keep_header=False)
        introduction = self._extract_section(text, r"^#+\s+(?:1\s+)?Introduction", keep_header=False)
        conclusion = self._extract_conclusion(text)
        
        # 计算Introduction的1/3位置
        intro_1_3_info = self._calculate_intro_1_3(introduction) if introduction else None
        
        # 获取全文（移除页分割标记）
        full_text = self._clean_page_splits(text)
        
        # 统计信息
        stats = {
            "total_chars": len(text),
            "title_chars": len(title) if title else 0,
            "abstract_chars": len(abstract) if abstract else 0,
            "introduction_chars": len(introduction) if introduction else 0,
            "conclusion_chars": len(conclusion) if conclusion else 0,
        }
        
        result = {
            "title": title,
            "abstract": abstract,
            "introduction": introduction,
            "introduction_1_3": intro_1_3_info.get("text") if intro_1_3_info else None,
            "introduction_1_3_position": intro_1_3_info.get("position") if intro_1_3_info else None,
            "conclusion": conclusion,
            "full_text": full_text,
            "stats": stats,
        }
        
        logger.info("文档结构提取完成")
        logger.info(f"  标题: {len(title)} 字符" if title else "  标题: 未找到")
        logger.info(f"  摘要: {len(abstract)} 字符" if abstract else "  摘要: 未找到")
        logger.info(f"  引言: {len(introduction)} 字符" if introduction else "  引言: 未找到")
        logger.info(f"  结论: {len(conclusion)} 字符" if conclusion else "  结论: 未找到")
        
        return result
    
    def _extract_title(self, text: str) -> Optional[str]:
        """提取文档标题（第一个一级标题）"""
        match = re.search(r"^#\s+(.+?)$", text, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None
    
    def _extract_conclusion(self, text: str) -> Optional[str]:
        """
        提取Conclusion部分
        支持两种形式：
        1. 独立章节标题形式：## Conclusion 或 ## 10 Conclusion
        2. 段落开头形式：Conclusion. （通常在Discussion章节内）
        
        Args:
            text: 完整文本
        
        Returns:
            Conclusion内容，如果未找到则返回None
        """
        # 方法1: 尝试提取标题形式的Conclusion
        conclusion = self._extract_section(text, r"^#+\s+(?:\d+\s+)?Conclusion", keep_header=False)
        
        if conclusion:
            logger.debug("找到标题形式的Conclusion")
            return conclusion
        
        # 方法2: 查找段落开头形式的Conclusion
        # 通常出现在Discussion章节内，以"Conclusion."开头
        pattern = r"(?:^|\n)Conclusion\.\s+(.+?)(?=\n\n|<---|$)"
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        
        if match:
            conclusion_text = "Conclusion. " + match.group(1).strip()
            logger.debug("找到段落形式的Conclusion")
            return conclusion_text
        
        # 方法3: 更宽松的匹配 - 查找Discussion章节中的Conclusion段落
        discussion = self._extract_section(text, r"^#+\s+(?:\d+\s+)?Discussion", keep_header=False)
        if discussion:
            # 在Discussion中查找Conclusion段落
            conclusion_match = re.search(r"Conclusion\.\s+(.+?)(?=\n\n|$)", discussion, re.DOTALL)
            if conclusion_match:
                conclusion_text = "Conclusion. " + conclusion_match.group(1).strip()
                logger.debug("在Discussion章节中找到Conclusion段落")
                return conclusion_text
        
        logger.debug("未找到Conclusion")
        return None
    
    def _extract_section(self, text: str, section_pattern: str, keep_header: bool = False) -> Optional[str]:
        """
        提取指定的章节内容
        
        Args:
            text: 完整文本
            section_pattern: 章节标题的正则表达式
            keep_header: 是否保留章节标题
        
        Returns:
            章节内容，如果未找到则返回None
        """
        # 查找章节开始位置
        section_match = re.search(section_pattern, text, re.MULTILINE | re.IGNORECASE)
        if not section_match:
            return None
        
        start_pos = section_match.start() if not keep_header else section_match.start()
        start_pos = section_match.start()
        
        # 查找下一个同级或更高级的标题
        # 找到当前标题的#数量
        header_line = text[start_pos:section_match.end()]
        current_level = len(re.match(r"^#+", header_line).group())
        
        # 从当前位置之后查找下一个标题
        remaining_text = text[section_match.end():]
        next_header = re.search(r"^#{1," + str(current_level) + r"}\s", remaining_text, re.MULTILINE)
        
        if next_header:
            end_pos = section_match.end() + next_header.start()
            section_content = text[start_pos:end_pos]
        else:
            section_content = text[start_pos:]
        
        # 处理标题
        if not keep_header:
            # 移除第一行（标题行）
            lines = section_content.split('\n')
            section_content = '\n'.join(lines[1:]).strip()
        else:
            section_content = section_content.strip()
        
        return section_content if section_content else None
    
    def _calculate_intro_1_3(self, introduction: str) -> Optional[Dict]:
        """
        计算Introduction后1/3的内容
        
        Args:
            introduction: Introduction的完整文本
        
        Returns:
            包含后1/3位置和文本的字典
        """
        if not introduction:
            return None
        
        # 按段落分割
        paragraphs = introduction.split('\n\n')
        
        total_chars = len(introduction)
        one_third_start = int(total_chars * 0.67)  # 后1/3从67%处开始
        
        # 找到1/3位置的文本（从后1/3开始）
        accumulated_chars = 0
        one_third_text = ""
        one_third_para_count = 0
        para_start_idx = 0
        
        for i, para in enumerate(paragraphs):
            para_end = accumulated_chars + len(para) + 2  # +2 for '\n\n'
            
            # 如果当前段落在后1/3范围内
            if accumulated_chars >= one_third_start or para_end > one_third_start:
                if accumulated_chars < one_third_start:
                    # 部分段落在后1/3范围内
                    offset = one_third_start - accumulated_chars
                    one_third_text += para[offset:] + '\n\n'
                else:
                    # 整个段落在后1/3范围内
                    one_third_text += para + '\n\n'
                
                one_third_para_count += 1
            
            accumulated_chars += len(para) + 2
        
        return {
            "text": one_third_text.strip(),
            "position": {
                "char_count": total_chars - one_third_start,
                "paragraph_count": one_third_para_count,
                "total_chars": total_chars,
                "ratio": 0.33,
                "start_position": one_third_start,
            }
        }
    
    def _clean_page_splits(self, text: str) -> str:
        """
        移除页分割标记
        
        Args:
            text: 原始文本
        
        Returns:
            清洁后的文本
        """
        # 移除页分割标记 <--- Page Split --->
        cleaned = re.sub(r"<---\s+Page Split\s+-+>", "", text)
        # 移除多余的空行
        cleaned = re.sub(r"\n\n\n+", "\n\n", cleaned)
        return cleaned.strip()
    
    def get_sections_list(self, text: str) -> list:
        """
        获取文档中所有的章节列表
        
        Args:
            text: markdown文本
        
        Returns:
            章节列表 [{"level": 1, "title": "...", "start": 0, "end": 100}, ...]
        """
        sections = []
        
        for match in re.finditer(r"^(#+)\s+(.+?)$", text, re.MULTILINE):
            level = len(match.group(1))
            title = match.group(2).strip()
            start = match.start()
            
            sections.append({
                "level": level,
                "title": title,
                "start": start,
            })
        
        # 添加每个章节的结束位置
        for i in range(len(sections)):
            if i < len(sections) - 1:
                sections[i]["end"] = sections[i + 1]["start"]
            else:
                sections[i]["end"] = len(text)
        
        return sections
