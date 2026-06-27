# KV Cache · 面试题

> 对应原理文档：[01-KVCache.md](../01-KVCache.md)
> 标注说明：难度 ⭐(简单)→⭐⭐⭐⭐(难)；高频 🔥(偶尔)→🔥🔥🔥(必问)

---

## Q1: 为什么需要 KV Cache？它把复杂度从多少降到多少？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

KV Cache（Key-Value 缓存）解决自回归生成的重复计算问题。

**朴素实现**：生成第 $t$ 个 token 时，对所有历史 token 重算一次 attention，每步 $O(t^2)$，总成本 $O(T^3)$。

**关键观察**：历史 token 的 K、V 在生成过程中**不变**（输入不变、权重不变），无需重算。

**优化做法**：把历史 K、V 缓存下来，每步只计算新 token 的 Q/K/V，然后 $\text{softmax}(qK_{\text{cache}}^T)V_{\text{cache}}$。

**复杂度**：每步从 $O(t^2)$ 降到 $O(t)$，总成本 $O(T^2)$。

**追问：Q 为什么不缓存？** Q 只用于当前 token，下一步的 Q 是新算的，没必要存。只有 K/V 会被未来所有 token "回头看"。

---

## Q2: 白板写出 KV Cache 显存公式，并算 LLaMA-2-7B 在 4K 序列下的占用
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

$$\boxed{\text{Memory} = 2 \cdot L \cdot s \cdot h \cdot d_h \cdot \text{bytes}}$$

**各项含义**：
- **2**：K 和 V 两份
- $L$：层数
- $s$：序列长度（prompt + 已生成 token）
- $h$：**KV 头数**（MHA = 注意力头数；MQA = 1；GQA = 分组数 $g$）
- $d_h$：每头维度（典型 128）
- $\text{bytes}$：单元素字节数（FP16/BF16 = 2，INT8/FP8 = 1，INT4 = 0.5）

**例：LLaMA-2-7B，FP16，4K 序列**（$L=32, h=32, d_h=128$）：

$$2 \times 32 \times 4096 \times 32 \times 128 \times 2 = 2147483648 \text{ B} \approx 2 \text{ GB}$$

**追问：LLaMA-3-70B 在 128K 序列下呢？** $L=80, h=8$（GQA），$d_h=128$：$2 \times 80 \times 131072 \times 8 \times 128 \times 2 \approx 42$ GB——单卡装不下，必须压缩或分布式。

---

## Q3: Prefill 和 Decode 有什么区别？为什么 Decode 是 memory-bound？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

| 阶段 | 输入 | 计算 | 瓶颈 | 关键指标 |
|---|---|---|---|---|
| **Prefill** | 整个 prompt（$n$ token） | 大矩阵乘，全并行 | **Compute-bound** | TTFT |
| **Decode** | 1 个 token + KV Cache | 矩阵-向量乘 | **Memory-bound** | TPOT |

**Decode memory-bound 的本质**：算术强度（Arithmetic Intensity）极低。

单 token 的 attention：
- 读：$O(t \cdot d)$ 字节（读 KV Cache）
- 算：$O(t \cdot d)$ FLOPs

$$\text{AI} = \frac{\text{FLOPs}}{\text{Bytes}} \approx 0.5 \text{ (FP16)}$$

远低于 A100 的算力/带宽比（约 100）→ GPU 算力闲置，HBM 带宽是瓶颈。

**符号说明**：TTFT = Time To First Token，TPOT = Time Per Output Token。

**追问：这个观察的工程含义？** ① 加 batch 几乎"免费"（权重读一次喂多请求）；② 减 IO 的优化（FlashAttention、量化 KV）效果显著；③ HBM 带宽比算力更值钱。

---

## Q4: GQA / MQA / MLA 怎么改变 KV Cache 显存？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

公式 $2 L s h d_h \cdot \text{bytes}$ 里**只改 $h$**：

| 架构 | KV 头数 $h$ | 相对 MHA | 例子 |
|---|---|---|---|
| **MHA** | $n_h$（注意力头数） | 1× | LLaMA-1 |
| **GQA** | $g$（分组数，$g < n_h$） | $g / n_h$× | LLaMA-2/3-70B（$g=8$） |
| **MQA** | 1 | $1/n_h$× | Falcon、PaLM |
| **MLA** | 用 $d_c$ 替换 $h \cdot d_h$ | 更小 | DeepSeek-V2/V3 |

**MQA**：Multi-Query Attention，所有头共享一份 K/V。
**GQA**：Grouped-Query Attention，每组头共享 K/V。
**MLA**：Multi-head Latent Attention，把 KV 压到低维潜空间 $d_c$（DeepSeek 典型 $d_c=512$），缓存的是潜向量而非完整 K/V。

**追问：MLA 的 KV Cache 公式怎么写？** $L \cdot s \cdot d_c \cdot \text{bytes}$（不含因子 2，因为 K/V 共用一份潜表示）。比 GQA 还小。

---

## Q5: Roofline 视角下，Decode 加 batch 为什么几乎"免费"？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

