# KV Cache（必考）

> 自回归推理的核心优化，必须能默写显存公式并解释 prefill/decode 差异。

---

## Q1: 为什么需要 KV Cache？

**答**：
**问题背景**：
- LLM 推理是自回归的：生成第 $t$ 个 token 需要做一次 attention 计算。
- 朴素实现：每生成一个新 token，对所有历史 token 重新算一次 attention，复杂度 $O(t^2)$，浪费严重。

**关键观察**：
- 历史 token 的 K 和 V 在生成过程中**不变**（因为它们的输入不变，权重不变）。
- 只需要算新 token 的 Q、K、V，并把新 K/V 加入缓存。
- 复杂度从 $O(t^2)$ 降到 $O(t)$ per step（线性于历史长度）。

**伪代码**：
```python
# 朴素
for t in range(T):
    out = attention(x[:t+1], x[:t+1], x[:t+1])  # O((t+1)^2)
    next_token = sample(out[-1])

# KV Cache
K_cache, V_cache = [], []
for t in range(T):
    q, k, v = compute_qkv(x_new)
    K_cache.append(k); V_cache.append(v)
    out = attention(q, K_cache, V_cache)  # O(t+1)
    next_token = sample(out)
```

---

## Q2: KV Cache 的显存占用公式？

**答**：**必背公式**：

$$\text{Memory} = 2 \times L \times s \times h \times d_h \times \text{dtype\_bytes}$$

- **2**：K 和 V 两份
- **L**：层数
- **s**：序列长度（包含 prompt + 生成）
- **h**：KV 头数（MHA 是 attention 头数；GQA 是分组数）
- **d_h**：head_dim
- **dtype_bytes**：BF16/FP16 = 2，FP8/INT8 = 1，INT4 = 0.5

**例 1**：LLaMA-2-7B，FP16，4K 序列
- L=32, h=32（MHA）, d_h=128
- KV Cache = $2 \times 32 \times 4096 \times 32 \times 128 \times 2 \approx 2$ GB

**例 2**：LLaMA-2-70B，FP16，4K 序列
- L=80, h=8（GQA, g=8）, d_h=128
- KV Cache = $2 \times 80 \times 4096 \times 8 \times 128 \times 2 \approx 1.3$ GB

**例 3**：LLaMA-3-70B，FP16，128K 序列
- L=80, h=8, d_h=128
- KV Cache = $2 \times 80 \times 131072 \times 8 \times 128 \times 2 \approx 42$ GB（**已经吃掉一张 A100**）

---

## Q3: Prefill 阶段 vs Decode 阶段？

**答**：

| 阶段 | 描述 | 输入 | 输出 | 计算特性 |
|------|------|------|------|---------|
| **Prefill** | 处理整个 prompt | n 个 token | n 个位置的隐藏态 | **Compute-bound**（并行算所有位置） |
| **Decode** | 逐个生成新 token | 1 个 token + KV Cache | 1 个 token | **Memory-bound**（读 KV Cache 主导） |

**Prefill**：
- 一次性算所有 token 的 KV
- GPU 利用率高（大矩阵乘）
- 时间复杂度 $O(n^2 d)$，但全程并行
- TTFT（Time To First Token）由此决定

**Decode**：
- 每步只算 1 个 token
- 矩阵乘退化为矩阵-向量乘
- **读 KV Cache 的带宽成为瓶颈**
- TPOT（Time Per Output Token）由此决定

**实际推理**：
```
prompt 长度 n, 生成长度 m
Prefill: O(n^2) 一次
Decode: O(t) per step, 共 m 步 → O(m × (n+m/2))
```

---

## Q4: 为什么 Decode 是 Memory-Bound？

**答**：
**Roofline 分析**：
- Decode 阶段，单个 token 的 attention 计算需要读 $O(t \cdot d)$ 数据，做 $O(t \cdot d)$ FLOPs。
- 算术强度 = FLOPs / Bytes ≈ 0.5（FP16），远低于 GPU 算力/带宽比（A100 约 100）。
- 所以是 **memory-bound**。

