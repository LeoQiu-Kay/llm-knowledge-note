# KV Cache（必考）

> 自回归推理的核心优化。必须能默写显存公式、解释 prefill/decode 差异。

---

## 1. 为什么需要 KV Cache？

**问题背景**：LLM 推理是自回归的——生成第 $t$ 个 token 需要做一次 attention。

**朴素实现**：每生成新 token，对所有历史 token 重新算 attention，复杂度 $O(t^2)$，浪费严重。

**关键观察**：

```text
历史 token 的 K、V 在生成过程中不变（输入不变、权重不变）。
只需算新 token 的 Q、K、V，并把新的 K/V 加入缓存。
```

复杂度从 $O(t^2)$ 降到 $O(t)$ per step（线性于历史长度）。

**伪代码对比**：
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

## 2. KV Cache 显存公式（必背）

$$\text{Memory} = 2 \cdot L \cdot s \cdot h \cdot d_h \cdot \text{bytes}$$

**符号说明**：
- **2**：K 和 V 两份
- $L$：模型层数（LLaMA-2-7B = 32，LLaMA-2-70B = 80）
- $s$：序列长度（prompt + 已生成的 token 数）
- $h$：**KV 头数**（MHA = 注意力头数；MQA = 1；GQA = 分组数 $g$）
- $d_h$：每头的维度（典型 128）
- $\text{bytes}$：单个数值字节数（BF16/FP16 = 2，INT8/FP8 = 1，INT4 = 0.5）

---

### 例子

**例 1：LLaMA-2-7B，FP16，4K 序列**
- $L = 32, h = 32, d_h = 128$
- KV Cache = $2 \times 32 \times 4096 \times 32 \times 128 \times 2 \approx 2$ GB

**例 2：LLaMA-2-70B，FP16，4K 序列**（GQA $g = 8$）
- $L = 80, h = 8, d_h = 128$
- KV Cache = $2 \times 80 \times 4096 \times 8 \times 128 \times 2 \approx 1.3$ GB

**例 3：LLaMA-3-70B，FP16，128K 序列**
- $L = 80, h = 8, d_h = 128, s = 131072$
- KV Cache = $2 \times 80 \times 131072 \times 8 \times 128 \times 2 \approx 42$ GB（**单卡装不下**）

---

## 3. Prefill 阶段 vs Decode 阶段

| 阶段 | 描述 | 输入 | 输出 | 计算特性 |
|---|---|---|---|---|
| **Prefill** | 处理整个 prompt | $n$ 个 token | $n$ 个位置的隐藏态 | **Compute-bound**（并行算所有位置） |
| **Decode** | 逐个生成新 token | 1 个 token + KV Cache | 1 个 token | **Memory-bound**（读 KV Cache 主导） |

### 3.1 Prefill

- 一次性算所有 token 的 KV
- GPU 利用率高（大矩阵乘）
- 时间复杂度 $O(n^2 d)$，但全程并行
- **TTFT**（Time To First Token）由此决定

### 3.2 Decode

- 每步只算 1 个 token
- 矩阵乘退化为矩阵-向量乘
- **读 KV Cache 的带宽**成为瓶颈
- **TPOT**（Time Per Output Token）由此决定

**符号说明**：
- TTFT：从请求到首 token 的时间
- TPOT：每个后续 token 的间隔

```text
Prefill 算力密集（GPU 并行算大矩阵）
Decode 带宽密集（频繁读 KV Cache）
```

---

## 4. 为什么 Decode 是 Memory-Bound？

**Roofline 分析**：

Decode 阶段单个 token 的 attention：
- 数据读：$O(t \cdot d)$（读 KV Cache）
- 计算：$O(t \cdot d)$ FLOPs

**算术强度**（Arithmetic Intensity）：
$$\text{AI} = \frac{\text{FLOPs}}{\text{Bytes}} \approx 0.5 \text{ (FP16)}$$

远低于 GPU 的算力/带宽比（A100 约 100）→ 是 **memory-bound**。

**意味着**：
- 加大 batch 几乎"免费"（同份 KV Cache 不用读多次，但权重读取仍要复用）
- 加 FLOPs 优化（如 FlashAttention 减 IO）效果显著
- HBM 带宽是关键，不是算力

