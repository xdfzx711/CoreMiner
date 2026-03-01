# CoreMiner - 论文贡献提取系统

基于深度学习的科技论文贡献总结自动生成系统。输入一篇AI学术论文的PDF，自动提取并生成其核心贡献的简洁摘要（3-5句话）。



## 系统架构

### 完整的处理流程（4个步骤）

```
PDF文件输入 
  ↓
[Step 1] PDF解析 (DeepSeek-OCR)
  ├─ PDF → Markdown转换
  └─ 输出: .mmd文件
  ↓
[Step 2] 结构化提取 + 清洗
  ├─ 提取：Abstract、Introduction后1/3、Conclusion
  ├─ 清洗：移除引用、公式、图表引用等
  └─ 输出: clean_results/*.json
  ↓
[Step 3] LLM提取贡献（第1次调用）
  ├─ 使用清洗后的文本
  ├─ LLM API调用（OpenAI/Anthropic）
  └─ 输出: llm_results/*.json
  ↓
[Step 4] 验证与优化（第2次调用）
  ├─ Validator: 验证摘要质量（评分0-10）
  ├─ Refiner: 根据批评意见优化摘要
  ├─ 迭代优化（最多3轮）
  └─ 输出: refine_results/*.json
  ↓
最终贡献摘要输出
```





## 安装和设置

### 1. 环境要求
- Python 3.9+
- DeepSeek-OCR环境（用于PDF解析）,参考项目：[DeepSeek-OCR](https://github.com/deepseek-ai/DeepSeek-OCR)

### 2. 安装依赖
```bash
conda create -n coreminer python=3.10
conda activate coreminer
pip install -r requirements.txt
```

主要依赖包括：
- `openai==1.3.9` - OpenAI API客户端
- `anthropic==0.7.8` - Anthropic Claude API客户端  
- `pydantic==2.5.3` - 数据验证和模型
- `pyyaml>=6.0.1` - 配置文件解析
- `python-dotenv==1.0.0` - 环境变量管理
- `requests==2.31.0` - HTTP请求

### 3. 配置API密钥

在项目根目录创建 `.env` 文件：
```bash
# Step3 LLM提取配置
Generate_API_KEY="Your_API_Key"
Generate_API_URL=" "
Generate_MODEL=" "

# Step4 验证器配置  
JUDGE_API_KEY="Your_API_Key"
JUDGE_API_URL=" "
JUDGE_MODEL=" "

# Step4 优化器配置
Refine_API_KEY="Your_API_Key"
Refine_API_URL=" "
Refine_MODEL=" "
```


## 使用方法

### 快速开始 - 完整流程（Step 1-4）

#### 前置步骤：准备输入文件

1. **准备PDF文件**  
   将论文PDF放入 `/DeepSeek-OCR/input` 目录

2. **使用DeepSeek-OCR解析PDF（Step 1）**
   ```bash
   cd DeepSeek-OCR/DeepSeek-OCR-master/DeepSeek-OCR-vllm
   python run_dpsk_ocr_pdf.py --pdf_path <your_pdf_path>
   ```
   
   输出: `.mmd` 文件保存在 `DeepSeek-OCR/output/` 目录

#### 运行主流程（Step 2-4）

3. **编辑 `src/main.py` 配置输入文件路径**
   ```python
   # Step 2配置
   mmd_file = Path(r"Your Path")
   ```

4. **运行完整流程**
   ```bash
   python src/main.py
   ```

流程执行：
- **Step 2**: 结构化提取和清洗
  - 输入: `.mmd` 文件
  - 输出: `output/clean_results/extracted_result_*.json`
  
- **Step 3**: LLM提取核心贡献
  - 输入: Step2的清洗结果
  - 输出: `output/llm_results/core_contributions_*.json`
  
- **Step 4**: 验证和优化
  - 输入: Step2原文 + Step3摘要
  - 输出: `output/refine_results/refine_record_*.json`

### 输出格式

#### Step 2输出示例 (extracted_result_*.json)
```json
{
  "source_file": "paper.mmd",
  "title": "论文标题",
  "original": {
    "abstract": "原始摘要...",
    "introduction_1_3": "引言后1/3...",
    "conclusion": "结论..."
  },
  "cleaned": {
    "abstract": "清洗后的摘要...",
    "introduction_1_3": "清洗后的引言...",
    "conclusion": "清洗后的结论..."
  },
  "stats": {
    "abstract": {"citations_removed": 10, "formulas_replaced": 5}
  }
}
```

#### Step 3输出示例 (core_contributions_*.json)
```json
{
  "source_file": "extracted_result_*.json",
  "title": "论文标题",
  "contributions_summary": "This paper introduces... [3-5句话的贡献摘要]",
  "model_used": "gpt-4-turbo-preview",
  "prompt_tokens": 1500,
  "completion_tokens": 200,
  "extraction_timestamp": "2026-01-30T10:33:25"
}
```

#### Step 4输出示例 (refine_record_*.json)
```json
{
  "paper_title": "论文标题",
  "original_summary": "初始摘要...",
  "original_validation": {
    "is_valid": false,
    "score": 6,
    "missing_points": ["缺失的贡献点1", "缺失的贡献点2"],
    "unsupported_claims": ["无依据的声称1"],
    "critique": "详细的批评意见..."
  },
  "refinement_applied": true,
  "refinement_iterations": [
    {
      "iteration": 1,
      "summary": "第1次优化后的摘要...",
      "validation": {"score": 7, ...}
    },
    {
      "iteration": 2,
      "summary": "第2次优化后的摘要...",
      "validation": {"score": 9, ...}
    }
  ],
  "final_summary": "最终优化后的摘要...",
  "final_validation": {
    "is_valid": true,
    "score": 9,
    "missing_points": [],
    "unsupported_claims": []
  },
  "total_iterations": 2
}
```



## 贡献指南

欢迎提交Issue和Pull Request！

开发建议：
1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 许可证

MIT License

## 联系方式

如有问题或建议，请通过Issue反馈。

## 联系方式

如有问题或建议，请提交Issue。
