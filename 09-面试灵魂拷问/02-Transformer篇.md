# 灵魂拷问 · Transformer 篇

> 7 道题，覆盖 Transformer 的"骨架问题"：
> 为什么用 Transformer / 为什么 Decoder-only / Attention 设计 / 位置编码 / 注意力演进 / 归一化 / 激活。

---

## Q1: 为什么 Transformer 比 RNN/LSTM 更适合 LLM？

### 1.0 先做背景铺垫

**RNN（Recurrent Neural Network）/ LSTM**：循环式处理序列——读完第 1 个 token 才能读第 2 个，靠"隐藏状态" $h_t$ 把过去信息传给未来。

**Transformer**：用 **Attention**（注意力机制）让任意两个 token 直接通信，整序列并行处理。

### 1.1 4 大优势

1. **长程依赖**：Attention 直接 $O(1)$ 跨距访问任意位置；RNN 信号沿时间衰减，记不住远处
2. **并行训练**：Transformer 一次处理所有位置；RNN 必须串行 → GPU 利用率低
3. **Scaling 友好**：弱归纳偏置 + 大数据，符合 scaling laws
4. **梯度路径短**：残差 + 直接 attention，避免梯度消失/爆炸

### 1.2 反例

**Mamba 等 SSM**（State Space Models）试图重回线性复杂度，长上下文可能反超 Transformer，但目前 LLM 主流仍是 Transformer。

> 📚 延伸：[02-Transformer篇/01-整体架构.md](../02-Transformer篇/01-整体架构.md)

---

## Q2: 为什么现在 LLM 都用 Decoder-only？

### 2.0 先做背景铺垫：3 种 Transformer 结构

| 结构 | 代表 | 特点 |
|---|---|---|
| **Encoder-only** | BERT | 双向 attention，做理解任务（分类、抽取） |
| **Decoder-only** | GPT、LLaMA | 单向 attention（causal mask），做生成任务 |
| **Encoder-Decoder** | T5、原始 Transformer | Encoder 双向 + Decoder 单向 + Cross-Attention |

### 2.1 5 大原因

1. **Zero-shot 能力强**：GPT-3 后系统验证，Decoder-only + scaling 吊打 Encoder-Decoder（如 T5）
2. **训练目标统一**：CLM（Causal LM）一个目标覆盖理解 + 生成，**数据利用率 100%**（vs MLM 只 15%）
3. **架构简单**：无 Cross-Attention，部署 / 并行 / 缓存都简洁
4. **In-Context Learning 天然**：causal mask + 任意长 prompt 完美适配
5. **Scaling 路径成熟**：从 GPT-2 到 GPT-4 一脉相承，资本和工程都偏好

### 2.2 简单答

"训练目标更好（每个 token 都在学习），scaling 路径已被验证，且架构简单适合 in-context learning。"

> 📚 延伸：[02-Transformer篇/01-整体架构.md](../02-Transformer篇/01-整体架构.md)

---

## Q3: Attention 为什么要 scale $\sqrt{d_k}$？

### 3.0 先做背景铺垫：Attention 公式

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{Q K^T}{\sqrt{d_k}}\right) V$$

**符号说明**：
- $Q, K, V$：query / key / value 矩阵
- $d_k$：每头的维度（典型 64 或 128）

问题：为什么要除 $\sqrt{d_k}$？

### 3.1 动机

**保持点积输出方差稳定**。

### 3.2 数学推导

假设 $q, k$ 各分量独立同分布、均值 0、方差 1：

$$q \cdot k = \sum_{i=1}^{d_k} q_i k_i$$

$$\mathbb{E}[q \cdot k] = 0, \quad \text{Var}[q \cdot k] = d_k$$

所以**标准差 $= \sqrt{d_k}$**。

### 3.3 不除会怎样？

$d_k = 64$ 时方差为 64，标准差约 8。Softmax 输入跨度 $\sim \pm 16$：
- Softmax 输出**接近 one-hot**（最大值 ≈ 1，其他 ≈ 0）
- 梯度对 argmax 之外几乎为 0 → 训练困难

除 $\sqrt{d_k}$ 后方差归一到 1，softmax 输入分布稳定。

> 📚 延伸：[02-Transformer篇/02-注意力机制.md](../02-Transformer篇/02-注意力机制.md)

---

## Q4: 主流位置编码方案 + RoPE 原理、优势与局限

### 4.0 先做背景铺垫：为什么需要位置编码？

Attention 是**置换不变**的——把输入 $[x_1, x_2, x_3]$ 打乱成 $[x_3, x_1, x_2]$，attention 内积不变，对每个 token 的输出只是相应换位。

→ 模型看不到顺序，"狗咬人"和"人咬狗"无差别 → 必须**显式注入位置信号**。

### 4.1 主流方案对照

