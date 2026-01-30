"""
CoreMiner 主入口脚本
完整的论文贡献提取流程：Step1-Step4
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import FileHandler, get_logger
from src.utils.logger import LoggerConfig


def main():
    """主函数 - 执行完整的论文提取流程"""
    
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
    logger.info("CoreMiner - 论文贡献提取系统")
    logger.info("=" * 80)
    
    # ========================================================================
    # Step 1: PDF解析 (暂时注释)
    # ========================================================================
    # logger.info("\n" + "=" * 80)
    # logger.info("Step 1: PDF解析")
    # logger.info("=" * 80)
    # 
    # from src.step1_pdf_parsing import GrobidParser, DeepSeekOCRParser, PDFHandler
    # 
    # parse_method = config.get("pdf_parser", {}).get("method", "deepseek")
    # target_pdf = Path(r"D:\pythonproject\CoreMiner\input\sample_papers\UnicodeInjection (9).pdf")
    # 
    # if not target_pdf.exists():
    #     logger.error(f"PDF文件不存在: {target_pdf}")
    #     return
    # 
    # logger.info(f"目标PDF: {target_pdf.name}")
    # logger.info(f"解析方式: {parse_method.upper()}")
    # 
    # # 执行PDF解析...
    # logger.info("Step 1 暂时跳过，直接从已有的MMD文件开始")
    
    # ========================================================================
    # Step 2: 文本提取和清洗
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("Step 2: 文本提取和清洗")
    logger.info("=" * 80)
    
    from src.step2_text_extraction import TextExtractor
    
    # 输入文件
    mmd_file = Path(r"D:\pythonproject\CoreMiner\DeepSeek-OCR\output\UnicodeInjection.mmd")
    # 输出目录
    clean_results_dir = Path(r"D:\pythonproject\CoreMiner\output\clean_results")
    clean_results_dir.mkdir(parents=True, exist_ok=True)
    
    if not mmd_file.exists():
        logger.error(f"MMD文件不存在: {mmd_file}")
        return
    
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
        return
    
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
    llm_results_dir = Path(r"D:\pythonproject\CoreMiner\output\llm_results")
    llm_results_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"输入目录: {step3_input_dir}")
    logger.info(f"输出目录: {llm_results_dir}")
    
    try:
        # 加载LLM配置
        llm_config = load_config_from_env()
        logger.info(f"使用模型: {llm_config.model_name}")
        
        # 创建Pipeline并执行
        pipeline = Step3Pipeline(llm_config, str(step3_input_dir))
        core_contribution = pipeline.run()
        
        # 保存到llm_results目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = llm_results_dir / f"core_contributions_{timestamp}.json"
        
        contribution_data = {
            "source_file": core_contribution.source_file,
            "title": core_contribution.title,
            "contributions_summary": core_contribution.contributions_summary,
            "extraction_timestamp": core_contribution.extraction_timestamp,
            "model_used": core_contribution.model_used,
            "prompt_tokens": core_contribution.prompt_tokens,
            "completion_tokens": core_contribution.completion_tokens
        }
        
        FileHandler.save_json(contribution_data, str(output_file))
        logger.info(f"✓ Step 3 完成")
        logger.info(f"  贡献摘要: {output_file}")
        logger.info(f"  摘要长度: {len(core_contribution.contributions_summary)} 字符")
        
    except Exception as e:
        logger.error(f"✗ Step 3 失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
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
        # 读取Step2的清洗结果（获取原文）
        import json
        clean_result_files = list(step3_input_dir.glob("extracted_result_*.json"))
        if not clean_result_files:
            logger.error("未找到清洗后的结果文件")
            return
        
        latest_clean_file = max(clean_result_files, key=lambda p: p.stat().st_mtime)
        with open(latest_clean_file, 'r', encoding='utf-8') as f:
            clean_data = json.load(f)
        
        # 提取原文章节
        sections = clean_data.get('cleaned', {}) or clean_data.get('original', {})
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
                "source_file": latest_clean_file.name
            }
        )
        
        saved_path = save_refine_record(record)
        logger.info(f"\n  完整记录已保存: {saved_path}")
        
        # 输出最终摘要
        logger.info(f"\n最终优化摘要:")
        logger.info(f"  {final_summary}")
        
    except Exception as e:
        logger.error(f"✗ Step 4 失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========================================================================
    # 完成
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("✓ 所有步骤完成！")
    logger.info("=" * 80)
    logger.info(f"\n输出文件:")
    logger.info(f"  Step 2 清洗结果: {clean_results_dir}")
    logger.info(f"  Step 3 贡献提取: {llm_results_dir}")
    logger.info(f"  Step 4 验证优化: output/refine_results/")


if __name__ == "__main__":
    main()
