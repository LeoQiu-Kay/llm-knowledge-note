# RAG（检索增强生成）

> 让 LLM 用上外部知识的核心技术。

---

## 1. 为什么要 RAG？

**LLM 知识的三大局限**：
- 训练截止后的新知识不知道
- 私有 / 公司内部知识没见过
- 容易"幻觉"编造事实

**RAG 思路**：
1. **检索**：从知识库找相关文档
2. **增强**：把文档塞进 prompt
3. **生成**：LLM 基于文档作答

**流程**：

```
用户问题 → Embedding → 向量检索 → Top-K 文档
                                    ↓
                  [问题 + 文档] → LLM → 答案
```

---

## 2. RAG 演进：Naive → Advanced → Modular

**Naive RAG**（初代）：
- 简单 chunk + embedding + 检索 + 拼接
- 问题：召回不准、文档相关性差

**Advanced RAG**：
- **Pre-retrieval**：Query 改写、扩展、分解
- **Retrieval**：混合检索（向量 + 关键词）、Rerank
- **Post-retrieval**：上下文压缩、重排序

**Modular RAG**：
- 模块化设计
- 路由（不同问题走不同检索）
- 多步检索 / 迭代 RAG
- Self-RAG（模型自决定要不要检索）

---

## 3. 文档切分（Chunking）

| 策略 | 思路 |
|---|---|
| 固定大小 | 每 chunk 500 tokens（简单但可能切断语义） |
| 按段落 / 标题 | 利用 markdown / HTML 结构 |
| 滑动窗口 + 重叠 | chunk 500，overlap 50（缓解切断） |
| 语义切分 | 用 embedding 相似度判段落边界 |
| 层级切分 | 大 chunk（章节）+ 小 chunk（段落） |

**经验**：
- 通用：500-1000 tokens / chunk，overlap 50-100
- 代码：按函数 / 类切
- 表格：每行 / 每表为单位

---

## 4. 向量数据库选型

| 数据库 | 特点 |
|---|---|
| **Faiss** | Meta 开源、本地库、速度快、无服务化 |
| **Milvus** | 开源、分布式、功能全 |
| **Qdrant** | Rust 写、性能好、过滤强 |
| **Chroma** | 轻量、嵌入式 |
| **Weaviate** | 自带 vectorizer、混合搜索 |
| **Pinecone** | 闭源 SaaS、托管 |
| **Elasticsearch** | 加 vector 支持、文本 + 向量混合 |
| **PGVector** | PostgreSQL 扩展，复用现有 DB |

**选型考虑**：规模、过滤复杂度、托管 vs 自建、与现有系统集成。

---

## 5. Embedding 模型对比

| 模型 | 特点 |
|---|---|
| OpenAI text-embedding-3 | 闭源、效果好、需 API |
| **BGE**（智源） | 开源、中英双语 |
| **E5**（MS） | 开源、英语主、多语言版 |
| **Jina** | 开源、长文本（8K） |
| **GTE**（阿里） | 开源、强中文 |
| Cohere Embed | 闭源、多语言 |

**关键维度**：
- 维度（384 / 768 / 1024 / 3072）
- 最大输入长度（512 / 8K / 32K）
- 语种支持

**评测**：MTEB（Massive Text Embedding Benchmark）。

---

## 6. Rerank：把召回 Top-K 重排

**问题**：向量检索召回 Top-K 后相关性可能不准。

**Rerank**：用更强模型对召回结果重新排序。

**模型类型**：
- **Cross-Encoder**：query + doc 一起进 BERT 输出相关性分数（比 bi-encoder 准但慢）
- **ColBERT**：late interaction，平衡速度与精度
- **bge-reranker / jina-reranker**：开源专用 reranker

**典型流程**：
1. 向量检索 top-100
2. Rerank 到 top-10
3. 给 LLM 用

**效果**：5-10% 召回率提升。

---

## 7. Query 改写 / 扩展

**问题**：用户的问题模糊、口语化，直接检索效果差。

| 技术 | 思路 |
|---|---|
| **Query Rewrite** | LLM 把口语化问题改写成检索友好的查询 |
| **Query Expansion** | 扩展同义词、上下位词 |
| **HyDE** | 让 LLM 生成"假设的答案文档"，用它检索 |
| **Multi-Query** | 生成多个变体查询，多路召回合并 |
| **Query Decomposition** | 把复杂问题分解为子问题分别检索 |