**意味着**：
- 加大 batch size 几乎"免费"（同一份 KV Cache 不用读多次，但 weight 复用更好）
- 加 FLOPs 优化（如 FlashAttention 减少 IO）效果显著
- 算力增长意义有限（HBM 带宽才是关键）

---

## Q5: KV Cache 的瓶颈与优化方向？

**答**：

**瓶颈**：
1. **显存占用**：长上下文 / 大并发时显存爆炸
2. **HBM 带宽**：decode 阶段需要反复读 KV
3. **碎片化**：不同请求长度不同导致内存浪费

**优化方向**：
1. **架构层**：MQA / GQA / MLA（减少 K/V 数量）
2. **量化**：KV Cache 量化到 INT8/INT4
3. **稀疏化/淘汰**：H2O、StreamingLLM、SnapKV（丢弃不重要 token）
4. **内存管理**：PagedAttention（vLLM）减少碎片
5. **复用**：Prefix Caching（跨请求共享）
6. **Offload**：CPU/NVMe offload（牺牲速度换显存）

---

## Q6: 单卡能跑多少并发？

**答**：
**估算公式**：
$$N_{\text{concurrent}} = \frac{\text{Total GPU Mem} - \text{Model Mem} - \text{Overhead}}{\text{KV Cache per request}}$$

**例**：LLaMA-3-70B，BF16，单卡 80GB（A100）：
- 模型权重：~140GB → 需要 2 卡 tp=2
- 假设 8 卡 H100 80GB 部署（640GB 总）
- 模型 + 激活：~200GB
- 剩余 KV Cache 可用：~400GB
- 每个 4K 请求 KV Cache：~1.3GB
- 理论并发：~300

**实际**：
- vLLM 的 PagedAttention 显著提高利用率
- 还可加 prefix caching 进一步提升

---

## Q7: KV Cache 与 Prompt Caching？

**答**：
**Prompt Caching**：跨请求复用相同 prompt 的 KV Cache。

**典型场景**：
- 系统 prompt 重复（如 RAG 模板）
- 多轮对话历史
- Few-shot 示例

**实现**（如 Anthropic Claude 的 prompt caching）：
- 缓存按前缀对齐的 KV
- 命中前缀直接复用，跳过 prefill
- 大幅降低 TTFT 和成本

**框架支持**：
- vLLM：Automatic Prefix Caching
- SGLang：RadixAttention（基于 radix tree）
- Anthropic API：显式标记 cacheable section

---

## Q8: KV Cache 在多轮对话中的处理？

**答**：
**朴素**：每轮请求把完整历史发给服务，服务做完整 prefill。

**问题**：随轮数增长，prefill 越来越长，浪费。

**优化**：
1. **会话级 KV Cache**：服务端保留会话状态，下一轮只需 prefill 新内容。
2. **Prefix Caching**：自动复用相同前缀。
3. **Session Affinity**：负载均衡时让同会话路由到同一节点。

---

## Q9: KV Cache 数据布局？

**答**：
**两种主流布局**：
- **[B, L, H, S, D]**：batch × layer × head × seq × dim
- **[L, B, S, H, D]**：layer × batch × seq × head × dim

**实际选择**：
- 影响访存连续性
- FlashAttention 等 kernel 内部偏好特定布局
- 框架（vLLM、TRT-LLM）内部抽象，用户一般不直接接触

---

## 🎯 高频追问

1. **KV Cache 能否压缩到 0**？理论上可以重计算（recompute）替代，但每步都重算太慢。可以**部分重算**（如 attention sink 保留首部，远处 token 淘汰后需要时重算）。
2. **GQA 怎么影响 KV Cache 公式**？把公式中的 `h`（头数）换成 `g`（组数），KV Cache 缩小 h/g 倍。
3. **MLA 的 KV Cache 怎么算**？$L \times s \times (d_c + d^R_h)$，比 GQA 还小。
4. **KV Cache 在 Encoder-Decoder 中怎么处理**？Decoder self-attention 有 KV Cache，Cross-attention 的 K/V 来自 encoder（一次性计算，整段缓存）。
5. **为什么不能直接用更大显存解决一切**？显存有摩尔定律瓶颈，HBM 容量增长慢于模型规模增长。优化必不可少。
