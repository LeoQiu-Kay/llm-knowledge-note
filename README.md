# OfferPilot 多方向面试知识库

> 本仓库是 OfferPilot「八股」模块绑定的 GitHub 内容仓库，按 Track 整理面试高频知识与参考答案。
> 当前包含 **大模型算法、Java 后端开发、Agent 应用开发**，每个知识点由精读正文和同序号 QA 配套组成。

## 📁 目录结构

```text
.
├── tracks.json                    # Track 元数据与顺序
├── 01-基础篇 ... 10-手撕代码篇       # LLM Track（兼容既有 URL）
└── tracks/
    ├── java/
    │   ├── 01-Java核心/
    │   └── 02-Spring与数据/
    └── agent/
        ├── 01-Agent基础/
        └── 02-Agent工程化/
```

新 Track 的 Markdown 使用稳定 front matter slug，移动章节或调整编号时不会改变线上 URL：

```md
---
slug: java-collections
title: Java 集合框架
---
```

正文与 `QA/` 下同序号文件共用基础 slug，QA 页面与题库自动追加 `-qa`。

## 大模型算法 Track

### [01-基础篇/](./01-基础篇/) — 数学与机器学习基础
- [01-概率与信息论.md](./01-基础篇/01-概率与信息论.md) — KL 散度、交叉熵、PPL
- [02-线性代数.md](./01-基础篇/02-线性代数.md) — 矩阵分解、低秩、范数
- [03-优化与训练.md](./01-基础篇/03-优化与训练.md) — Adam、混合精度、梯度问题
- [04-归一化方法.md](./01-基础篇/04-归一化方法.md) — LN / RMSNorm / Pre-Post Norm
- [05-激活函数.md](./01-基础篇/05-激活函数.md) — GELU / SwiGLU / Softmax

### [02-Transformer篇/](./02-Transformer篇/) — 架构与核心机制
- [01-整体架构.md](./02-Transformer篇/01-整体架构.md) — Encoder/Decoder、Causal Mask
- [02-注意力机制.md](./02-Transformer篇/02-注意力机制.md) — Self-Attention、MHA
- [03-注意力机制演进.md](./02-Transformer篇/03-注意力机制演进.md) — MHA / MQA / GQA / MLA
- [04-位置编码.md](./02-Transformer篇/04-位置编码.md) — Sinusoidal / RoPE / ALiBi / YaRN
- [05-FFN与残差.md](./02-Transformer篇/05-FFN与残差.md) — FFN 设计、残差连接
- [06-Tokenization.md](./02-Transformer篇/06-Tokenization.md) — BPE / WordPiece / SP

### [03-训练与对齐篇/](./03-训练与对齐篇/) — 训练范式与 RLHF
- [01-预训练.md](./03-训练与对齐篇/01-预训练.md) — CLM/MLM、Scaling Laws
- [02-监督微调SFT.md](./03-训练与对齐篇/02-监督微调SFT.md) — LoRA、QLoRA、PEFT
- [03-对齐与强化学习.md](./03-训练与对齐篇/03-对齐与强化学习.md) — PPO / DPO / GRPO
- [04-推理时计算.md](./03-训练与对齐篇/04-推理时计算.md) — CoT、o1/R1、PRM
- [05-解码与采样.md](./03-训练与对齐篇/05-解码与采样.md) — Top-k/p、温度
- [06-OnPolicy蒸馏OPD.md](./03-训练与对齐篇/06-OnPolicy蒸馏OPD.md) — On-Policy Distillation vs SFT vs RL
- [07-DeepSeek-R1论文解读.md](./03-训练与对齐篇/07-DeepSeek-R1论文解读.md) — R1-Zero 纯 RL + GRPO + 四阶段流水线

### [04-训练推理加速篇/](./04-训练推理加速篇/) — 推理优化
- [01-KVCache.md](./04-训练推理加速篇/01-KVCache.md) — 原理、显存计算
- [02-KVCache压缩.md](./04-训练推理加速篇/02-KVCache压缩.md) — 量化、淘汰
- [03-高效注意力算法.md](./04-训练推理加速篇/03-高效注意力算法.md) — FlashAttention、PagedAttention
- [04-批处理与调度.md](./04-训练推理加速篇/04-批处理与调度.md) — Continuous Batching、PD 分离
- [05-量化.md](./04-训练推理加速篇/05-量化.md) — GPTQ、AWQ、SmoothQuant
- [06-蒸馏.md](./04-训练推理加速篇/06-蒸馏.md) — 知识蒸馏、白盒/黑盒
- [07-投机解码.md](./04-训练推理加速篇/07-投机解码.md) — Speculative、Medusa、EAGLE

### [05-分布式训练篇/](./05-分布式训练篇/) — 并行与扩展
- [01-并行策略.md](./05-分布式训练篇/01-并行策略.md) — DP/TP/PP/SP/EP
- [02-通信与显存.md](./05-分布式训练篇/02-通信与显存.md) — ZeRO、显存估算
- [03-训练稳定性.md](./05-分布式训练篇/03-训练稳定性.md) — Loss spike、BF16

### [06-模型架构演进篇/](./06-模型架构演进篇/) — 主流模型
- [01-主流开源模型.md](./06-模型架构演进篇/01-主流开源模型.md) — LLaMA/Qwen/DeepSeek
- [02-MoE混合专家.md](./06-模型架构演进篇/02-MoE混合专家.md) — 路由、负载均衡
- [03-长上下文模型.md](./06-模型架构演进篇/03-长上下文模型.md) — 外推、Ring Attention
- [04-多模态.md](./06-模型架构演进篇/04-多模态.md) — VLM、Q-Former

