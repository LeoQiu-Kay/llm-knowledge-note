# RAG · 面试题

> 对应原理文档：[01-RAG.md](../01-RAG.md)
> 标注说明：难度 ⭐(简单)→⭐⭐⭐⭐(难)；高频 🔥(偶尔)→🔥🔥🔥(必问)

---

## Q1: 什么是 RAG？为什么要用它？三步流程是什么？
> 难度 ⭐ ｜ 高频 🔥🔥🔥

**RAG**（Retrieval-Augmented Generation，检索增强生成）：让 LLM 在回答前先去外部知识库检索相关文档，把文档拼进 prompt 再生成答案。

**为什么用**：解决 LLM 的三大局限
1. 训练截止后的新知识不知道
2. 私有/公司内部数据没见过
3. 容易"幻觉"编造事实

**三步**：

```
用户问题 → Embedding → 向量检索 → Top-K 文档
                                    ↓
                  [问题 + 文档] → LLM → 答案
```

**追问：RAG 和微调比，最大优势是什么？** 知识可实时更新（改库不改模型）、可溯源（带引用）、增量成本低（无需重训）。

---

## Q2: 文档怎么切（Chunking）？切大切小有什么权衡？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

**常见策略**：

| 策略 | 思路 |
|---|---|
| 固定大小 | 每 chunk 500 tokens（简单但可能切断语义） |
| 按段落/标题 | 用 markdown/HTML 结构 |
| 滑动窗口 + 重叠 | chunk 500 + overlap 50 缓解切断 |
| 语义切分 | embedding 相似度判段落边界 |
| 层级切分 | 大 chunk（章节）+ 小 chunk（段落） |

**大 vs 小的权衡**：

| | 小 chunk（~200） | 大 chunk（~1000+） |
|---|---|---|
| 召回精度 | 高（关键词集中） | 低（噪声多） |
| 上下文完整 | 差（容易丢前后文） | 好 |
| 检索成本 | 高（库膨胀） | 低 |

**经验**：通用 500-1000 tokens、overlap 50-100；代码按函数/类切；表格按行切。

**追问：为什么需要 overlap？** 防止重要信息恰好被切在 chunk 边界——重叠让边界附近的句子在两个 chunk 中都能被检索到。

---

## Q3: Embedding 模型怎么选？维度越大越好吗？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

**主流模型**：

| 模型 | 特点 |
|---|---|
| OpenAI text-embedding-3 | 闭源、效果好、需 API |
| BGE（智源） | 开源、中英双语强 |
| E5（MS） | 开源、英语主 |
| Jina | 开源、长文本（8K） |
| GTE（阿里） | 开源、中文强 |

**关键维度**：向量维度（384/768/1024/3072）、最大输入长度（512/8K/32K）、语种支持。

**维度越大越好？不一定**：
- 大维度 → 更多存储 + 更慢检索（线性增长）
- 小维度（768/1024）已够大多数任务
- MTEB 榜单也证明：维度不是单调正相关

**追问：怎么科学评估 embedding 选型？** 用 MTEB（Massive Text Embedding Benchmark）；中文场景用 C-MTEB；最终最好用业务数据自评（domain shift 很大）。

---

## Q4: Rerank 是什么？为什么向量检索之后还要 rerank？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

**问题**：向量检索（bi-encoder）把 query 和 doc 各自独立编码再算相似度，**没有交互**，精度有上限。

**Rerank**：用更强的 cross-encoder 把 query 和 doc **拼在一起**送进 BERT，输出相关性分数。

| | Bi-Encoder（检索） | Cross-Encoder（Rerank） |
|---|---|---|
| 输入 | query 和 doc 独立编码 | query+doc 拼接一起编码 |
| 交互 | 无（向量内积） | 有（token-level attention） |
| 速度 | 快（可预算向量） | 慢（每对都要跑模型） |
| 精度 | 低 | 高 |

**典型流程**：

