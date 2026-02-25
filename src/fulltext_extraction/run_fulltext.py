"""
全文提取运行脚本
独立运行，用于测试和对比
"""
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import os

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.logger import get_logger
from src.fulltext_extraction import FullTextExtractor
from src.fulltext_extraction.data_models import ExtractionConfig

logger = get_logger("CoreMiner.FullTextRun")


def load_config_from_env() -> ExtractionConfig:
    """从环境变量加载配置"""
    load_dotenv()
    
    api_key = os.getenv("Generate_API_KEY")
    api_url = os.getenv("Generate_API_URL")
    model_name = os.getenv("Generate_MODEL")
    
    if not all([api_key, api_url, model_name]):
        raise ValueError("缺少必要的环境变量: Generate_API_KEY, Generate_API_URL, Generate_MODEL")
    
    config = ExtractionConfig(
        api_key=api_key,
        api_url=api_url,
        model_name=model_name,
        max_tokens=2000,
        temperature=0.7,
        preprocessing_mode="none"  # 使用选项C：完全不处理
    )
    
    logger.info("配置加载成功")
    logger.info(f"  API URL: {api_url}")
    logger.info(f"  模型: {model_name}")
    logger.info(f"  预处理模式: {config.preprocessing_mode}")
    
    return config


def save_result(result, output_dir: str) -> str:
    """保存提取结果
    
    Args:
        result: FullTextResult对象
        output_dir: 输出目录
        
    Returns:
        保存的文件路径
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名（基于论文标题）
    safe_title = "".join(c for c in result.title if c.isalnum() or c in (' ', '_', '-')).strip()
    safe_title = safe_title.replace(' ', '_')[:100]  # 限制长度
    
    filename = f"fulltext_result_{safe_title}.json"
    filepath = output_path / filename
    
    # 保存为JSON
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    
    logger.info(f"结果已保存: {filepath}")
    return str(filepath)


def run_single_file(mmd_file_path: str, output_dir: str = None):
    """运行单个文件的全文提取
    
    Args:
        mmd_file_path: .mmd文件路径
        output_dir: 输出目录，默认为 output/fulltext_results/
    """
    if output_dir is None:
        output_dir = "/home/ubuntu/pythonproject/CoreMiner/output/fulltext_results"
    
    try:
        logger.info("\n" + "=" * 80)
        logger.info("全文提取 - 独立运行模式")
        logger.info("=" * 80)
        logger.info(f"输入文件: {mmd_file_path}")
        logger.info(f"输出目录: {output_dir}")
        
        # 1. 加载配置
        config = load_config_from_env()
        
        # 2. 创建提取器
        extractor = FullTextExtractor(config)
        
        # 3. 执行提取
        result = extractor.extract(mmd_file_path)
        
        # 4. 保存结果
        output_file = save_result(result, output_dir)
        
        logger.info("\n" + "=" * 80)
        logger.info("✓ 全文提取完成")
        logger.info("=" * 80)
        logger.info(f"输出文件: {output_file}")
        logger.info(f"\n核心贡献摘要:\n{result.contributions_summary}")
        
        return result
        
    except Exception as e:
        logger.error(f"✗ 全文提取失败: {e}")
        import traceback
        traceback.print_exc()
        raise


def batch_process(input_dir: str, output_dir: str = None):
    """批量处理多个.mmd文件
    
    Args:
        input_dir: 包含.mmd文件的目录（例如 DeepSeek-OCR/output_001/）
        output_dir: 输出目录
    """
    if output_dir is None:
        output_dir = "/home/ubuntu/pythonproject/CoreMiner/output/fulltext_results"
    
    input_path = Path(input_dir)
    mmd_files = list(input_path.glob("*.mmd"))
    
    if not mmd_files:
        logger.error(f"在 {input_dir} 中未找到.mmd文件")
        return
    
    logger.info(f"找到 {len(mmd_files)} 个.mmd文件")
    
    results = []
    for i, mmd_file in enumerate(mmd_files, 1):
        logger.info(f"\n处理文件 {i}/{len(mmd_files)}: {mmd_file.name}")
        try:
            result = run_single_file(str(mmd_file), output_dir)
            results.append(result)
        except Exception as e:
            logger.error(f"处理文件 {mmd_file.name} 失败: {e}")
            continue
    
    logger.info(f"\n批量处理完成，成功: {len(results)}/{len(mmd_files)}")


def process_all_step1_outputs(output_dir: str = None):
    """处理所有Step1输出的PDF文件
    
    自动扫描所有 DeepSeek-OCR/output_* 目录，处理其中的.mmd文件
    
    Args:
        output_dir: 输出目录，默认为 output/fulltext_results/
    """
    if output_dir is None:
        output_dir = "/home/ubuntu/pythonproject/CoreMiner/output/fulltext_results"
    
    base_dir = Path("/home/ubuntu/pythonproject/CoreMiner/DeepSeek-OCR")
    
    # 查找所有 output_* 目录
    output_dirs = sorted(base_dir.glob("output_*"))
    
    if not output_dirs:
        logger.error(f"在 {base_dir} 中未找到任何 output_* 目录")
        logger.info("请先运行 Step1 解析PDF文件")
        return
    
    logger.info("=" * 80)
    logger.info(f"找到 {len(output_dirs)} 个Step1输出目录")
    logger.info("=" * 80)
    
    for i, output_path in enumerate(output_dirs, 1):
        logger.info(f"\n[{i}/{len(output_dirs)}] 处理目录: {output_path.name}")
        logger.info("-" * 60)
        
        # 查找该目录下的.mmd文件
        mmd_files = list(output_path.glob("*.mmd"))
        
        if not mmd_files:
            logger.warning(f"  目录 {output_path.name} 中未找到.mmd文件，跳过")
            continue
        
        logger.info(f"  找到 {len(mmd_files)} 个.mmd文件")
        
        # 处理每个.mmd文件
        for j, mmd_file in enumerate(mmd_files, 1):
            logger.info(f"  [{j}/{len(mmd_files)}] {mmd_file.name}")
            try:
                run_single_file(str(mmd_file), output_dir)
            except Exception as e:
                logger.error(f"  处理失败: {e}")
                continue
    
    logger.info("\n" + "=" * 80)
    logger.info("✓ 所有Step1输出处理完成")
    logger.info("=" * 80)
    logger.info(f"结果保存在: {output_dir}")
    
    # 统计结果
    result_files = list(Path(output_dir).glob("fulltext_result_*.json"))
    logger.info(f"共生成 {len(result_files)} 个结果文件")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="全文直接提取工具")
    parser.add_argument("--file", type=str, help=".mmd文件路径")
    parser.add_argument("--dir", type=str, help="包含.mmd文件的目录")
    parser.add_argument("--output", type=str, help="输出目录（默认: output/fulltext_results/）")
    parser.add_argument("--all", action="store_true", help="处理所有Step1输出目录（默认行为）")
    
    args = parser.parse_args()
    
    if args.file:
        # 处理单个文件
        run_single_file(args.file, args.output)
    elif args.dir:
        # 处理指定目录
        batch_process(args.dir, args.output)
    else:
        # 默认：自动处理所有Step1输出
        logger.info("自动模式：处理所有Step1已解析的PDF文件")
        process_all_step1_outputs(args.output)
