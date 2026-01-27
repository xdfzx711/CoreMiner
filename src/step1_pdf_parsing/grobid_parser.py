"""
Grobid PDF解析器
用于调用Grobid服务解析PDF并提取结构化信息
"""
import requests
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any
from pathlib import Path
from src.utils.logger import get_logger

# 关闭SSL警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = get_logger("CoreMiner.Grobid")


class GrobidParser:
    """
    Grobid PDF解析器
    调用本地或远程Grobid服务来解析PDF
    """
    
    # Grobid API端点
    PROCESS_ENDPOINT = "/api/processFulltextDocument"
    SERVICE_HEALTH_CHECK = "/api/isalive"
    
    def __init__(self, service_url: str = "http://localhost:8070", timeout: int = 60):
        """
        初始化Grobid解析器
        
        Args:
            service_url: Grobid服务地址（如 http://localhost:8070）
            timeout: 请求超时时间（秒）
        """
        self.service_url = service_url.rstrip("/")
        self.timeout = timeout
        
        # 创建持久化 Session，提高连接效率
        self.session = requests.Session()
        self.session.verify = False
        self.session.proxies = {'http': None, 'https': None}
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        })
        
        self._verify_service()
    
    def _verify_service(self) -> bool:
        """
        验证Grobid服务是否可用
        
        Returns:
            服务是否可用
        """
        try:
            url = f"{self.service_url}{self.SERVICE_HEALTH_CHECK}"
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                logger.info(f"Grobid服务可用: {self.service_url}")
                return True
            else:
                logger.warning(
                    f"Grobid服务返回异常状态码 {response.status_code}"
                )
                return False
        except requests.ConnectionError as e:
            logger.error(f"无法连接到Grobid服务 {self.service_url}: {e}")
            return False
        except Exception as e:
            logger.error(f"检查Grobid服务时出错: {e}")
            return False
    
    def parse_pdf(
        self, pdf_path: str, include_raw_affiliation: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        解析PDF文件
        
        Args:
            pdf_path: PDF文件路径
            include_raw_affiliation: 是否包含原始機構信息
        
        Returns:
            解析结果字典，包含：
            - xml: 原始Grobid XML
            - text: 提取的文本
            - title: 论文标题
            - authors: 作者列表
            - abstract: 摘要
            - success: 是否解析成功
            - error: 错误信息（如有）
        """
        pdf_path = Path(pdf_path)
        
        # 验证文件存在
        if not pdf_path.exists():
            logger.error(f"PDF文件不存在: {pdf_path}")
            return None
        
        # 验证文件是PDF
        if pdf_path.suffix.lower() != ".pdf":
            logger.error(f"文件不是PDF格式: {pdf_path}")
            return None
        
        try:
            logger.info(f"开始解析PDF: {pdf_path}")
            
            # 打开PDF文件并发送到Grobid
            with open(pdf_path, "rb") as f:
                files = {"input": f}
                params = {
                    "consolidateHeader": 1,
                    "includeRawAffiliation": 1 if include_raw_affiliation else 0,
                }
                
                url = f"{self.service_url}{self.PROCESS_ENDPOINT}"
                response = self.session.post(
                    url,
                    files=files,
                    params=params,
                    timeout=self.timeout
                )
            
            # 检查响应
            if response.status_code != 200:
                logger.error(
                    f"Grobid返回错误状态码 {response.status_code}: {response.text}"
                )
                return {
                    "success": False,
                    "error": f"Grobid返回状态码 {response.status_code}",
                }
            
            # 解析XML响应
            xml_content = response.text
            result = self._parse_xml(xml_content, pdf_path)
            result["xml"] = xml_content  # 保存原始XML
            result["success"] = True
            
            logger.info(f"PDF解析成功: {pdf_path}")
            return result
            
        except requests.Timeout:
            error_msg = f"Grobid请求超时 ({self.timeout}秒)"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except requests.RequestException as e:
            error_msg = f"Grobid请求失败: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"PDF解析失败: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def _parse_xml(self, xml_content: str, pdf_path: Path) -> Dict[str, Any]:
        """
        解析Grobid返回的XML
        
        Args:
            xml_content: XML字符串
            pdf_path: 源PDF路径
        
        Returns:
            提取的结构化信息
        """
        result = {
            "pdf_path": str(pdf_path),
            "title": "",
            "authors": [],
            "abstract": "",
            "text": "",
        }
        
        try:
            root = ET.fromstring(xml_content)
            
            # 定义命名空间
            namespaces = {'tei': 'http://www.tei-c.org/ns/1.0'}
            
            # 提取标题
            title_elem = root.find(".//tei:title[@level='a']", namespaces)
            if title_elem is not None and title_elem.text:
                result["title"] = title_elem.text.strip()
            
            # 提取作者
            authors = []
            for author_elem in root.findall(".//tei:author", namespaces):
                author_parts = []
                
                firstname = author_elem.find(".//tei:firstname", namespaces)
                if firstname is not None and firstname.text:
                    author_parts.append(firstname.text.strip())
                
                lastname = author_elem.find(".//tei:lastname", namespaces)
                if lastname is not None and lastname.text:
                    author_parts.append(lastname.text.strip())
                
                if author_parts:
                    authors.append(" ".join(author_parts))
            result["authors"] = authors
            
            # 提取摘要
            abstract_elem = root.find(".//tei:abstract", namespaces)
            if abstract_elem is not None:
                abstract_text = "".join(abstract_elem.itertext()).strip()
                result["abstract"] = abstract_text
            
            # 提取全文 - 包括正文(body)和附录(back)的所有内容
            full_text_parts = []
            
            # 1. 提取正文部分 (body)
            body_elem = root.find(".//tei:body", namespaces)
            if body_elem is not None:
                body_text = "".join(body_elem.itertext()).strip()
                if body_text:
                    full_text_parts.append(body_text)
            
            # 2. 提取附录部分 (back) - 包括参考文献等
            back_elem = root.find(".//tei:back", namespaces)
            if back_elem is not None:
                back_text = "".join(back_elem.itertext()).strip()
                if back_text:
                    full_text_parts.append(back_text)
            
            # 3. 如果上述方法都没有提取到内容，尝试从整个text元素提取
            if not full_text_parts:
                text_elem = root.find(".//tei:text", namespaces)
                if text_elem is not None:
                    all_text = "".join(text_elem.itertext()).strip()
                    if all_text:
                        full_text_parts.append(all_text)
            
            # 合并所有文本部分
            result["text"] = "\n\n".join(full_text_parts) if full_text_parts else ""
            
            logger.debug(f"XML解析完成，提取标题: {result['title'][:50]}...")
            logger.info(f"成功提取: 标题长度={len(result['title'])}, 作者数={len(result['authors'])}, 摘要长度={len(result['abstract'])}, 正文长度={len(result['text'])}")
            return result
            
        except ET.ParseError as e:
            logger.error(f"XML解析错误: {e}")
            return result
        except Exception as e:
            logger.error(f"提取XML信息时出错: {e}")
            return result
    
    def parse_pdf_with_retries(
        self,
        pdf_path: str,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> Optional[Dict[str, Any]]:
        """
        带重试的PDF解析
        
        Args:
            pdf_path: PDF文件路径
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
        
        Returns:
            解析结果
        """
        import time
        
        for attempt in range(max_retries):
            try:
                result = self.parse_pdf(pdf_path)
                if result and result.get("success"):
                    return result
                
                if attempt < max_retries - 1:
                    logger.warning(
                        f"解析失败，{retry_delay}秒后进行第 {attempt + 2} 次尝试..."
                    )
                    time.sleep(retry_delay)
            except Exception as e:
                logger.error(f"第 {attempt + 1} 次尝试失败: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        logger.error(f"在 {max_retries} 次尝试后仍然无法解析PDF")
        return None
