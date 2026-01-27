# CoreMiner - 论文贡献提取系统

基于深度学习的科技论文贡献总结自动生成系统。输入一篇AI学术论文的PDF，自动提取并生成其核心贡献的简洁摘要（3-5句话）。

## 系统架构

### 5个处理步骤

```
PDF/文本输入 
  ↓
[Step 1] PDF解析 (Grobid)
  ↓
[Step 2] 结构化提取 + 去噪
  ↓
[Step 3] LLM提取贡献点（第1次调用）
  ↓
[Step 4] Refine验证（第2次调用）
  ↓
[Step 5] Fallback（长文本深度阅读，如需要）
  ↓
最终贡献摘要输出
```

### 模块说明

#### Step 1: PDF解析
- **grobid_parser.py**: 调用Grobid服务解析PDF为XML/JSON，提取标题、摘要、作者等元数据
- **pdf_handler.py**: PDF文件验证、信息获取等工具

#### Step 2: 文本提取和清理
- **structure_extractor.py**: 从Grobid XML中提取Abstract、Introduction末尾1/3、Conclusion
- **text_cleaner.py**: 去噪处理（移除引用符号`[1]`、替换公式为`<EQ>`、移除图表引用等）

#### Step 3: LLM提取贡献
- **llm_client.py**: 统一的LLM接口（支持OpenAI、Claude等）
- **contribution_extractor.py**: 调用LLM进行第一次贡献提取

#### Step 4: Refine验证
- **refine_validator.py**: 检查提取的贡献点是否在Conclusion中得到呼应
- **refiner.py**: 调用LLM进行第二次修正

#### Step 5: Fallback策略
- **long_text_reader.py**: 调用支持长上下文的模型
- **fallback_handler.py**: 判断是否触发fallback，处理异常情况

## 项目结构

```
CoreMiner/
├── README.md                          # 项目文档
├── requirements.txt                   # Python依赖
├── config.yaml                        # 配置文件
│
├── input/
│   └── sample_papers/                 # 输入PDF文件夹
│
├── output/
│   ├── results/                       # 最终结果
│   └── logs/                          # 执行日志
│
├── src/
│   ├── step1_pdf_parsing/             # Step 1: PDF解析
│   ├── step2_extraction_cleaning/     # Step 2: 提取+去噪
│   ├── step3_llm_extraction/          # Step 3: LLM提取
│   ├── step4_refine/                  # Step 4: Refine
│   ├── step5_fallback/                # Step 5: Fallback
│   ├── utils/                         # 通用工具
│   └── main.py                        # 主入口脚本
│
└── tests/                             # 单元测试
    └── fixtures/                      # 测试数据
```

## 安装和设置

### 1. 环境要求
- Python 3.9+
- Docker (用于运行Grobid)

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 启动Grobid服务

使用Docker启动本地Grobid服务：
```bash
docker pull grobid/grobid:0.7.3
docker run -t --rm -p 8070:8070 grobid/grobid:0.7.3
```

或者使用remote Grobid服务（如 https://cloud.science-miner.com/grobid/）

### 4. 配置API密钥

在项目根目录创建 `.env` 文件：
```bash
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### 5. 配置文件

编辑 `config.yaml` 根据需要调整：
- Grobid服务地址
- LLM提供商和模型
- 处理参数
- 日志配置等

## 使用方法

### 快速开始 - Step 1: PDF解析

1. **将PDF文件放入** `input/sample_papers/` 文件夹

2. **运行Step 1解析脚本**
```bash
python src/main.py
```

脚本会：
- 验证PDF文件
- 调用Grobid解析PDF
- 提取标题、作者、摘要、全文
- 保存结果到 `output/results/`

### 输出格式

解析结果以JSON格式保存，包含：
```json
{
  "success": true,
  "pdf_path": "input/sample_papers/example.pdf",
  "title": "论文标题",
  "authors": ["作者1", "作者2"],
  "abstract": "论文摘要内容...",
  "text": "完整论文文本...",
  "xml": "<TEI XML content>"
}
```

## 配置参数详解

### Grobid配置 (config.yaml)
```yaml
grobid:
  service_url: http://localhost:8070    # Grobid服务地址
  timeout: 60                            # 请求超时（秒）
  max_retries: 3                         # 最大重试次数
  retry_delay: 2                         # 重试间隔（秒）
```

### LLM配置 (config.yaml)
```yaml
llm:
  provider: "openai"                     # 选择提供商
  openai:
    model: "gpt-4-turbo-preview"
    temperature: 0.3
    max_tokens: 2000
  anthropic:
    model: "claude-3-opus-20240229"
    temperature: 0.3
    max_tokens: 2000
```

## 日志

日志文件位置: `output/logs/coreminer.log`

日志级别: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## 故障排除

### Grobid连接失败
- 检查Grobid服务是否运行: `curl http://localhost:8070/api/isalive`
- 验证config.yaml中的service_url是否正确

### PDF解析失败
- 检查PDF文件是否有效（魔术数字检查）
- 确认PDF文件大小 < 100MB
- 查看日志了解具体错误

### API密钥错误
- 确认.env文件中的密钥正确
- 检查API额度是否足够

## 下一步

当Step 1完成后，将继续实现：
- Step 2: 结构化文本提取和去噪
- Step 3: LLM贡献提取
- Step 4: Refine验证
- Step 5: Fallback策略

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交Issue。
