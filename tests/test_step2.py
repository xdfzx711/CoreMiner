"""
步骤2测试用例：文本提取与去噪

运行方式：
  pytest tests/test_step2.py -v
  pytest tests/test_step2.py::TestTextExtractor -v
  pytest tests/test_step2.py::TestTextCleaner -v
  pytest tests/test_step2.py::TestRealDataProcessing -v
"""

import sys
import os
import pytest
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.step2_text_extraction import TextExtractor, TextCleaner


class TestTextExtractor:
    """测试文本提取器"""
    
    def test_extract_success(self):
        """测试成功提取文本"""
        extractor = TextExtractor()
        parsed_data = {
            "success": True,
            "pdf_path": "test.pdf",
            "title": "Deep Learning for Computer Vision",
            "authors": ["John Smith", "Jane Doe"],
            "abstract": "This paper presents a novel approach.",
            "text": "1. Introduction\nContent here.\n\n2. Methods\nMore content.",
        }
        
        result = extractor.extract(parsed_data)
        
        assert result["success"] is True
        assert result["title"] == "Deep Learning for Computer Vision"
        assert len(result["authors"]) == 2
        assert len(result["sections"]) > 0
    
    def test_extract_failed_input(self):
        """测试处理失败的输入"""
        extractor = TextExtractor()
        failed_data = {"success": False, "error": "解析失败"}
        
        result = extractor.extract(failed_data)
        assert result["success"] is False
        assert "error" in result
    
    def test_section_splitting(self):
        """测试章节分割"""
        extractor = TextExtractor()
        parsed_data = {
            "success": True,
            "title": "Test",
            "authors": [],
            "abstract": "This is the abstract.",
            "text": """1. Introduction
Introduction content.

2. Methodology
Method content.

3. Conclusion
Conclusion content.""",
        }
        
        result = extractor.extract(parsed_data)
        sections = result["sections"]
        
        # 应该返回Abstract、Introduction、Conclusion
        assert len(sections) == 3
        headings = [s["heading"] for s in sections]
        assert "Abstract" in headings
        assert "Introduction" in headings
        assert "Conclusion" in headings
    
    def test_extract_specific_section(self):
        """测试提取特定章节"""
        extractor = TextExtractor()
        parsed_data = {
            "success": True,
            "title": "Test",
            "authors": [],
            "abstract": "",
            "text": "1. Introduction\nThis introduces the problem.\n\n2. Methods\nMethod details.",
        }
        
        content = extractor.extract_specific_section(parsed_data, ["introduction"])
        assert content is not None
        assert "introduces" in content.lower()
    
    def test_is_section_heading(self):
        """测试章节标题识别"""
        extractor = TextExtractor()
        
        # 应该识别为标题
        assert extractor._is_section_heading("1. Introduction")
        assert extractor._is_section_heading("I. Background")
        assert extractor._is_section_heading("INTRODUCTION")
        assert extractor._is_section_heading("Related Work")
        
        # 不应该识别为标题
        assert not extractor._is_section_heading("This is a long sentence that should not be a heading.")
        assert not extractor._is_section_heading("we conducted experiments")


class TestTextCleaner:
    """测试文本清洗器"""
    
    def test_remove_citations(self):
        """测试去除引用"""
        cleaner = TextCleaner()
        text = "This paper [1] presents a method (Smith et al., 2020). See also [2,3] and [4-6]."
        cleaned = cleaner.clean(text)
        
        assert "[1]" not in cleaned
        assert "[2,3]" not in cleaned
        assert "[4-6]" not in cleaned
        assert "(Smith et al., 2020)" not in cleaned
    
    def test_remove_formulas(self):
        """测试去除公式"""
        cleaner = TextCleaner()
        text = "The formula is $y = wx + b$ and $$E = mc^2$$."
        cleaned = cleaner.clean(text)
        
        assert "$y = wx + b$" not in cleaned
        assert "$$E = mc^2$$" not in cleaned
        assert "[FORMULA]" in cleaned
    
    def test_remove_urls(self):
        """测试去除URL"""
        cleaner = TextCleaner()
        text = "Visit https://example.com for details."
        cleaned = cleaner.clean(text)
        
        assert "https://example.com" not in cleaned
    
    def test_normalize_whitespace(self):
        """测试空白字符规范化"""
        cleaner = TextCleaner()
        text = "This  has   multiple    spaces.\n\n\n\nAnd multiple newlines."
        cleaned = cleaner.clean(text)
        
        assert "  " not in cleaned
        assert "\n\n\n" not in cleaned
    
    def test_clean_extracted_data(self):
        """测试清洗提取的数据"""
        cleaner = TextCleaner()
        extracted_data = {
            "success": True,
            "title": "Deep Learning [1]",
            "authors": ["John Smith"],
            "abstract": "This work (Doe, 2020) presents $x = y$.",
            "full_text": "Introduction [1,2] with formula $z = a + b$.",
            "sections": [{"heading": "1. Introduction", "content": "Text with citations [3]."}],
            "metadata": {}
        }
        
        result = cleaner.clean_extracted_data(extracted_data)
        
        assert result["success"] is True
        assert "[1]" not in result["title"]
        assert "(Doe, 2020)" not in result["abstract"]
        assert "[1,2]" not in result["full_text"]
        assert "[3]" not in result["sections"][0]["content"]
        assert result["metadata"]["cleaned"] is True
    
    def test_cleaning_stats(self):
        """测试清洗统计"""
        cleaner = TextCleaner()
        original = "This [1] has $formula$ and https://url.com"
        cleaned = cleaner.clean(original)
        stats = cleaner.get_cleaning_stats(original, cleaned)
        
        assert "original_length" in stats
        assert "cleaned_length" in stats
        assert "citations_removed" in stats
        assert "formulas_removed" in stats
        assert stats["removed_chars"] > 0
    
    def test_selective_cleaning(self):
        """测试选择性清洗"""
        cleaner = TextCleaner(
            remove_citations=True,
            remove_formulas=False,
            remove_urls=False
        )
        
        text = "This [1] has $formula$ and https://url.com"
        cleaned = cleaner.clean(text)
        
        assert "[1]" not in cleaned
        assert "$formula$" in cleaned
        assert "https://url.com" in cleaned


