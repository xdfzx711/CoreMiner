"""
PDF处理工具
处理PDF文件的验证等操作
"""
from pathlib import Path
from typing import Optional
from src.utils.logger import get_logger


logger = get_logger("CoreMiner.PDFHandler")


class PDFHandler:
    """PDF文件处理类"""
    
    VALID_EXTENSIONS = {".pdf"}
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    
    @staticmethod
    def validate_pdf(pdf_path: str) -> tuple[bool, Optional[str]]:
        """
        验证PDF文件
        
        Args:
            pdf_path: PDF文件路径
        
        Returns:
            (是否有效, 错误信息)
        """
        pdf_path = Path(pdf_path)
        
        # 检查文件是否存在
        if not pdf_path.exists():
            return False, f"文件不存在: {pdf_path}"
        
        # 检查是否是文件
        if not pdf_path.is_file():
            return False, f"不是文件: {pdf_path}"
        
        # 检查扩展名
        if pdf_path.suffix.lower() not in PDFHandler.VALID_EXTENSIONS:
            return False, f"不是PDF文件: {pdf_path}"
        
        # 检查文件大小
        file_size = pdf_path.stat().st_size
        if file_size == 0:
            return False, f"PDF文件为空: {pdf_path}"
        
        if file_size > PDFHandler.MAX_FILE_SIZE:
            return False, f"PDF文件过大 ({file_size / 1024 / 1024:.2f}MB > 100MB)"
        
        # 尝试读取文件头以验证是有效的PDF
        try:
            with open(pdf_path, "rb") as f:
                header = f.read(5)
                if header != b"%PDF-":
                    return False, "文件不是有效的PDF (魔术数字检查失败)"
        except IOError as e:
            return False, f"无法读取PDF文件: {e}"
        
        return True, None
    
    @staticmethod
    def get_pdf_info(pdf_path: str) -> dict:
        """
        获取PDF文件信息
        
        Args:
            pdf_path: PDF文件路径
        
        Returns:
            文件信息字典
        """
        pdf_path = Path(pdf_path)
        
        info = {
            "path": str(pdf_path),
            "name": pdf_path.name,
            "size_bytes": 0,
            "size_mb": 0.0,
            "exists": False,
            "valid": False,
            "error": None,
        }
        
        if pdf_path.exists():
            info["exists"] = True
            size_bytes = pdf_path.stat().st_size
            info["size_bytes"] = size_bytes
            info["size_mb"] = size_bytes / 1024 / 1024
            
            is_valid, error = PDFHandler.validate_pdf(pdf_path)
            info["valid"] = is_valid
            info["error"] = error
        else:
            info["error"] = "文件不存在"
        
        return info