**HyDE** 直觉：用 LLM 生成的假答案做向量检索，比用问题更接近真答案的语义空间。

---

## 8. 多路召回（Hybrid Search）

**思路**：用多种检索方式同时召回，合并结果。

**常见组合**：
- **向量检索（dense）**：捕获语义
- **BM25（sparse）**：捕获关键词、稀有词
- **元数据过滤**：精确条件

**融合方式 RRF**（Reciprocal Rank Fusion）：

$$\text{score}(d) = \sum_q \frac{1}{k + \text{rank}_q(d)}$$

**符号说明**：
- $d$：文档
- $q$：召回方法（如 dense、BM25）
- $\text{rank}_q(d)$：文档 $d$ 在 $q$ 召回结果中的排名
- $k$：常数（典型 60），防止排名 1 权重过大

**实践**：Hybrid Search（dense + BM25 + RRF）通常优于纯向量。

---

## 9. RAG 评估

**评估维度**：
1. **检索质量**：召回率（relevant doc 在 top-K 比例）、MRR
2. **生成质量**：
   - **Faithfulness**：答案是否基于文档（不幻觉）
   - **Answer Relevance**：答案是否回答了问题
   - **Context Relevance**：检索的上下文是否相关
3. **端到端**：准确率、用户满意度

**工具**：
- **Ragas**：自动评估框架（用 LLM 评）
- **TruLens**：监控 + 评估
- **DeepEval**：单元测试式评估

---

## 10. RAG 常见坑

1. **Chunk 切割不当**：跨段落丢失上下文
2. **Embedding 模型不匹配**：英文模型用在中文
3. **召回不准**：没用 hybrid / rerank
4. **上下文太多**：塞太多 doc，"lost in the middle"
5. **没考虑时效性**：知识库陈旧
6. **元数据缺失**：无法过滤（如按部门、时间）
7. **幻觉**：LLM 即使有 doc 也可能编造
8. **格式不一致**：表格、代码用同 chunk 策略效果差

---

## 11. 何时不该用 RAG？

**不适合**：
1. 小知识库 + 频繁查 → 直接放 system prompt（用 Prompt Caching）
2. 极其新的事件 → 检索源也不全
3. 需深度推理 / 综合 → 单 doc 难回答
4. 创意任务 → RAG 限制创造性
5. 数学 / 代码 → 靠模型能力 > 检索

**替代**：微调（知识内化）、长上下文（全塞进 context）、Agent（动态调工具）。

---

## 12. RAG vs 长上下文 vs 微调

| 方法 | 优 | 劣 |
|---|---|---|
| **RAG** | 知识可更新、可解释、按需检索 | 检索质量瓶颈、上下文限制 |
| **长上下文** | 简单、信息保真 | 成本高、KV Cache 大、注意力分散 |
| **微调** | 模型"内化"知识 | 更新慢、可解释差 |

**实际**：
- 频繁更新 + 大量文档 → RAG
- 少量稳定知识 + 短上下文 → 长上下文 prompt
- 持久学习 + 风格定制 → 微调

**组合**：RAG + 长上下文 + 微调 都可叠加。

---

## 13. 最简记忆

```text
RAG 三步：检索 → 增强 → 生成

演进：Naive → Advanced（hybrid + rerank）→ Modular（路由 + 多步）

关键模块：
  Chunking：500-1000 tokens 通用
  Embedding：BGE / E5 / OpenAI
  向量库：Faiss / Milvus / Qdrant / Chroma
  Rerank：cross-encoder / bge-reranker
  Hybrid：dense + BM25 + RRF

评估：Ragas（faithfulness / answer / context relevance）
```

---

## 🎯 高频追问

1. **Embedding 维度越大越好吗**？不一定。大维度需要更多存储和计算；小维度（1024）已够用很多任务。

2. **RAG 用 GPT-4 还是开源**？看预算。GPT-4 质量高但贵；Llama-3-70B 接近且省钱。

3. **检索 top-K 多少合适**？通常 5-10。太少漏信息，太多注意力分散。

4. **HyDE 真有用吗**？特定场景（开放领域 QA）显著提升；专业领域可能反而误导。

5. **怎么处理表格、图像**？专门 chunker（如表格行级）、多模态 embedding（如 ColPali）。
