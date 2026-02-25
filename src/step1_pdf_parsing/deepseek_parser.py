"""
DeepSeek OCR PDF解析器
直接调用DeepSeek-OCR的run_dpsk_ocr_pdf.py脚本来解析PDF
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from src.utils.logger import get_logger

logger = get_logger("CoreMiner.DeepSeekOCR")


class DeepSeekOCRParser:
    """
    DeepSeek OCR PDF解析器
    直接调用DeepSeek-OCR脚本来解析PDF
    """
    
    def __init__(self, 
                 deepseek_ocr_path: str = None,
                 model_path: str = "deepseek-ai/DeepSeek-OCR"):
        """
        初始化DeepSeek OCR解析器
        
        Args:
            deepseek_ocr_path: DeepSeek-OCR项目路径
            model_path: 模型路径
        """
        if deepseek_ocr_path is None:
            # 默认路径
            deepseek_ocr_path = r"/home/ubuntu/pythonproject/CoreMiner/DeepSeek-OCR/DeepSeek-OCR-master/DeepSeek-OCR-vllm"
        
        self.deepseek_ocr_path = Path(deepseek_ocr_path)
        self.model_path = model_path
        self.run_script = self.deepseek_ocr_path / "run_dpsk_ocr_pdf.py"
        self.config_file = self.deepseek_ocr_path / "config.py"
        
        # 验证路径
        if not self.deepseek_ocr_path.exists():
            raise FileNotFoundError(f"DeepSeek-OCR路径不存在: {self.deepseek_ocr_path}")
        
        if not self.run_script.exists():
            raise FileNotFoundError(f"运行脚本不存在: {self.run_script}")
        
        logger.info(f"DeepSeek OCR解析器初始化成功")
        logger.info(f"DeepSeek-OCR路径: {self.deepseek_ocr_path}")
        logger.info(f"运行脚本: {self.run_script}")
    
    def parse_pdf(self, 
                  pdf_path: str = None,
                  output_dir: str = None,
                  prompt: str = None) -> Dict[str, Any]:
        """
        解析PDF文件
        
        Args:
            pdf_path: PDF文件路径（可选，如果不指定则从config.py读取INPUT_PATH）
            output_dir: 输出目录（可选，如果不指定则由DeepSeek OCR使用默认路径）
            prompt: OCR提示词
        
        Returns:
            包含解析结果的字典
        """
        # 如果未提供pdf_path，从config.py读取
        if pdf_path is None:
            config_vars = {}
            with open(self.config_file, 'r', encoding='utf-8') as f:
                exec(f.read(), config_vars)
            pdf_path = config_vars.get('INPUT_PATH', '')
            if not pdf_path:
                raise ValueError("pdf_path未提供，且config.py中INPUT_PATH为空")
            logger.info(f"从config.py读取PDF路径: {pdf_path}")
        
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        # 设置输出目录（如果未指定，使用DeepSeek OCR的默认输出路径）
        if output_dir is None:
            output_dir = self.deepseek_ocr_path.parent.parent / "output"
        else:
            output_dir = Path(output_dir)
        
        # 设置提示词
        if prompt is None:
            prompt = '<image>\n<|grounding|>Convert the document to markdown.'
        
        logger.info(f"开始解析PDF: {pdf_path}")
        logger.info(f"输出目录: {output_dir}")
        
        # 修改config.py中的INPUT_PATH和OUTPUT_PATH
        self._update_config(
            input_path=str(pdf_path.absolute()).replace('\\', '/'),
            output_path=str(output_dir.absolute()).replace('\\', '/'),
            prompt=prompt
        )
        
        # 运行脚本
        try:
            logger.info("正在运行DeepSeek OCR脚本...")
            result = subprocess.run(
                [sys.executable, str(self.run_script)],
                cwd=str(self.deepseek_ocr_path),
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                logger.error(f"解析失败: {result.stderr}")
                raise RuntimeError(f"DeepSeek OCR解析失败: {result.stderr}")
            
            logger.info("✓ PDF解析完成")
            logger.info(f"输出已保存到: {output_dir}")
            
            result_dict = {
                "success": True,
                "pdf_path": str(pdf_path),
                "output_dir": str(output_dir),
                "stdout": result.stdout,
            }
            
            return result_dict
            
        except Exception as e:
            logger.error(f"解析过程中出错: {str(e)}")
            raise
    
    def _update_config(self, input_path: str, output_path: str, prompt: str):
        """更新config.py文件"""
        try:
            # 读取config.py
            with open(self.config_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 修改INPUT_PATH和OUTPUT_PATH
            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                if line.strip().startswith('INPUT_PATH ='):
                    new_lines.append(f"INPUT_PATH = '{input_path}'\n")
                elif line.strip().startswith('OUTPUT_PATH ='):
                    new_lines.append(f"OUTPUT_PATH = '{output_path}'\n")
                elif line.strip().startswith('PROMPT ='):
                    # 使用repr来正确转义包含换行符的字符串
                    new_lines.append(f"PROMPT = {repr(prompt)}\n")
                else:
                    new_lines.append(line)
                i += 1
            
            # 写回config.py
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            logger.info("Config文件更新成功")
            
        except Exception as e:
            logger.error(f"更新config文件失败: {str(e)}")
            raise
    

