"""
Step 2 测试脚本：测试文本提取和清洁功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import get_logger, LoggerConfig
from src.step2_text_extraction.text_extractor import TextExtractor

def main():
    """主函数"""
    # 初始化日志
    LoggerConfig.setup(
        log_level="INFO",
        log_file="output/logs/step2.log",
        console=True,
    )
    
    logger = get_logger("CoreMiner.Step2Test")
    
    logger.info("=" * 80)
    logger.info("Step 2: 文本提取和清洁")
    logger.info("=" * 80)
    
    # Markdown文件路径
    mmd_file = r"D:\pythonproject\CoreMiner\DeepSeek-OCR\output\UnicodeInjection.mmd"
    output_dir = r"D:\pythonproject\CoreMiner\output\clean_results"
    
    # 创建提取器
    logger.info(f"\n初始化文本提取器...")
    extractor = TextExtractor()
    
    # 执行提取和保存
    logger.info(f"\n开始处理文件: {mmd_file}")
    try:
        output_file = extractor.extract_and_save(mmd_file, output_dir)
        logger.info(f"\n✓ 处理完成！")
        logger.info(f"  结果文件: {output_file}")
    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