```
向量检索 top-100  →  Rerank → top-10  →  LLM
       (粗排，快)         (精排，准)
```

**常用模型**：bge-reranker、jina-reranker、Cohere Rerank；ColBERT 是 late interaction 折中。

**效果**：通常带来 5-10% 召回率提升，是 Advanced RAG 的关键模块。

---

## Q5: 什么是 Hybrid Search？RRF 公式怎么算？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

**Hybrid Search**（混合检索）：同时用多种检索方式，合并结果。

**为什么**：
- **向量检索（dense）**：擅长语义，但对**关键词、稀有词、人名、ID**不敏感
- **BM25（sparse）**：基于关键词，擅长精确匹配，但不懂语义同义
- 两者互补 → 一起用

**RRF**（Reciprocal Rank Fusion，倒数排名融合）：

$$\text{score}(d) = \sum_q \frac{1}{k + \text{rank}_q(d)}$$

**符号**：$d$ 文档；$q$ 召回方法（dense/BM25）；$\text{rank}_q(d)$ 文档 $d$ 在 $q$ 中的排名；$k$ 常数（典型 60，防止 rank=1 权重过大）。

**为什么不用分数加权？** 不同检索方法分数量纲不一致（cosine 在 [0,1]，BM25 可能 0-50），直接加要做归一化很麻烦；RRF 只看排名，无需归一化。

**追问：BM25 为什么这么硬核还没被淘汰？** ① 关键词、ID、稀有名词向量召不回；② 零训练成本；③ 可解释；④ 工业级搜索 30 年沉淀。Elasticsearch / OpenSearch 都内置。

---

## Q6: Query 改写有哪些方式？HyDE 是什么直觉？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

**问题**：用户问题口语化、模糊、信息少，直接拿去检索效果差。

**常见技术**：

| 技术 | 思路 |
|---|---|
| Query Rewrite | LLM 把口语化问题改写成检索友好的查询 |
| Query Expansion | 扩展同义词、上下位词 |
| **HyDE** | LLM 生成"假设的答案文档"，用它做向量检索 |
| Multi-Query | 生成多个变体查询，多路召回合并 |
| Query Decomposition | 把复杂问题拆成子问题分别检索 |

**HyDE**（Hypothetical Document Embeddings）直觉：
- 问题和答案的语义空间不一样——问题是"问"，答案是"答"
- 用问题向量去匹配答案文档，距离天然较远
- 让 LLM 先"瞎编"一份假答案（hallucinated answer），用假答案的 embedding 去检索
- 假答案虽然事实可能错，但**语义空间接近真答案** → 召回更准

**适用场景**：开放域 QA 提升明显；专业领域可能反而误导（LLM 假答案错得离谱）。

---

## Q7: RAG 怎么评估？Faithfulness / Answer Relevance / Context Relevance 各是什么？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

**三层评估**：

1. **检索质量**（独立评检索）
   - **召回率 Recall@K**：相关 doc 在 top-K 的比例
   - **MRR**（Mean Reciprocal Rank）：第一个相关 doc 排名倒数的平均

2. **生成质量**（评 LLM 用上下文的能力）
   - **Faithfulness**（忠实度）：答案是否**完全基于**检索到的文档（不编造）
   - **Answer Relevance**（答案相关）：答案是否真的**回答了问题**（不答非所问）
   - **Context Relevance**（上下文相关）：检索的上下文**和问题相关**的比例

3. **端到端**：准确率、用户满意度

**工具**：
- **Ragas**：用 LLM 当裁判自动评（最流行）
- **TruLens**：监控 + 评估
- **DeepEval**：单元测试式

**追问：用 LLM 当裁判的坑？** ① 裁判模型偏好长答案；② 与人工评估有差距；③ 同一模型既生成又评分会偏袒；最好用更强模型（如 GPT-4）评弱模型，且抽样人工校准。

---

## Q8: RAG 有哪些常见坑？"Lost in the Middle"指什么？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

**常见坑**：

