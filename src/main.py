"""
主入口脚本 - Step 1: PDF解析演示
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import FileHandler, get_logger
from src.step1_pdf_parsing import GrobidParser, PDFHandler


def main():
    """主函数"""
    # 初始化日志
    config = FileHandler.load_config("config.yaml")
    logger = get_logger("CoreMiner")
    
    log_config = config.get("logging", {})
    from src.utils.logger import LoggerConfig
    LoggerConfig.setup(
        log_level=log_config.get("level", "INFO"),
        log_file=log_config.get("file", "output/logs/coreminer.log"),
        console=log_config.get("console", True),
    )
    
    logger.info("=" * 80)
    logger.info("CoreMiner - 论文贡献提取系统")
    logger.info("步骤1: PDF解析")
    logger.info("=" * 80)
    
    # 获取配置
    grobid_config = config.get("grobid", {})
    service_url = grobid_config.get("service_url", "http://localhost:8070")
    timeout = grobid_config.get("timeout", 60)
    
    # 初始化Grobid解析器
    logger.info(f"初始化Grobid解析器...")
    logger.info(f"  服务地址: {service_url}")
    logger.info(f"  超时时间: {timeout}秒")
    
    parser = GrobidParser(service_url=service_url, timeout=timeout)
    
    # 直接处理指定的PDF文件
    target_pdf = Path(r"D:\pythonproject\CoreMiner\input\sample_papers\UnicodeInjection (9).pdf")
    
    if not target_pdf.exists():
        logger.error(f"PDF文件不存在: {target_pdf}")
        return
    
    logger.info(f"\n目标PDF文件: {target_pdf}")
    pdf_files = [target_pdf]
    
    # 处理PDF文件
    for pdf_path in pdf_files:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"处理文件: {pdf_path.name}")
        logger.info(f"{'=' * 80}")
        
        # 验证PDF
        is_valid, error = PDFHandler.validate_pdf(str(pdf_path))
        if not is_valid:
            logger.error(f"PDF验证失败: {error}")
            continue
        
        logger.info(f"✓ PDF文件验证成功")
        
        # 获取文件信息
        pdf_info = PDFHandler.get_pdf_info(str(pdf_path))
        logger.info(f"  文件大小: {pdf_info['size_mb']:.2f} MB")
        
        # 解析PDF
        logger.info(f"开始解析PDF...")
        result = parser.parse_pdf_with_retries(str(pdf_path))
        
        if not result or not result.get("success"):
            logger.error(f"PDF解析失败: {result.get('error') if result else '未知错误'}")
            continue
        
        logger.info(f"✓ PDF解析成功")
        
        # 输出提取的信息
        logger.info(f"\n提取信息:")
        logger.info(f"  标题: {result.get('title', '未找到')[:100]}")
        
        authors = result.get("authors", [])
        logger.info(f"  作者数: {len(authors)}")
        if authors:
            for i, author in enumerate(authors[:3], 1):
                logger.info(f"    {i}. {author}")
            if len(authors) > 3:
                logger.info(f"    ... 等 {len(authors) - 3} 位作者")
        
        abstract = result.get("abstract", "")
        logger.info(f"  摘要长度: {len(abstract)} 字符")
        if abstract:
            logger.info(f"  摘要预览: {abstract[:200]}...")
        
        full_text = result.get("text", "")
        logger.info(f"  全文长度: {len(full_text)} 字符")
        
        # 保存结果（带时间戳）
        from datetime import datetime
        output_dir = Path("output/results")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"parsed_result_{timestamp}.json"
        FileHandler.save_json(result, str(output_file))
        logger.info(f"\n✓ 结果已保存: {output_file}")
        logger.info(f"  标题长度: {len(result.get('title', ''))}")
        logger.info(f"  作者数: {len(result.get('authors', []))}")
        logger.info(f"  摘要长度: {len(result.get('abstract', ''))}")
        logger.info(f"  正文长度: {len(result.get('text', ''))}")


if __name__ == "__main__":
    main()
