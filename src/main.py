"""
CoreMiner 主入口脚本
完整的论文贡献提取流程：Step1-Step4
支持批量处理多个PDF文件
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import FileHandler, get_logger
from src.utils.logger import LoggerConfig


def process_single_pdf(pdf_path: Path, pdf_index: int, config: Dict[str, Any], logger) -> bool:
    """
    处理单个PDF的完整流程 (Step 1-4)
    
    Args:
        pdf_path: PDF文件路径
        pdf_index: PDF序号（用于创建独立输出目录）
        config: 配置字典
        logger: 日志对象
    
    Returns:
        bool: 处理是否成功
    """
    
    logger.info("\n" + "=" * 80)
    logger.info(f"开始处理: {pdf_path.name}")
    logger.info("=" * 80)
    
    # ========================================================================
    # Step 1: PDF解析
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("Step 1: PDF解析")
    logger.info("=" * 80)
    
    from src.step1_pdf_parsing import DeepSeekOCRParser
    
    # 为每个PDF创建独立的输出目录（带编号）
    ocr_output_dir = Path(f"/home/ubuntu/pythonproject/CoreMiner/DeepSeek-OCR/output_{pdf_index:03d}")
    
    try:
        parser = DeepSeekOCRParser()
        result = parser.parse_pdf(str(pdf_path), str(ocr_output_dir))
        step1_output_dir = Path(result['output_dir'])
        logger.info(f"✓ Step 1 完成")
        logger.info(f"  输出目录: {step1_output_dir}")
    except Exception as e:
        logger.error(f"✗ Step 1 失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========================================================================
    # Step 2: 文本提取和清洗
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("Step 2: 文本提取和清洗")
    logger.info("=" * 80)
    
    from src.step2_text_extraction import TextExtractor
    
    # 从Step 1输出目录中查找.mmd文件
    mmd_files = list(step1_output_dir.glob("*.mmd"))
    if not mmd_files:
        logger.error(f"Step 1输出目录中未找到.mmd文件: {step1_output_dir}")
        return False
    
    mmd_file = mmd_files[0]  # 使用找到的第一个.mmd文件
    
    # 输出目录
    clean_results_dir = Path(r"/home/ubuntu/pythonproject/CoreMiner/output/clean_results")
    clean_results_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"输入文件: {mmd_file.name}")
    logger.info(f"输出目录: {clean_results_dir}")
    
    try:
        extractor = TextExtractor()
        output_file = extractor.extract_and_save(str(mmd_file), str(clean_results_dir))
        logger.info(f"✓ Step 2 完成")
        logger.info(f"  清洗后的数据: {output_file}")
    except Exception as e:
        logger.error(f"✗ Step 2 失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 提取论文标题和内容用于后续步骤
    paper_title = None
    step2_result = None
    try:
        import json
        with open(output_file, 'r', encoding='utf-8') as f:
            step2_result = json.load(f)
            paper_title = step2_result.get('title')
            if paper_title:
                logger.info(f"  论文标题: {paper_title}")
    except Exception as e:
        logger.warning(f"无法提取论文标题: {e}")
    
    # ========================================================================
    # Step 3: LLM提取核心贡献
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("Step 3: LLM提取核心贡献")
    logger.info("=" * 80)
    
    from src.step3_llm_extraction.main import Step3Pipeline, load_config_from_env
    
    # 输入目录（Step2的输出）
    step3_input_dir = clean_results_dir
    # 输出目录
    llm_results_dir = Path(r"/home/ubuntu/pythonproject/CoreMiner/output/llm_results")
    llm_results_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"输入目录: {step3_input_dir}")
    logger.info(f"输出目录: {llm_results_dir}")
    
    try:
        # 加载LLM配置
        llm_config = load_config_from_env()
        logger.info(f"使用模型: {llm_config.model_name}")
        
        # 创建Pipeline并执行 - 直接传递Step 2的输出文件
        pipeline = Step3Pipeline(llm_config, output_file)
        core_contribution = pipeline.run()
        
        # 保存到llm_results目录 - 使用论文标题命名
        output_file = Step3Pipeline.save_contribution(
            core_contribution,
            str(llm_results_dir),
            paper_title
        )
        
        logger.info(f"✓ Step 3 完成")
        logger.info(f"  贡献摘要: {output_file}")
        logger.info(f"  摘要长度: {len(core_contribution.contributions_summary)} 字符")
        
    except Exception as e:
        logger.error(f"✗ Step 3 失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========================================================================
    # Step 4: 验证和优化贡献摘要
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("Step 4: 验证和优化贡献摘要")
    logger.info("=" * 80)
    
    from src.step4_refine import (
        validate_and_refine,
        RefineRecord,
        save_refine_record
    )
    
    # 输入：从clean_results读取原文，从llm_results读取贡献摘要
    logger.info(f"原文来源: {step3_input_dir}")
    logger.info(f"贡献摘要来源: {llm_results_dir}")
    
    try:
        # 读取Step2的清洗结果（获取原文）- 直接使用之前已读取的step2_result
        if not step2_result:
            logger.error("Step 2结果数据不可用")
            return False
        
        # 提取原文章节
        sections = step2_result.get('cleaned', {}) or step2_result.get('original', {})
        abstract = sections.get('abstract', '')
        introduction_full = sections.get('introduction_1_3', '')
        conclusion = sections.get('conclusion', '')
        
        # 提取引言后1/3
        total_chars = len(introduction_full)
        start_pos = int(total_chars * 2 / 3)
        introduction_last_third = introduction_full[start_pos:]
        
        logger.info(f"原文章节提取:")
        logger.info(f"  - Abstract: {len(abstract)} 字符")
        logger.info(f"  - Introduction (后1/3): {len(introduction_last_third)} 字符")
        logger.info(f"  - Conclusion: {len(conclusion) if conclusion else 0} 字符")
        
        # 读取Step3的贡献摘要
        summary_text = core_contribution.contributions_summary
        paper_title = core_contribution.title
        
        logger.info(f"\n开始验证和优化...")
        logger.info(f"  论文标题: {paper_title}")
        logger.info(f"  原始摘要长度: {len(summary_text)} 字符")
        
        # 执行验证和优化
        final_summary, final_validation, iterations = validate_and_refine(
            summary_text=summary_text,
            abstract_text=abstract,
            introduction_last_third=introduction_last_third,
            conclusion_text=conclusion,
            refine_threshold=8,
            max_iterations=3
        )
        
        logger.info(f"✓ Step 4 完成")
        logger.info(f"\n验证结果:")
        logger.info(f"  - is_valid: {final_validation.is_valid}")
        logger.info(f"  - score: {final_validation.score}/10")
        logger.info(f"  - 遗漏要点: {len(final_validation.missing_points)}")
        logger.info(f"  - 无依据声称: {len(final_validation.unsupported_claims)}")
        logger.info(f"  - Refinement迭代: {len(iterations)} 次")
        
        # 保存完整的Refine记录
        record = RefineRecord(
            paper_title=paper_title,
            validation_time=datetime.now().isoformat(),
            ground_truth={
                "abstract": abstract,
                "introduction_last_third": introduction_last_third,
                "conclusion": conclusion
            },
            original_summary=summary_text,
            original_validation=iterations[0].validation if iterations else final_validation,
            refinement_applied=len(iterations) > 0,
            refinement_iterations=iterations,
            final_summary=final_summary,
            final_validation=final_validation,
            total_iterations=len(iterations),
            metadata={
                "model": core_contribution.model_used,
                "prompt_tokens": core_contribution.prompt_tokens,
                "completion_tokens": core_contribution.completion_tokens,
                "refine_threshold": 8,
                "max_iterations": 3,
                "source_file": Path(output_file).name
            }
        )
        
        # 保存验证记录 - 使用论文标题命名
        saved_path = save_refine_record(record, paper_title=paper_title)
        logger.info(f"\n  完整记录已保存: {saved_path}")
        
        # 输出最终摘要
        logger.info(f"\n最终优化摘要:")
        logger.info(f"  {final_summary}")
        
    except Exception as e:
        logger.error(f"✗ Step 4 失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 处理成功
    logger.info("\n" + "=" * 80)
    logger.info(f"✓ {pdf_path.name} 处理完成！")
    logger.info("=" * 80)
    return True


def main():
    """主函数 - 批量处理PDF文件"""
    from tqdm import tqdm
    
    # 初始化日志
    config = FileHandler.load_config("config.yaml")
    logger = get_logger("CoreMiner")
    
    log_config = config.get("logging", {})
    LoggerConfig.setup(
        log_level=log_config.get("level", "INFO"),
        log_file=log_config.get("file", "output/logs/coreminer.log"),
        console=log_config.get("console", True),
    )
    
    logger.info("=" * 80)
    logger.info("CoreMiner - 论文贡献提取系统 (批量处理模式)")
    logger.info("=" * 80)
    
    # 获取input目录下所有PDF文件
    project_root = Path(__file__).parent.parent
    input_dir = project_root / "DeepSeek-OCR" / "input"
    
    # 确保input目录存在
    input_dir.mkdir(parents=True, exist_ok=True)
    
    # 查找所有PDF文件
    pdf_files = sorted(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"在 {input_dir} 中未找到PDF文件")
        logger.info("请将PDF文件放入input目录后重新运行")
        return
    
    logger.info(f"\n发现 {len(pdf_files)} 个PDF文件:")
    for i, pdf in enumerate(pdf_files, 1):
        logger.info(f"  {i}. {pdf.name}")
    
    # 批量处理
    results = {"success": [], "failed": []}
    start_time = datetime.now()
    
    # 使用tqdm创建美观的进度条
    logger.info("")  # 空行
    with tqdm(pdf_files, desc="📄 总体进度", unit="PDF", ncols=100, 
              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') as pbar:
        for i, pdf_file in enumerate(pbar, 1):
            # 更新进度条描述显示当前文件
            pbar.set_description(f"📄 处理中: {pdf_file.name[:40]}")
            
            logger.info("\n" + "═" * 80)
            logger.info(f"📋 [{i}/{len(pdf_files)}] {pdf_file.name}")
            logger.info("═" * 80)
            
            pdf_start_time = datetime.now()
            success = process_single_pdf(pdf_file, i, config, logger)
            pdf_duration = (datetime.now() - pdf_start_time).total_seconds()
            
            if success:
                results["success"].append(pdf_file.name)
                pbar.set_postfix_str(f"✓ 成功 {pdf_duration:.1f}s")
                logger.info(f"\n✓ 成功完成 - 用时: {pdf_duration:.1f}秒")
            else:
                results["failed"].append(pdf_file.name)
                pbar.set_postfix_str(f"✗ 失败 {pdf_duration:.1f}s")
                logger.error(f"\n✗ 处理失败 - 用时: {pdf_duration:.1f}秒")
    
    # 输出统计
    total_duration = (datetime.now() - start_time).total_seconds()
    
    logger.info("\n" + "═" * 80)
    logger.info("🎉 批量处理完成！")
    logger.info("═" * 80)
    logger.info(f"\n📊 统计信息:")
    logger.info(f"  📁 总文件数: {len(pdf_files)}")
    logger.info(f"  ✅ 成功: {len(results['success'])} ({len(results['success'])/len(pdf_files)*100:.1f}%)")
    logger.info(f"  ❌ 失败: {len(results['failed'])} ({len(results['failed'])/len(pdf_files)*100:.1f}%)")
    logger.info(f"  ⏱️  总用时: {total_duration:.1f}秒 ({total_duration/60:.1f}分钟)")
    logger.info(f"  ⚡ 平均用时: {total_duration/len(pdf_files):.1f}秒/文件")
    
    if results['success']:
        logger.info(f"\n✅ 成功处理的文件:")
        for filename in results['success']:
            logger.info(f"   ✓ {filename}")
    
    if results['failed']:
        logger.info(f"\n❌ 失败的文件:")
        for filename in results['failed']:
            logger.error(f"   ✗ {filename}")
    
    logger.info(f"\n📂 输出目录:")
    logger.info(f"   🔍 OCR结果: DeepSeek-OCR/output_001, output_002, ...")
    logger.info(f"   📝 清洗结果: output/clean_results/")
    logger.info(f"   🤖 贡献提取: output/llm_results/")
    logger.info(f"   ✨ 验证优化: output/refine_results/")


if __name__ == "__main__":
    main()