| 坑 | 表现 | 对策 |
|---|---|---|
| Chunk 切割不当 | 跨段落丢上下文 | 用语义/结构切，加 overlap |
| Embedding 不匹配 | 英文模型用在中文 | 选语种对的模型 |
| 召回不准 | top-K 都不相关 | Hybrid + Rerank |
| **塞太多 doc** | "lost in the middle" | 控制 top-K，关键 doc 放头尾 |
| 没考虑时效性 | 用旧知识答新问题 | 加时间过滤、定期更新 |
| 元数据缺失 | 无法按部门/时间过滤 | 加 metadata 字段 |
| 幻觉 | 即使给 doc 也编 | Faithfulness prompt + 引用强制 |

**Lost in the Middle**（Liu et al. 2023）：LLM 在长上下文中对**开头和结尾**的信息利用最好，**中间**的信息容易被忽略——所以 top-K 不能贪多，且重要 doc 应该放头尾。

**追问：RAG 怎么强制 LLM 不幻觉？** ① 在 prompt 中明确"只能基于以下文档回答，没有就说不知道"；② 要求带引用（[doc1]）；③ 输出后用另一模型做 faithfulness 校验。

---

## Q9: 什么时候**不**该用 RAG？RAG / 长上下文 / 微调怎么选？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

**不适合 RAG 的场景**：
1. 小知识库 + 高频查询 → 直接放 system prompt（用 Prompt Caching 更便宜）
2. 极其新的事件 → 检索源本身就不全
3. 需深度跨文档推理 → 单 doc 难回答
4. 创意任务 → RAG 反而限制创造性
5. 纯数学/代码 → 模型能力 > 检索

**三种方法对比**：

| 方法 | 优 | 劣 |
|---|---|---|
| RAG | 知识可更新、可解释、按需检索 | 检索质量瓶颈、上下文限制 |
| 长上下文 | 简单、信息保真 | 成本高、KV Cache 大、注意力分散 |
| 微调 | 知识"内化"、风格定制 | 更新慢、可解释差、训练成本 |

**选型直觉**：
- 频繁更新 + 海量文档 → **RAG**
- 少量稳定知识 + 短上下文 → **长上下文 prompt**
- 持久学习 + 风格/格式定制 → **微调**
- 实际产品往往**叠加**：微调基础风格 + RAG 接知识 + 长上下文容纳关键文档

---

## Q10: Naive RAG → Advanced RAG → Modular RAG 演进了什么？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

**Naive RAG**（初代，2020）：
- 流程：chunk → embedding → 向量检索 → 拼 prompt → 生成
- 问题：召回不准、文档相关性差、无重排

**Advanced RAG**：
- **Pre-retrieval**：Query 改写、扩展、分解
- **Retrieval**：Hybrid（dense + BM25 + RRF）
- **Post-retrieval**：Rerank、上下文压缩、去重

**Modular RAG**：
- **模块化**：每一步可换可组合
- **路由**：不同问题走不同检索路径（FAQ 走精确匹配，长尾问题走向量）
- **多步检索**：一次不够再来一次（iterative retrieval）
- **Self-RAG**：模型自己决定**要不要**检索、检索结果**够不够好**

**演进核心**：从"检索一次塞一次"到"按需检索 + 反馈循环"，越来越像 Agent。

**追问：Self-RAG 怎么决定要不要检索？** 训练模型输出特殊 token（如 `[Retrieve]` / `[NoRetrieve]`），相当于在生成中插入控制信号。

---

## 🎯 自测清单

- [ ] 能讲清 RAG 三步流程 + 为什么需要 RAG
- [ ] 能比较 chunk 大小的权衡 + 默认参数（500-1000 / overlap 50-100）
- [ ] 能讲清 Rerank 的 bi-encoder vs cross-encoder 差异
- [ ] 能写 RRF 公式 + 解释为什么 Hybrid 优于纯向量
- [ ] 能区分 Faithfulness / Answer Relevance / Context Relevance
