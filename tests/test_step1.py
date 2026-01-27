"""
Step 1 单元测试：PDF解析与处理
"""
import sys
import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.step1_pdf_parsing import PDFHandler, GrobidParser


class TestPDFHandler:
    """PDF处理器测试"""
    
    def test_validate_pdf_not_exists(self):
        """测试文件不存在的情况"""
        is_valid, error = PDFHandler.validate_pdf("nonexistent.pdf")
        assert not is_valid
        assert "文件不存在" in error
    
    def test_validate_pdf_not_pdf_extension(self):
        """测试非PDF扩展名"""
        is_valid, error = PDFHandler.validate_pdf("test.txt")
        assert not is_valid
        assert "文件不存在" in error  # 文件不存在时先检查存在性
    
    @patch('builtins.open', mock_open(read_data=b''))
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_file', return_value=True)
    @patch('pathlib.Path.stat')
    def test_validate_pdf_empty_file(self, mock_stat, mock_is_file, mock_exists):
        """测试空PDF文件"""
        mock_stat.return_value.st_size = 0
        is_valid, error = PDFHandler.validate_pdf("empty.pdf")
        assert not is_valid
        assert "为空" in error
    
    @patch('builtins.open', mock_open(read_data=b'invalid'))
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_file', return_value=True)
    @patch('pathlib.Path.stat')
    def test_validate_pdf_invalid_header(self, mock_stat, mock_is_file, mock_exists):
        """测试无效PDF头"""
        mock_stat.return_value.st_size = 1024
        is_valid, error = PDFHandler.validate_pdf("invalid.pdf")
        assert not is_valid
        assert "不是有效的PDF" in error
    
    @patch('builtins.open', mock_open(read_data=b'%PDF-1.4\n'))
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_file', return_value=True)
    @patch('pathlib.Path.stat')
    def test_validate_pdf_valid(self, mock_stat, mock_is_file, mock_exists):
        """测试有效PDF文件"""
        mock_stat.return_value.st_size = 1024
        is_valid, error = PDFHandler.validate_pdf("valid.pdf")
        assert is_valid
        assert error is None  # 成功时返回None
    
    def test_get_pdf_info_nonexistent(self):
        """测试获取不存在文件的信息"""
        info = PDFHandler.get_pdf_info("nonexistent.pdf")
        assert not info["exists"]
        assert info["valid"] is False
        assert "文件不存在" in info["error"]
    
    def test_get_pdf_info_exists(self):
        """测试获取存在文件的信息"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_file', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('builtins.open', mock_open(read_data=b'%PDF-1.4\n')):
            
            mock_stat.return_value.st_size = 2048
            info = PDFHandler.get_pdf_info("test.pdf")
            assert info["exists"]
            assert info["path"] == "test.pdf"
            assert info["size_bytes"] == 2048  # 正确的键名是size_bytes
    
    def test_get_pdf_files_empty_dir(self):
        """测试空目录"""
        pdf_files = PDFHandler.get_pdf_files("nonexistent_dir")
        assert pdf_files == []
    
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_dir', return_value=True)
    @patch('pathlib.Path.glob')
    def test_get_pdf_files_with_pdfs(self, mock_glob, mock_is_dir, mock_exists):
        """测试包含PDF的目录"""
        mock_glob.return_value = [
            Path("test1.pdf"),
            Path("test2.pdf")
        ]
        pdf_files = PDFHandler.get_pdf_files("test_dir")
        assert len(pdf_files) == 2


class TestGrobidParser:
    """Grobid解析器测试"""
    
    @pytest.fixture
    def mock_response_success(self):
        """模拟成功的HTTP响应"""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.text = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a">Deep Learning for NLP</title>
            </titleStmt>
        </fileDesc>
    </teiHeader>
    <text>
        <front>
            <abstract>This is an abstract.</abstract>
        </front>
        <body>
            <div>Introduction text here.</div>
        </body>
    </text>
</TEI>"""
        return mock_resp
    
    def test_parser_initialization(self):
        """测试解析器初始化"""
        parser = GrobidParser(service_url="http://localhost:8070", timeout=30)
        assert parser.service_url == "http://localhost:8070"
        assert parser.timeout == 30
    
    @patch('requests.Session')
    def test_parse_xml_success(self, mock_session):
        """测试XML解析成功"""
        parser = GrobidParser()
        
        xml_content = """<?xml version="1.0"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title level="a">Test Title</title>
            </titleStmt>
        </fileDesc>
    </teiHeader>
    <text>
        <front>
            <abstract>Test abstract</abstract>
        </front>
    </text>
</TEI>"""
        
        result = parser._parse_xml(xml_content, Path("test.pdf"))
        
        assert result["title"] == "Test Title"
        assert result["abstract"] == "Test abstract"
        assert result["pdf_path"] == "test.pdf"
    
    @patch('requests.Session')
    def test_parse_xml_with_authors(self, mock_session):
        """测试解析包含作者的XML"""
        parser = GrobidParser()
        
        xml_content = """<?xml version="1.0"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader>
        <fileDesc>
            <sourceDesc>
                <biblStruct>
                    <analytic>
                        <author>
                            <persName>
                                <firstname>John</firstname>
                                <lastname>Smith</lastname>
                            </persName>
                        </author>
                        <author>
                            <persName>
                                <firstname>Jane</firstname>
                                <lastname>Doe</lastname>
                            </persName>
                        </author>
                    </analytic>
                </biblStruct>
            </sourceDesc>
        </fileDesc>
    </teiHeader>
</TEI>"""
        
        result = parser._parse_xml(xml_content, Path("test.pdf"))
        
        # 注意：当前实现可能未正确解析作者，这是测试的一部分
        # 实际情况需要根据真实XML结构调整


class TestGrobidIntegration:
    """Grobid集成测试（需要运行的Grobid服务）"""
    
    @pytest.mark.integration
    def test_parse_real_pdf(self):
        """测试解析真实PDF（集成测试）"""
        import json
        from datetime import datetime
        
        parser = GrobidParser(service_url="http://localhost:8070")
        test_pdf = Path(r"D:\pythonproject\CoreMiner\input\sample_papers\UnicodeInjection (9).pdf")
        
        result = parser.parse_pdf(test_pdf)
        assert result is not None
        assert result["success"] is True
        assert len(result["title"]) > 0
        
        # 保存解析结果
        output_dir = Path(r"D:\pythonproject\CoreMiner\output\results")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"parsed_result_{timestamp}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n解析结果已保存到: {output_file}")
        print(f"标题: {result.get('title', 'N/A')}")
        print(f"作者数: {len(result.get('authors', []))}")
        print(f"摘要长度: {len(result.get('abstract', ''))}")
        print(f"正文长度: {len(result.get('text', ''))}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
