"""
Step3 LLM提取模块
从清洗后的文本中使用大模型提取论文核心贡献
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import re

import requests
from dotenv import load_dotenv

from src.utils.logger import get_logger
from src.step3_llm_extraction.data_models import (
    PaperContent, CoreContribution, ExtractionConfig
)

logger = get_logger("CoreMiner.Step3LLMExtraction")


class FileHandler:
    """文件处理器"""
    
    @staticmethod
    def get_latest_result_file(results_dir: str) -> Optional[str]:
        """获取最新的提取结果文件"""
        results_path = Path(results_dir)
        
        if not results_path.exists():
            logger.error(f"结果目录不存在: {results_dir}")
            return None
        
        # 获取所有JSON文件
        json_files = list(results_path.glob("extracted_result_*.json"))
        
        if not json_files:
            logger.error(f"在{results_dir}中未找到结果文件")
            return None
        
        # 按时间戳排序，获取最新的
        latest_file = sorted(json_files, key=lambda x: x.name)[-1]
        logger.info(f"找到最新的结果文件: {latest_file}")
        return str(latest_file)
    
    @staticmethod
    def load_paper_content(file_path: str) -> Dict[str, Any]:
        """从JSON文件中加载论文内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"成功加载文件: {file_path}")
            return data
        except Exception as e:
            logger.error(f"加载文件失败: {e}")
            raise


class TextExtractor:
    """文本提取器"""
    
    @staticmethod
    def extract_paper_sections(data: Dict[str, Any]) -> PaperContent:
        """从JSON数据中提取论文的各个部分"""
        try:
            # 优先从cleaned字段获取，否则从original字段获取
            cleaned = data.get('cleaned', {})
            original = data.get('original', {})
            
            abstract = cleaned.get('abstract') or original.get('abstract', '')
            introduction_1_3 = cleaned.get('introduction_1_3') or original.get('introduction_1_3', '')
            conclusion = cleaned.get('conclusion') or original.get('conclusion')
            title = data.get('title', 'Unknown Title')
            
            # 清理空白和多余空格
            abstract = abstract.strip() if abstract else ''
            introduction_1_3 = introduction_1_3.strip() if introduction_1_3 else ''
            conclusion = conclusion.strip() if conclusion else None
            
            paper_content = PaperContent(
                title=title,
                abstract=abstract,
                introduction_1_3=introduction_1_3,
                conclusion=conclusion
            )
            
            logger.info(f"成功提取论文内容: {title}")
            logger.debug(f"摘要长度: {len(abstract)}, 引言后三分之一长度: {len(introduction_1_3)}")
            
            return paper_content
            
        except ValueError as e:
            logger.error(f"论文内容验证失败: {e}")
            raise
        except Exception as e:
            logger.error(f"提取论文内容失败: {e}")
            raise