Decode 阶段两类内存读取：
1. **权重**：每张卡固定那份权重，读一次可服务整个 batch
2. **KV Cache**：每个请求独有，batch 内并行的 $B$ 个请求各读自己的 KV

加 batch 时：
- 权重读取被 $B$ 个请求**摊薄** → 算术强度提升 → 离 roofline 折点更近
- KV Cache 读取仍是每请求 $O(t \cdot d)$

直到 KV Cache 读取主导，batch 收益才衰减。所以 vLLM 等引擎追求 **Continuous Batching + 大 batch**。

**追问：什么时候 batch 不再"免费"？** 当 batch 大到使 KV Cache 总读量 ≈ 权重读量时；或显存装不下更多 KV Cache 时（这通常先到）。

---

## Q6: 估算单卡能跑多少并发？（白板题）
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

$$N_{\text{concurrent}} \approx \frac{\text{GPU 显存} - \text{模型权重} - \text{激活与开销}}{\text{每请求 KV Cache}}$$

**例：8 × H100 80GB（640 GB）跑 LLaMA-3-70B BF16**：
- 模型 + 激活：~200 GB
- 剩余给 KV Cache：~400 GB
- 每个 4K 请求 KV Cache（GQA $g=8$）：~1.3 GB
- 理论并发：~300（实际 vLLM 的 PagedAttention 还能更高）

**追问：长上下文怎么办？** 128K 序列单请求 ~42 GB，并发只剩个位数。必须组合 GQA/MLA + 量化 KV + 淘汰策略 + offload。

---

## Q7: 多卡场景下 KV Cache 怎么分布？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

| 并行方式 | KV Cache 分布 | 总量 |
|---|---|---|
| **Tensor Parallel (TP)** | 按头切分，每卡持有自己负责的头 | 总量不变，分摊到多卡 |
| **Pipeline Parallel (PP)** | 按层切分，每卡持有自己负责的层的 KV | 总量不变，分摊到多卡 |
| **Expert Parallel (EP, MoE)** | 与 KV 无关（KV 不参与专家路由） | 不变 |

**注意**：TP 不能减少**总** KV Cache，只能把它分散到多张卡；想真正减小总量，得靠架构（GQA/MLA）、量化、淘汰。

---

## Q8: Prefix Caching 是什么？哪些场景受益？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

**核心**：把多个请求共享的前缀（prompt 开头）的 KV 缓存下来，跨请求复用。命中后**直接跳过 prefill**。

**典型场景**：
1. 多用户共享同一 system prompt
2. RAG：检索模板重复
3. Few-shot 示例反复使用
4. 同一会话的多轮对话（历史轮已计算）

**框架**：
- **vLLM** Automatic Prefix Caching（基于 block hash）
- **SGLang** RadixAttention（基于 radix tree，更细粒度）
- **Anthropic API** 显式 cacheable section

**效果**：TTFT 大幅降低；按命中给折扣计费。

**追问：和 PagedAttention 什么关系？** PagedAttention 把 KV 切 block；Prefix Caching 借助 block 级哈希做去重——两者天然搭配。

---

## Q9: KV Cache 优化有哪 5 大方向？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

| 方向 | 代表方法 | 思路 |
|---|---|---|
| **架构层** | MQA / GQA / MLA | 训练时就减少 KV 数量 |
| **量化** | INT8 / INT4 / FP8 KV | 单元素更小 |
| **淘汰** | H2O / StreamingLLM / SnapKV | 删冗余 token |
| **内存管理** | PagedAttention | 消除碎片、按需分配 |
| **跨请求复用** | Prefix Caching / RadixAttention | 多请求共享前缀 |
| **Offload** | CPU / NVMe | 牺牲速度换显存 |

**实战组合**：GQA/MLA（架构）+ INT8 KV（量化）+ PagedAttention（内存）+ Prefix Caching（复用）→ 几乎是 vLLM/SGLang 的默认栈。

---

## Q10: Encoder-Decoder 模型的 KV Cache 怎么处理？
> 难度 ⭐⭐⭐ ｜ 高频 🔥

两类 attention 分开处理：
- **Decoder Self-Attention**：和纯 decoder LLM 一样，逐步累积 KV Cache
- **Cross-Attention**：K、V 来自 Encoder 的输出，**一次性算完整段**，整个解码过程**不变**——所以缓存一次后反复用

工程含义：T5、BART 这类模型，cross-attention 的 KV 是"静态缓存"，比 decoder self-attention 简单。

---

## 🎯 自测清单

- [ ] 能白板默写 KV Cache 显存公式 $2 L s h d_h \cdot \text{bytes}$ 并算具体数字
- [ ] 能说清 Prefill compute-bound vs Decode memory-bound 的本质
- [ ] 能解释 Decode 算术强度低（AI ≈ 0.5）→ HBM 带宽是瓶颈
- [ ] 能说出 GQA/MQA/MLA 各让 $h$ 变成多少
- [ ] 能估算单卡并发数（剩余显存 / 每请求 KV）