### [07-评测与部署篇/](./07-评测与部署篇/) — 评测与工程
- [01-评测.md](./07-评测与部署篇/01-评测.md) — MMLU、Arena
- [02-推理框架.md](./07-评测与部署篇/02-推理框架.md) — vLLM、SGLang、TRT-LLM
- [03-工程相关.md](./07-评测与部署篇/03-工程相关.md) — TTFT/TPOT、SLA

### [08-应用与生态篇/](./08-应用与生态篇/) — RAG/Agent
- [01-RAG.md](./08-应用与生态篇/01-RAG.md) — 检索增强生成
- [02-Agent.md](./08-应用与生态篇/02-Agent.md) — ReAct、Function Calling
- [03-提示工程.md](./08-应用与生态篇/03-提示工程.md) — CoT、注入防御

### [09-面试灵魂拷问/](./09-面试灵魂拷问/) — 开放题
- [README.md](./09-面试灵魂拷问/README.md) — 总索引 + 答题方法论
- [01-基础篇.md](./09-面试灵魂拷问/01-基础篇.md) — 手撕交叉熵、Adam 优化器（2 题）
- [02-Transformer篇.md](./09-面试灵魂拷问/02-Transformer篇.md) — 注意力 / 位置编码 / 归一化 / 激活（7 题）
- [03-训练与对齐篇.md](./09-面试灵魂拷问/03-训练与对齐篇.md) — PPO / DPO / GRPO / LoRA / GAE（6 题）
- [04-训练推理加速篇.md](./09-面试灵魂拷问/04-训练推理加速篇.md) — FlashAttention / KV Cache / 量化（3 题）
- [05-分布式与稳定性篇.md](./09-面试灵魂拷问/05-分布式与稳定性篇.md) — Loss spike 排查（1 题）
- [06-模型架构演进篇.md](./09-面试灵魂拷问/06-模型架构演进篇.md) — MoE / 长上下文（2 题）
- [07-Scaling与认知篇.md](./09-面试灵魂拷问/07-Scaling与认知篇.md) — Chinchilla / 幻觉（2 题）
- [08-开放设计题.md](./09-面试灵魂拷问/08-开放设计题.md) — 下一代 LLM 架构（1 题）

### [10-手撕代码篇/](./10-手撕代码篇/) — 白板手写代码
- [README.md](./10-手撕代码篇/README.md) — 总索引 + 手撕套路
- [01-MHA.md](./10-手撕代码篇/01-MHA.md) — 多头注意力
- [02-RoPE.md](./10-手撕代码篇/02-RoPE.md) — 旋转位置编码
- [03-KL散度.md](./10-手撕代码篇/03-KL散度.md) — KL 及 k1/k2/k3 估计器
- [04-GAE.md](./10-手撕代码篇/04-GAE.md) — 优势估计反向递推
- [05-GRPO.md](./10-手撕代码篇/05-GRPO.md) — 组内归一化 + clip loss
- [06-FlashAttention.md](./10-手撕代码篇/06-FlashAttention.md) — online softmax 分块
- [07-KVCache.md](./10-手撕代码篇/07-KVCache.md) — 自回归增量解码
- [08-梯度裁剪.md](./10-手撕代码篇/08-梯度裁剪.md) — by-norm 全局裁剪
- [09-AdamW.md](./10-手撕代码篇/09-AdamW.md) — 动量 + 解耦权重衰减

---

## 📝 配套面试题（QA）

`01~08` 每个篇章下都有一个 `QA/` 子目录，为该篇**每个原理文档**配了一份对应的面试问答（`XX-主题-面试题.md`）。Java 与 Agent Track 同样使用正文 + `QA/` 配对结构。目前共 **46 份、405 道题**。

- 每题标注**难度**（⭐→⭐⭐⭐⭐）和**高频度**（🔥→🔥🔥🔥）
- 结构：`问题 → 参考答案（含公式/表格）→ 追问`
- 每份末尾附 `🎯 自测清单`

**推荐用法**：先读原理文档建立理解 → 再用同目录 `QA/` 的面试题自测 → 对照参考答案查漏补缺。

> 跨主题的开放大题见 [09-面试灵魂拷问/](./09-面试灵魂拷问/)；白板手写代码见 [10-手撕代码篇/](./10-手撕代码篇/)。

## Java 后端与 Agent Track

- [Java 核心](./tracks/java/01-Java核心/)：集合框架、JVM 内存与 GC
- [Spring 与数据](./tracks/java/02-Spring与数据/)：Spring IoC/AOP、MySQL 索引与事务
- [Agent 基础](./tracks/agent/01-Agent基础/)：运行循环/ReAct、工具调用与结构化输出
- [Agent 工程化](./tracks/agent/02-Agent工程化/)：MCP 集成、评测与可观测性

正文统一按「30 秒回答 → 核心原理 → 工程权衡 → 常见故障 → 面试追问」组织，方便先形成短答，再深入到生产实践。

---

## 🎯 使用建议

1. **第一轮通读**：把所有 MD 浏览一遍，建立全局地图
2. **第二轮精读**：针对每个高频考点形成"1 分钟讲解版 + 3 分钟深入版"
3. **第三轮模拟**：白板手写关键公式，模拟面试串讲

## 📌 三层准备维度

- **会讲**：用 1-2 句话讲清楚定义和动机
- **能写**：能在白板上写出核心公式或伪代码
- **能推**：能对比相近概念、分析优劣、推导扩展
