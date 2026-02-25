"""
全文直接提取器
不经过章节提取和清洗，直接对完整.mmd文件进行贡献提取
"""
import re
from pathlib import Path
from typing import Optional
import requests

from src.utils.logger import get_logger
from .data_models import FullTextResult, ExtractionConfig

logger = get_logger("CoreMiner.FullTextExtraction")


class FullTextExtractor:
    """全文直接提取器"""
    
    def __init__(self, config: ExtractionConfig):
        """初始化提取器
        
        Args:
            config: 提取配置
        """
        self.config = config
        self.config.validate()
        logger.info(f"初始化全文提取器，模型: {config.model_name}")
        logger.info(f"预处理模式: {config.preprocessing_mode}")
    
    def load_mmd_file(self, mmd_file_path: str) -> str:
        """加载完整.mmd文件
        
        Args:
            mmd_file_path: .mmd文件路径
            
        Returns:
            完整文件内容
        """
        try:
            with open(mmd_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"成功加载.mmd文件: {Path(mmd_file_path).name}")
            logger.info(f"文件长度: {len(content)} 字符")
            
            return content
            
        except Exception as e:
            logger.error(f"加载.mmd文件失败: {e}")
            raise
    
    def preprocess_content(self, content: str) -> str:
        """预处理内容
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        if self.config.preprocessing_mode == "none":
            # 完全不处理
            logger.info("预处理模式: none - 直接使用原始内容")
            return content
        
        elif self.config.preprocessing_mode == "minimal":
            # 最小处理：仅移除图片和表格
            logger.info("预处理模式: minimal - 移除图片和表格")
            
            # 移除Markdown图片语法 ![alt](url)
            content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
            
            # 移除简单的Markdown表格
            lines = content.split('\n')
            filtered_lines = []
            in_table = False
            
            for line in lines:
                # 检测表格分隔符行
                if re.match(r'^\s*\|?[\s\-:|]+\|[\s\-:|]*\|?\s*$', line):
                    in_table = True
                    continue
                # 检测表格行
                elif in_table and '|' in line:
                    continue
                else:
                    in_table = False
                    filtered_lines.append(line)
            
            content = '\n'.join(filtered_lines)
            
        elif self.config.preprocessing_mode == "medium":
            # 中等处理：额外移除数学公式、引用格式
            logger.info("预处理模式: medium - 移除图片、表格、公式、引用")
            
            # 先执行minimal处理
            content = self.preprocess_content(content)
            
            # 移除LaTeX公式
            content = re.sub(r'\$\$.*?\$\$', '', content, flags=re.DOTALL)  # 块公式
            content = re.sub(r'\$.*?\$', '', content)  # 行内公式
            
            # 移除引用标记 [1], [2,3], etc.
            content = re.sub(r'\[[\d,\s-]+\]', '', content)
        
        logger.info(f"预处理后长度: {len(content)} 字符")
        return content
    
    def extract_title_from_mmd(self, content: str) -> str:
        """从.mmd内容中提取标题
        
        Args:
            content: .mmd文件内容
            
        Returns:
            论文标题
        """
        # 查找第一个一级标题
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            logger.info(f"提取到标题: {title}")
            return title
        
        # 如果没有找到，返回默认值
        logger.warning("未找到标题，使用默认值")
        return "Unknown Title"
    
    def build_prompt(self, full_content: str) -> str:
        """构建全文提取的Prompt
        
        Args:
            full_content: 完整论文内容
            
        Returns:
            构建好的Prompt
        """
        prompt = f"""Role: You are an experienced academic paper reviewer skilled at precisely extracting core innovations from complete research papers.

Task: Please read the COMPLETE paper content I provide, and summarize the core contributions of this paper.

Requirements:

Information Source: Based on the ENTIRE paper content, including all sections (Abstract, Introduction, Method, Experiments, Conclusion, etc.). Focus on identifying the key innovations, new methods, new findings, new frameworks, or significant performance improvements proposed by the authors.

Output Format: Please output as a concise, coherent paragraph-style summary, strictly limited to 3-5 sentences.

Content Requirements: Avoid listing bullet points; instead, connect the contributions through logical connectors (e.g., "First," "Through...," "Finally..."). Synthesize information from across the paper to provide a comprehensive view.

Language Style: Maintain academic rigor, get straight to the point, and avoid redundant openings like "This paper argues that."

Complete Paper Content:

{full_content}

Please output the core contribution summary directly in English, without repeating the above requirements."""
        
        return prompt
    
    def call_llm_api(self, prompt: str) -> dict:
        """调用LLM API
        
        Args:
            prompt: 完整提示词
            
        Returns:
            API响应
        """
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
            logger.info(f"Prompt长度: {len(prompt)} 字符")
            
            response = requests.post(
                self.config.api_url,
                json=payload,
                headers=headers,
                timeout=120  # 增加超时时间，因为输入更长
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
    
    def extract(self, mmd_file_path: str) -> FullTextResult:
        """执行全文提取
        
        Args:
            mmd_file_path: .mmd文件路径
            
        Returns:
            提取结果
        """
        try:
            # 1. 加载.mmd文件
            logger.info("=" * 80)
            logger.info("开始全文提取流程")
            logger.info("=" * 80)
            
            full_content = self.load_mmd_file(mmd_file_path)
            
            # 2. 提取标题
            title = self.extract_title_from_mmd(full_content)
            
            # 3. 预处理（根据配置模式）
            processed_content = self.preprocess_content(full_content)
            
            # 4. 构建Prompt
            prompt = self.build_prompt(processed_content)
            
            # 5. 调用LLM API
            api_response = self.call_llm_api(prompt)
            
            # 6. 解析响应
            if 'choices' not in api_response or not api_response['choices']:
                raise ValueError("LLM API响应格式异常")
            
            contribution_text = api_response['choices'][0].get('message', {}).get('content', '')
            
            if not contribution_text:
                raise ValueError("LLM API返回空内容")
            
            # 7. 创建结果对象
            result = FullTextResult(
                source_file=str(Path(mmd_file_path).name),
                title=title,
                contributions_summary=contribution_text.strip(),
                model_used=self.config.model_name,
                prompt_tokens=api_response.get('usage', {}).get('prompt_tokens', 0),
                completion_tokens=api_response.get('usage', {}).get('completion_tokens', 0),
                input_length=len(processed_content),
                preprocessing_mode=self.config.preprocessing_mode
            )
            
            logger.info("=" * 80)
            logger.info("全文提取完成")
            logger.info("=" * 80)
            logger.info(f"标题: {title}")
            logger.info(f"输入长度: {result.input_length} 字符")
            logger.info(f"Prompt tokens: {result.prompt_tokens}")
            logger.info(f"Completion tokens: {result.completion_tokens}")
            logger.info(f"摘要长度: {len(result.contributions_summary)} 字符")
            
            return result
            
        except Exception as e:
            logger.error(f"全文提取失败: {e}")
            raise