class LLMExtractor:
    """LLM提取器 - 使用大模型提取核心贡献"""
    
    def __init__(self, config: ExtractionConfig):
        """初始化LLM提取器"""
        self.config = config
        self.config.validate()
    
    def build_prompt(self, paper_content: PaperContent) -> str:
        """构建提示词"""
        prompt = f"""Role: You are an experienced academic paper reviewer skilled at precisely extracting core innovations from complex research texts.

Task: Please read the paper segments I provide (including abstract, latter half of introduction, and conclusion), and summarize the core contributions of this paper.

Requirements:

Information Source: Based solely on the text content I provide, focus on the new methods, new findings, new frameworks, or performance improvements proposed by the authors.

Output Format: Please output as a concise, coherent paragraph-style summary, strictly limited to 3-5 sentences.

Content Requirements: Avoid listing bullet points; instead, connect the contributions through logical connectors (e.g., "First," "Through...," "Finally...").

Language Style: Maintain academic rigor, get straight to the point, and avoid redundant openings like "This paper argues that."

Content to Analyze:

[Abstract]
{paper_content.abstract}

[Introduction (Last Third)]
{paper_content.introduction_1_3}

[Conclusion]
{paper_content.conclusion if paper_content.conclusion else 'Conclusion section not provided'}

Please output the core contribution summary directly in English, without repeating the above requirements."""
        
        return prompt
    
    def call_llm_api(self, prompt: str) -> Dict[str, Any]:
        """调用LLM API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.config.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature
            }
            
            logger.info(f"调用LLM API，模型: {self.config.model_name}")
            logger.debug(f"API URL: {self.config.api_url}")
            
            response = requests.post(
                self.config.api_url,
                json=payload,
                headers=headers,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info("LLM API调用成功")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {e}")
            raise
        except Exception as e:
            logger.error(f"API调用异常: {e}")
            raise
    
    def extract_contribution(self, paper_content: PaperContent) -> CoreContribution:
        """提取核心贡献"""
        try:
            # 构建提示词
            prompt = self.build_prompt(paper_content)
            
            # 调用LLM API
            api_response = self.call_llm_api(prompt)
            
            # 解析响应
            if 'choices' not in api_response or not api_response['choices']:
                raise ValueError("LLM API响应格式异常")
            
            contribution_text = api_response['choices'][0].get('message', {}).get('content', '')
            
            if not contribution_text:
                raise ValueError("LLM API返回空内容")
            
            # 创建核心贡献对象
            core_contribution = CoreContribution(
                source_file=paper_content.title,
                title=paper_content.title,
                contributions_summary=contribution_text.strip(),
                model_used=self.config.model_name,
                prompt_tokens=api_response.get('usage', {}).get('prompt_tokens', 0),
                completion_tokens=api_response.get('usage', {}).get('completion_tokens', 0)
            )
            
            logger.info(f"成功提取论文核心贡献")
            logger.debug(f"提取结果长度: {len(contribution_text)}")
            
            return core_contribution
            
        except Exception as e:
            logger.error(f"提取核心贡献失败: {e}")
            raise


class Step3Pipeline:
    """Step3处理流程"""
    
    def __init__(self, config: ExtractionConfig, input_file: str):
        """初始化Pipeline
        
        Args:
            config: LLM配置
            input_file: Step2输出的JSON文件路径
        """
        self.input_file = input_file
        self.config = config
        self.llm_extractor = LLMExtractor(config)
    
    def run(self) -> CoreContribution:
        """运行完整的处理流程"""
        try:
            # 第一步：验证输入文件存在
            logger.info("Step3: 开始处理")
            if not os.path.exists(self.input_file):
                raise FileNotFoundError(f"输入文件不存在: {self.input_file}")
            
            logger.info(f"处理文件: {self.input_file}")
            
            # 第二步：加载论文内容
            paper_data = FileHandler.load_paper_content(self.input_file)
            
            # 第三步：提取论文各部分
            paper_content = TextExtractor.extract_paper_sections(paper_data)
            
            # 第四步：使用LLM提取核心贡献
            core_contribution = self.llm_extractor.extract_contribution(paper_content)
            
            logger.info("Step3: 处理完成")
            return core_contribution
            
        except Exception as e:
            logger.error(f"Step3处理失败: {e}")
            raise
    
    @staticmethod
    def save_contribution(contribution: CoreContribution, output_dir: str, paper_title: str = None) -> str:
        """
        保存核心贡献到JSON文件
        
        Args:
            contribution: CoreContribution对象
            output_dir: 输出目录
            paper_title: 论文标题(可选,用于生成文件名)
        
        Returns:
            保存的文件路径
        """
        from src.utils.file_handler import FileHandler
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名 - 优先使用论文标题
        sanitized_title = FileHandler.sanitize_title(paper_title) if paper_title else None
        
        if sanitized_title:
            filename = f"core_contributions_{sanitized_title}.json"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"core_contributions_{timestamp}.json"
        
        file_path = output_path / filename
        
        # 保存JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(
                contribution.to_dict(),
                f,
                ensure_ascii=False,
                indent=2
            )
        
        logger.info(f"核心贡献已保存: {file_path}")
        return str(file_path)


def load_config_from_env() -> ExtractionConfig:
    """从.env文件加载配置（使用Generate Model）"""
    load_dotenv()
    
    api_key = os.getenv('Generate_API_KEY')
    api_url = os.getenv('Generate_API_URL')
    model_name = os.getenv('Generate_MODEL')
    
    if not all([api_key, api_url, model_name]):
        raise ValueError(".env文件中缺少必要的配置: Generate_API_KEY, Generate_API_URL, Generate_MODEL")
    
    return ExtractionConfig(
        api_key=api_key,
        api_url=api_url,
        model_name=model_name
    )
