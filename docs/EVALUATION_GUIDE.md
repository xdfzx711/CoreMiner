# Step 5: 评估模块使用指南

## 📋 概述

Step 5 评估模块用于评估论文贡献摘要的质量，主要通过ROUGE指标对比：
1. **Original Summary** (Step 3 LLM提取) vs **参考摘要**
2. **Final Summary** (Step 4 优化后) vs **参考摘要**
3. **Final** vs **Original** (改进分析)

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

新增依赖：
- `rouge-score==0.1.2` - ROUGE评估
- `matplotlib>=3.7.0` - 可视化
- `numpy>=1.24.0` - 数值计算

### 2. 准备数据

确保以下文件存在：

```
CoreMiner/
├── Manual_Summary_Generation.json  # 参考摘要（人工标注）
├── output/
│   ├── llm_results/
│   │   └── core_contributions_*.json  # Step 3 输出
│   └── refine_results/
│       └── refine_record_*.json       # Step 4 输出
```

### 3. 运行评估

**方法一：使用快速脚本**
```bash
python run_evaluation.py
```

**方法二：直接运行**
```bash
python src/step5_evaluation/main.py
```

## 📊 输出结果

评估结果保存在 `output/evaluation_results/` 目录下：

```
evaluation_results/
├── data_preparation/
│   └── evaluation_pairs_YYYYMMDD_HHMMSS.json  # 匹配的数据对
├── rouge_scores/
│   ├── detailed_scores_YYYYMMDD_HHMMSS.json   # 详细分数
│   └── aggregate_statistics_YYYYMMDD_HHMMSS.json  # 汇总统计
├── comparison/
│   ├── original_vs_reference_YYYYMMDD_HHMMSS.csv  # 对比表格
│   ├── final_vs_reference_YYYYMMDD_HHMMSS.csv
│   └── improvement_analysis_YYYYMMDD_HHMMSS.csv   # 改进分析
└── visualization/
    ├── rouge_comparison.png      # ROUGE分数对比图
    ├── improvement_bars.png       # 改进幅度柱状图
    ├── rouge_heatmap.png          # 热力图
    └── score_distribution.png     # 分数分布图
```

## 📈 评估指标说明

### ROUGE-1
- 一元词（单词）重叠
- 衡量基本词汇匹配度

### ROUGE-2
- 二元词（连续两个词）重叠
- 衡量短语级别匹配度

### ROUGE-L
- 最长公共子序列
- 考虑句子结构相似性

每个指标包含：
- **Precision**: 候选摘要中有多少词在参考摘要中
- **Recall**: 参考摘要中有多少词被候选摘要覆盖
- **F1-Score**: Precision和Recall的调和平均

## 🔧 配置说明

在 `config.yaml` 中可以调整评估参数：

```yaml
evaluation:
  # 标题匹配相似度阈值（0-1）
  title_similarity_threshold: 0.85
  
  rouge:
    # 是否使用词干提取（将words还原为词根）
    use_stemmer: true
    language: "english"
```

## 📝 数据匹配逻辑

### 标题匹配
使用 `difflib.SequenceMatcher` 计算标题相似度：
- 默认阈值：0.85（85%相似度）
- 大小写不敏感
- 自动去除首尾空格

### 匹配流程
1. 加载 `Manual_Summary_Generation.json` 中的参考摘要
2. 扫描 `refine_results/` 中的所有论文
3. 为每篇论文在参考摘要中找最佳匹配
4. 同时匹配对应的 `llm_results/` 文件
5. 生成评估数据对

## 🎯 典型用例

### 查看单篇论文的评估结果

查看 `rouge_scores/detailed_scores_*.json`：

```json
{
  "paper_title": "...",
  "scores": {
    "original_vs_reference": {
      "rouge1": {"precision": 0.45, "recall": 0.52, "fmeasure": 0.48},
      "rouge2": {"precision": 0.28, "recall": 0.31, "fmeasure": 0.29},
      "rougeL": {"precision": 0.42, "recall": 0.48, "fmeasure": 0.45}
    },
    "final_vs_reference": {
      "rouge1": {"precision": 0.52, "recall": 0.58, "fmeasure": 0.55},
      ...
    }
  },
  "improvement": {
    "rouge1": {
      "absolute_delta": 0.07,
      "relative_improvement_percent": 14.58
    }
  }
}
```

### 查看整体统计

查看 `rouge_scores/aggregate_statistics_*.json`：

```json
{
  "total_papers": 16,
  "original_vs_reference": {
    "rouge1": {
      "fmeasure": {
        "mean": 0.485,
        "std": 0.082,
        "min": 0.321,
        "max": 0.612
      }
    }
  },
  "improvement_summary": {
    "rouge1": {
      "absolute_delta": {"mean": 0.065},
      "relative_improvement_percent": {"mean": 13.4},
      "papers_improved": 14,
      "papers_degraded": 2
    }
  }
}
```

## ⚠️ 常见问题

### 1. 没有找到匹配的论文
**原因**：标题差异太大
**解决**：
- 降低 `title_similarity_threshold`（如0.75）
- 检查 `Manual_Summary_Generation.json` 中的标题是否正确
- 手动修正标题

### 2. 评估对数量为0
**检查**：
- `llm_results/` 和 `refine_results/` 是否有文件
- 文件格式是否正确
- 查看日志中的匹配详情

### 3. 可视化图表显示异常
**解决**：
- 确保安装了matplotlib
- Windows系统需要中文字体支持
- 尝试修改 `visualizer.py` 中的字体设置

## 🔮 未来扩展

### BERTScore（计划中）
- 基于BERT语义嵌入的评估
- 更准确的语义相似度
- 配置在 `config.yaml` 中预留

### 消融实验（计划中）
- 不同输入章节组合的影响
- 文档长度策略对比
- Refine迭代次数优化

## 📞 支持

如有问题，请查看：
- 日志文件：`output/logs/coreminer.log`
- 数据匹配结果：`evaluation_results/data_preparation/`
- 详细错误信息通常在控制台输出
