"""
文本提取器
从结构提取器的输出中进一步提取和清洁文本
"""
import json
from pathlib import Path
from typing import Dict, Optional
from src.utils.logger import get_logger
from src.step2_text_extraction.structure_extractor import StructureExtractor
from src.step2_text_extraction.text_cleaner import TextCleaner

logger = get_logger("CoreMiner.TextExtractor")


class TextExtractor:
    """文本提取器，从markdown文件提取和清洁文本"""
    
    def __init__(self):
        """初始化提取器"""
        self.structure_extractor = StructureExtractor()
        self.text_cleaner = TextCleaner()
    
    def extract_from_file(self, mmd_file: str) -> Dict[str, any]:
        """
        从mmd文件中提取和清洁文本
        
        Args:
            mmd_file: markdown文件路径
        
        Returns:
            包含提取和清洁结果的字典
        """
        logger.info(f"开始从文件提取文本: {mmd_file}")
        
        # 第一步：提取文档结构
        structure = self.structure_extractor.extract_from_file(mmd_file)
        
        # 第二步：对各部分进行清洁
        result = {
            "source_file": str(mmd_file),
            "title": structure.get("title"),
            "original": {
                "abstract": structure.get("abstract"),
                "introduction": structure.get("introduction"),
                "introduction_1_3": structure.get("introduction_1_3"),
                "conclusion": structure.get("conclusion"),
                "full_text": structure.get("full_text"),
            },
            "cleaned": {},
            "stats": {},
        }
        
        # 清洁各部分
        for part_name, part_text in result["original"].items():
            if part_text:
                cleaned_result = self.text_cleaner.clean(part_text)
                result["cleaned"][part_name] = cleaned_result["cleaned_text"]
                result["stats"][part_name] = cleaned_result["stats"]
            else:
                result["cleaned"][part_name] = None
                result["stats"][part_name] = None
        
        # 添加结构信息
        result["structure"] = {
            "stats": structure.get("stats"),
            "sections": self.structure_extractor.get_sections_list(structure.get("full_text", "")),
        }
        
        logger.info("文本提取和清洁完成")
        
        return result
    
    def save_result(self, result: Dict, output_dir: str) -> str:
        """
        保存提取结果为JSON文件
        
        Args:
            result: 提取结果字典
            output_dir: 输出目录
        
        Returns:
            保存的文件路径
        """
        from src.utils.file_handler import FileHandler
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名 - 优先使用论文标题
        title = result.get('title')
        sanitized_title = FileHandler.sanitize_title(title) if title else None
        
        if sanitized_title:
            output_file = output_dir / f"extracted_result_{sanitized_title}.json"
        else:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"extracted_result_{timestamp}.json"
        
        # 保存为JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"结果已保存: {output_file}")
        
        return str(output_file)
    
    def extract_and_save(self, mmd_file: str, output_dir: str) -> str:
        """
        一步完成：提取并保存结果
        
        Args:
            mmd_file: markdown文件路径
            output_dir: 输出目录
        
        Returns:
            保存的文件路径
        """
        result = self.extract_from_file(mmd_file)
        return self.save_result(result, output_dir)