---

## 5. KV Cache 的优化方向

| 方向 | 方法 | 效果 |
|---|---|---|
| **架构层** | MQA / GQA / MLA | 减少 K/V 数量 |
| **量化** | INT8 / INT4 / FP8 KV Cache | 单元素更小 |
| **稀疏化 / 淘汰** | H2O、StreamingLLM、SnapKV | 删冗余 token |
| **内存管理** | PagedAttention（vLLM） | 减少碎片 |
| **复用** | Prefix Caching | 跨请求共享 |
| **Offload** | CPU / NVMe | 牺牲速度换显存 |

详见 KV Cache 压缩篇、高效注意力篇。

---

## 6. 单卡能跑多少并发？

**估算公式**：

$$N_{\text{concurrent}} \approx \frac{\text{GPU Memory} - \text{Model} - \text{Overhead}}{\text{KV Cache per request}}$$

**例**：LLaMA-3-70B，BF16，8 张 H100 80GB（共 640 GB）：
- 模型 + 激活：~200 GB
- 剩余 KV Cache 可用：~400 GB
- 每个 4K 请求 KV Cache：~1.3 GB
- 理论并发：~300（实际更高，因为 vLLM 的 PagedAttention 提升利用率）

---

## 7. Prefix Caching：跨请求复用

**Prefix Caching**：缓存按前缀对齐的 KV，多个请求共享相同前缀。

**典型场景**：
- 多用户共享同一 system prompt
- RAG 中重复的检索模板
- Few-shot 示例反复使用
- 同一会话的多轮对话

**框架支持**：
- **vLLM**：Automatic Prefix Caching
- **SGLang**：RadixAttention（基于 radix tree，更细粒度）
- **Anthropic API**：显式标注 cacheable section

**效果**：命中前缀直接跳过 prefill → TTFT 大幅降低 + 成本降低。

---

## 8. 多卡 / 分布式下的 KV Cache

**Tensor Parallel（TP）下**：
- KV Cache 按头切分：每张卡只持有自己负责的头的 KV
- KV Cache 总量不变，但分布到多卡

**Pipeline Parallel（PP）下**：
- 每张卡持有自己负责的层的 KV
- 不同层 KV 在不同卡上

**专家并行（EP，MoE）**：
- 与 KV Cache 无关（KV 不参与专家路由）

---

## 9. KV Cache 数据布局

**两种主流布局**：
- $[B, L, H, S, D]$：batch × layer × head × seq × dim
- $[L, B, S, H, D]$：layer × batch × seq × head × dim

**符号说明**：
- $B$：batch
- $L$：层数
- $H$：头数
- $S$：序列长度
- $D$：head_dim

不同布局影响访存连续性。框架（vLLM、TRT-LLM）内部抽象，用户一般不直接接触。

---

## 10. 最简记忆

```text
KV Cache 解决：自回归生成时重复算历史 K/V → 缓存复用
显存公式：2 × L × s × h × d_h × bytes
  L=层数, s=序列长, h=KV 头数, d_h=每头维度

Prefill：算 prompt（compute-bound，决定 TTFT）
Decode：逐 token 生成（memory-bound，决定 TPOT）

Decode 是 memory-bound 的根源：算术强度低，HBM 带宽是瓶颈。

优化五大方向：
  架构层（MQA/GQA/MLA）+ 量化 + 淘汰 + 内存管理 + 跨请求复用
```

---

## 🎯 高频追问

1. **KV Cache 能否完全去掉**？理论上可以重算（recompute），但每步都重算太慢。可部分重算（如 attention sink 保留首部，远处淘汰后需要时重算）。

2. **GQA 怎么影响 KV Cache 公式**？公式中 $h$（头数）换成 $g$（组数），KV Cache 缩小 $h/g$ 倍。

3. **MLA 的 KV Cache 怎么算**？$L \cdot s \cdot d_c$（$d_c$ 是潜空间维度），比 GQA 还小。

4. **Encoder-Decoder 的 KV Cache 怎么处理**？Decoder self-attention 有 KV Cache；Cross-Attention 的 K/V 来自 encoder（一次性算，整段缓存）。

5. **为什么不能直接用更大显存解决**？HBM 容量增长慢于模型规模，优化必不可少。