| 方案 | 形式 | 类别 | 代表模型 | 优点 | 缺点 |
|---|---|---|---|---|---|
| **Sinusoidal**（原版） | 加到 input embedding | 绝对 | 原始 Transformer | 简单、固定不学 | 外推差、信号集中底层 |
| **Learned PE** | 可学习向量加到 embedding | 绝对 | BERT、GPT-1/2 | 灵活 | 完全不能外推 |
| **ALiBi** | 加偏置 $-m\|i-j\|$ 到 attention scores | 相对 | BLOOM、MPT | 天然外推 | 关注长距离能力弱 |
| **T5 bias** | 桶化相对距离查表加偏置 | 相对 | T5 | 可学相对距离 | 桶离散，外推有限 |
| **RoPE** | 旋转 Q/K | 相对 | LLaMA / Qwen / DeepSeek | 实现简单、效果好 | 直接外推差，需 YaRN 修正 |

### 4.2 RoPE 详解（必背）

**核心思想**：在每对维度上把 Q、K 旋转一个**与位置成正比**的角度。

二维子空间（$d_h$ 拆 $d_h/2$ 对）：

$$R_m = \begin{pmatrix} \cos m\theta & -\sin m\theta \\ \sin m\theta & \cos m\theta \end{pmatrix}, \quad \theta_i = 10000^{-2i/d_h}$$

**符号**：$m$ 是 token 位置，$\theta_i$ 是第 $i$ 对维度的基础旋转角；低维高频（短距离精细）、高维低频（长距离平滑）。

### 4.3 为什么是"相对"位置编码（关键证明）

利用 $R_m^T = R_{-m}$，$R_\alpha R_\beta = R_{\alpha+\beta}$：

$$\langle R_m q, R_n k \rangle = q^T R_m^T R_n k = q^T R_{n-m} k$$

**Attention 分数只依赖相对位置 $n - m$**——这就是 RoPE 是相对编码的本质。

### 4.4 RoPE 的 5 大优势

1. **相对位置内嵌**：分数自然只看距离
2. **不增加参数**：纯函数式旋转
3. **每层都注入**：信号不会被深层稀释
4. **数学优雅**：与 attention 内积天然兼容
5. **可外推（结合 YaRN）**：旋转操作连续可微

### 4.5 RoPE 的 4 大局限

1. **直接外推效果差**：训练 4K 推 128K → 远距离旋转角度落在训练分布之外
2. **需 YaRN/NTK/PI 修正**：长上下文必须配合频率缩放
3. **与 MLA 不兼容**：低秩压缩破坏旋转结构 → DeepSeek 用"解耦 RoPE"
4. **2D 子空间约束**：head_dim 必须是偶数

> 📚 延伸：[02-Transformer篇/04-位置编码.md](../02-Transformer篇/04-位置编码.md)

---

## Q5: MHA / MQA / GQA / MLA 对比 + 云上推理选型逻辑

### 5.0 先做背景铺垫：4 个缩写到底是什么

| 缩写 | 全称 | 一句话 |
|---|---|---|
| **MHA** | Multi-Head Attention | 标准多头注意力，每个头有独立 Q/K/V |
| **MQA** | Multi-Query Attention | 多 Q 头，但所有头**共享同一个 K/V**（极端） |
| **GQA** | Grouped-Query Attention | 多 Q 头，K/V 分 $g$ 组，组内共享（折中） |
| **MLA** | Multi-head Latent Attention | DeepSeek 自研，把 K/V **压到低秩潜空间** $c^{KV}$，需要时再上投影 |

**演化逻辑**：所有变体的目的都是**减小 KV Cache**（推理时的显存大头）。

### 5.1 结构差异

| 维度 | MHA | MQA | GQA | MLA |
|---|---|---|---|---|
| Q 头数 | $h$ | $h$ | $h$ | $h$ |
| K/V 头数 | $h$ | **1** | **$g$**（1 < g < h） | 共享 1 个低秩潜空间 $d_c$ |
| KV Cache 公式（单 token 单层） | $2 h d_h$ | $2 d_h$ | $2 g d_h$ | $d_c + d_h^R$ |
| 还原方式 | 直接用 | 共享 | 分组共享 | 上投影 $W^{UK}, W^{UV}$ |

### 5.2 显存开销（LLaMA-3-70B 配置，FP16，128K 序列）

| 方案 | 假设参数 | KV Cache |
|---|---|---|
| MHA（假想 $h=64$） | 64 头 × 128 维 | ~340 GB |
| **GQA** | $g=8$，64 头 → 8 组 | **~42 GB**（缩 8×） |
| **MLA** | $d_c=512, d_h^R=64$ | **~10 GB**（缩 34×） |

### 5.3 推理速度（Decode 阶段）

Decode 是 **memory-bound**：

```
速度 ∝ 1 / KV Cache 大小
```

→ KV Cache 越小，每张卡能服务的并发越高、TPOT 越短。

| 方案 | 相对吞吐（单卡） |
|---|---|
| MHA | 1× |
| GQA | ~3-5× |
| MLA | ~5-10× |

