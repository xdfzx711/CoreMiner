"""
Step3 测试脚本
验证LLM提取模块的功能
"""
import json
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.step3_llm_extraction.main import (
    Step3Pipeline, 
    load_config_from_env,
    FileHandler,
    TextExtractor
)
from src.utils.logger import get_logger

logger = get_logger("CoreMiner.TestStep3")


def test_file_handler():
    """测试文件处理器"""
    logger.info("=" * 50)
    logger.info("测试1: 文件处理器")
    logger.info("=" * 50)
    
    results_dir = str(project_root / "output" / "results")
    
    # 获取最新文件
    latest_file = FileHandler.get_latest_result_file(results_dir)
    if latest_file:
        logger.info(f"✓ 找到最新文件: {latest_file}")
    else:
        logger.error("✗ 未找到结果文件")
        return False
    
    # 加载文件
    try:
        data = FileHandler.load_paper_content(latest_file)
        logger.info(f"✓ 成功加载文件")
        logger.info(f"  - 标题: {data.get('title', 'N/A')[:50]}...")
        return True
    except Exception as e:
        logger.error(f"✗ 加载文件失败: {e}")
        return False


def test_text_extractor():
    """测试文本提取器"""
    logger.info("\n" + "=" * 50)
    logger.info("测试2: 文本提取器")
    logger.info("=" * 50)
    
    results_dir = str(project_root / "output" / "results")
    latest_file = FileHandler.get_latest_result_file(results_dir)
    
    try:
        data = FileHandler.load_paper_content(latest_file)
        paper_content = TextExtractor.extract_paper_sections(data)
        
        logger.info("✓ 成功提取论文部分")
        logger.info(f"  - 标题: {paper_content.title}")
        logger.info(f"  - 摘要长度: {len(paper_content.abstract)} 字符")
        logger.info(f"  - 引言后三分之一长度: {len(paper_content.introduction_1_3)} 字符")
        logger.info(f"  - 结论: {'有' if paper_content.conclusion else '无'}")
        
        # 显示摘要开头
        logger.info(f"  - 摘要开头: {paper_content.abstract[:100]}...")
        
        return True
    except Exception as e:
        logger.error(f"✗ 文本提取失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_loading():
    """测试配置加载"""
    logger.info("\n" + "=" * 50)
    logger.info("测试3: 配置加载")
    logger.info("=" * 50)
    
    try:
        config = load_config_from_env()
        logger.info("✓ 成功加载配置")
        logger.info(f"  - API模型: {config.model_name}")
        logger.info(f"  - API URL: {config.api_url[:50]}...")
        logger.info(f"  - Max Tokens: {config.max_tokens}")
        logger.info(f"  - Temperature: {config.temperature}")
        return True
    except Exception as e:
        logger.error(f"✗ 配置加载失败: {e}")
        return False


def test_full_pipeline():
    """测试完整流程"""
    logger.info("\n" + "=" * 50)
    logger.info("测试4: 完整流程（LLM提取）")
    logger.info("=" * 50)
    
    try:
        # 加载配置
        config = load_config_from_env()
        
        # 创建Pipeline
        results_dir = str(project_root / "output" / "results")
        pipeline = Step3Pipeline(config, results_dir)
        
        # 运行Pipeline
        logger.info("开始调用LLM API...")
        core_contribution = pipeline.run()
        
        logger.info("✓ 成功提取核心贡献")
        logger.info(f"  - 论文标题: {core_contribution.title}")
        logger.info(f"  - 使用模型: {core_contribution.model_used}")
        logger.info(f"  - Prompt Tokens: {core_contribution.prompt_tokens}")
        logger.info(f"  - Completion Tokens: {core_contribution.completion_tokens}")
        logger.info(f"  - 提取时间: {core_contribution.extraction_timestamp}")
        
        logger.info("\n核心贡献总结:")
        logger.info("-" * 50)
        logger.info(core_contribution.contributions_summary)
        logger.info("-" * 50)
        
        # 保存结果
        output_file = project_root / "output" / "core_contributions.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(core_contribution.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ 结果已保存到: {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"✗ 流程执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    logger.info("开始测试Step3 LLM提取模块\n")
    
    results = {
        "文件处理器": test_file_handler(),
        "文本提取器": test_text_extractor(),
        "配置加载": test_config_loading(),
        "完整流程": test_full_pipeline()
    }
    
    logger.info("\n" + "=" * 50)
    logger.info("测试总结")
    logger.info("=" * 50)
    
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        logger.info(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    logger.info("=" * 50)
    
    if all_passed:
        logger.info("✓ 所有测试通过!")
        return 0
    else:
        logger.error("✗ 某些测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