class TestIntegration:
    """集成测试：提取 + 清洗"""
    
    def test_full_pipeline(self):
        """测试完整的提取和清洗流程"""
        parsed_data = {
            "success": True,
            "title": "Novel Architecture [1]",
            "authors": ["Alice", "Bob"],
            "abstract": "We propose (Smith, 2020) a new method with $loss = -log(p)$.",
            "text": "1. Introduction\nPrevious work [1,2] has limitations.\n\n3. Conclusion\nOur method works well.",
        }
        
        # 提取文本
        extractor = TextExtractor()
        extracted = extractor.extract(parsed_data)
        assert extracted["success"] is True
        
        # 验证只提取了关键章节
        sections = extracted["sections"]
        headings = [s["heading"] for s in sections]
        assert "Abstract" in headings
        assert "Introduction" in headings
        assert "Conclusion" in headings
        
        # 清洗文本
        cleaner = TextCleaner()
        cleaned = cleaner.clean_extracted_data(extracted)
        assert cleaned["success"] is True
        
        # 验证清洗效果
        assert "[1]" not in cleaned["title"]
        assert "(Smith, 2020)" not in cleaned["abstract"]
        assert "novel architecture" in cleaned["title"].lower()
        assert cleaned["metadata"]["cleaned"] is True


class TestRealDataProcessing:
    """真实数据处理测试：从results读取并保存清理后的数据"""
    
    @pytest.mark.integration
    def test_process_real_parsed_data(self):
        """测试处理真实的解析数据"""
        # 定义路径
        results_dir = Path(r"D:\pythonproject\CoreMiner\output\results")
        
        # 查找最新的解析结果文件
        parsed_files = sorted(results_dir.glob("parsed_result_*.json"))
        if not parsed_files:
            pytest.skip("没有找到解析结果文件")
        
        latest_file = parsed_files[-1]
        print(f"\n读取文件: {latest_file}")
        
        # 读取解析数据
        with open(latest_file, "r", encoding="utf-8") as f:
            parsed_data = json.load(f)
        
        assert parsed_data["success"] is True, "解析数据标记为失败"
        
        # 提取文本
        extractor = TextExtractor()
        extracted = extractor.extract(parsed_data)
        
        assert extracted["success"] is True
        print(f"\n提取统计:")
        print(f"  标题: {extracted['title'][:50]}...")
        print(f"  作者数: {len(extracted['authors'])}")
        print(f"  章节数: {len(extracted['sections'])}")
        
        # 清洗文本
        cleaner = TextCleaner()
        cleaned = cleaner.clean_extracted_data(extracted)
        
        assert cleaned["success"] is True
        assert cleaned["metadata"]["cleaned"] is True
        
        # 获取清洗统计
        if "full_text" in cleaned:
            stats = cleaner.get_cleaning_stats(
                extracted.get("full_text", ""),
                cleaned.get("full_text", "")
            )
            print(f"\n清洗统计:")
            print(f"  原始长度: {stats['original_length']}")
            print(f"  清洗后长度: {stats['cleaned_length']}")
            print(f"  移除字符数: {stats['removed_chars']}")
            print(f"  移除引用数: {stats['citations_removed']}")
            print(f"  移除公式数: {stats['formulas_removed']}")
        
        # 保存清洗后的数据
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = results_dir / f"cleaned_result_{timestamp}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)
        
        print(f"\n清洗结果已保存到: {output_file}")
        
        # 验证保存的文件
        assert output_file.exists()
        with open(output_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data["success"] is True
        assert saved_data["metadata"]["cleaned"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