### 5.4 适用场景

| 场景 | 推荐 | 理由 |
|---|---|---|
| 边缘 / 小模型推理（< 7B） | MHA 也行 | 模型本身小，KV Cache 不是瓶颈 |
| **主流开源 LLM 训练** | **GQA** | 效果几乎无损 + 显存 / 吞吐改善显著 |
| **极致云端推理** | **MLA** | KV Cache 最小，单卡服务最多用户 |
| 极致 KV 压缩 | MLA + INT8 量化 | DeepSeek-V3 部署方案 |
| 多模态长上下文 | GQA / MLA + YaRN | 长 KV + 长 context 双重压力 |

### 5.5 云上选型逻辑

云上服务核心是**最大化并发 × 吞吐 / GPU 成本**：

1. **算 KV Cache 上限**：根据期望 context 长度 + 并发数 → 算每张卡能放多少 KV
2. **倒推架构选型**：
   - MHA → 单卡 ~50 个 4K 用户
   - GQA → 单卡 ~400 个 4K 用户
   - MLA → 单卡 ~1500+ 个 4K 用户
3. **结合量化叠加**：INT8 KV Cache 再缩 50%
4. **结合调度**：Continuous Batching + PagedAttention 提升利用率

```text
铁律：
  小模型 + 不在意成本 → GQA
  大模型 + 高并发     → GQA / MLA（看是否自研）
  极致长上下文        → MLA + 量化 + Prefix Caching
```

**特例**：$g = 1$ → MQA；$g = h$ → MHA。所以"GQA 调参可退化到任意一端"。

> 📚 延伸：[02-Transformer篇/03-注意力机制演进.md](../02-Transformer篇/03-注意力机制演进.md)

---

## Q6: RMSNorm 相比 LayerNorm 为什么更受欢迎？

### 6.0 先做背景铺垫

**LayerNorm**（层归一化）：

$$y = \gamma \cdot \frac{x - \mu}{\sqrt{\sigma^2 + \epsilon}} + \beta$$

做了两件事：**减均值**（re-centering）+ **除标准差**（re-scaling）。

**RMSNorm**（均方根归一化）：

$$y = \gamma \cdot \frac{x}{\sqrt{\frac{1}{D}\sum x_i^2 + \epsilon}}$$

只做了 **re-scaling**（除均方根），没有 re-centering。

### 6.1 RMSNorm 省了什么？

1. **均值计算 $\mu$**（不再算）
2. **减均值操作**
3. **bias 参数 $\beta$**（通常省）

**计算节省**：约 7-15%。

### 6.2 效果如何？

**等效或略好**——研究发现 LN 主要靠 re-scaling 起作用，re-centering 影响很小。

### 6.3 现状

**LLaMA / Qwen / Mistral / DeepSeek 全用 RMSNorm**，已成事实标准。

> 📚 延伸：[01-基础篇/04-归一化方法.md](../01-基础篇/04-归一化方法.md)

---

## Q7: SwiGLU 为什么打败 ReLU / GELU？

### 7.0 先做背景铺垫：演化路线

**ReLU**（2010s）：$\max(0, x)$，简单粗暴。
**GELU**（BERT、GPT-2）：$x \cdot \Phi(x)$，平滑版 ReLU。
**Swish/SiLU**：$x \cdot \sigma(x)$，与 GELU 近亲。
**SwiGLU**（LLaMA 起）：在 Swish 基础上引入**门控机制**。

### 7.1 SwiGLU 形式

$$\text{SwiGLU}(x) = \text{Swish}(W_1 x) \otimes (W_3 x)$$

**符号**：$\otimes$ 是逐元素乘。

完整 FFN：

$$\text{FFN}(x) = W_2 \cdot \big[\text{Swish}(W_1 x) \otimes (W_3 x)\big]$$

### 7.2 为什么打败 GELU？

1. **门控机制**：$W_3 x$ 提供**软门控**，类似 LSTM 的 gate，让模型学到"对哪些维度更敏感"
2. **平滑可导**：处处连续
3. **表达力强**：3 个矩阵 vs 2 个，但参数对齐到原 FFN 同一总量

### 7.3 参数量对齐

为保持 FFN 总参数量不变（$8 d^2$），SwiGLU 中间维度从 $4d$ 改为 $\frac{8}{3}d$：

| FFN 形式 | 矩阵数 | 中间维度 | 总参数 |
|---|---|---|---|
| 朴素 | 2（$W_1, W_2$） | $4d$ | $8 d^2$ |
| SwiGLU | 3（$W_1, W_3, W_2$） | $\frac{8}{3} d$ | $8 d^2$ |

### 7.4 现状

**LLaMA / Qwen / Mistral / DeepSeek 全用 SwiGLU**。

> 📚 延伸：[01-基础篇/05-激活函数.md](../01-基础篇/05-激活函数.md)
