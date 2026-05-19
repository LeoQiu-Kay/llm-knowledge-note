# FFN 与残差

> FFN 是参数主体，残差是训练稳定性的关键。

---

## 1. FFN 在 Transformer 中干什么？

Attention 让 token 之间通信（"我看你"），但 attention 本身是**线性的**（softmax 加权 + 线性投影）。

线性变换的多层堆叠 = 单层线性。没有 FFN 提供的非线性，Transformer 表达力会退化。

**FFN 的两个角色**：
1. 提供**非线性**（GELU / SwiGLU）
2. 每个位置独立做特征变换（不在 token 间通信）

---

## 2. 朴素 FFN 公式

$$\text{FFN}(x) = W_2 \cdot \text{GELU}(W_1 x + b_1) + b_2$$

**符号说明**：
- $x \in \mathbb{R}^d$：当前 token 的特征向量（输入）
- $W_1 \in \mathbb{R}^{d_{ff} \times d}$：扩展矩阵
- $W_2 \in \mathbb{R}^{d \times d_{ff}}$：投影回原维度
- $b_1, b_2$：偏置（现代 LLM 通常省略）
- $d$：模型隐藏维度
- $d_{ff}$：FFN 中间维度（典型 $d_{ff} = 4d$）

**计算流程**：
1. $W_1 x$：把 $d$ 维扩展到 $d_{ff}$ 维（典型 4×）
2. 激活：GELU（或 ReLU、Swish）
3. $W_2$：投影回 $d$ 维

每个位置独立计算（**position-wise**）。

---

## 3. 为什么中间维度是 $4d$？

- **原始 Transformer**：$d = 512, d_{ff} = 2048 = 4d$
- **GPT/BERT 沿袭**：经验值，没有严格理论
- **直觉**：扩展到更大维度提供"工作空间"，类似 SVM 高维映射

**参数权衡**：

| | 参数量 |
|---|---|
| Attention | $4d^2$ |
| FFN | $2 \cdot 4d \cdot d = 8d^2$ |

FFN 参数约是 Attention 的 2 倍。

**SwiGLU 下变成 $\frac{8}{3}d$**：SwiGLU 用 3 个矩阵，对齐 $8d^2$ 总参数量 → $h = \frac{8}{3}d$（见激活函数篇）。

---

## 4. FFN 占多少参数？

**每个 Block**：
- Attention（QKVO 共 4 个 $d \times d$）：$4 d^2$
- FFN（无论原始还是 SwiGLU）：约 $8 d^2$

**比例**：FFN ≈ Attention 的 2 倍 → 占 Block 参数约 2/3。

**全模型**：FFN 约占总参数的 65%。这就是为什么 MoE 主要替换 FFN（更稀疏化最大块）。

---

## 5. FFN 的更深含义：key-value 存储器

论文 **"Transformer Feed-Forward Layers Are Key-Value Memories"**（Geva et al., 2021）发现：

$$\text{FFN}(x) = W_2 \cdot \text{activation}(W_1 x)$$

可以看作：
- $W_1$ 的每一行 → "**key**"（什么时候激活）
- $W_2$ 的每一列 → "**value**"（激活后输出什么）
- $\text{activation}$ → 门控

模型把大量事实知识存储在 FFN 权重中。这也部分解释为什么"模型越大记得越多"。

---

## 6. 残差连接：为什么必须有

### 6.1 形式

$$y = x + F(x)$$

**符号说明**：
- $x$：子层输入
- $F(x)$：子层（Attention 或 FFN）的输出
- $y$：加残差后的输出

### 6.2 为什么需要

**核心动机**：解决深层网络的训练困难。

**梯度高速通路**：

$$\frac{\partial y}{\partial x} = I + \frac{\partial F}{\partial x}$$

**符号**：$I$ 是单位矩阵。

恒有 $I$ 这一项 → 梯度可直接反传，不会消失。

**直觉理解**：
- 如果 $F$ 学不出有用的东西，至少 $x$ 直接通过（不丢信息）
- 每层在前一层基础上做"小修正"，而不是完全替换

```text
没有残差，深层 Transformer 几乎训不动。
```

---

## 7. Transformer 中残差的具体位置

每个 block 有 **两个残差**：

$$h' = h + \text{Attention}(\text{LayerNorm}(h))$$
$$h'' = h' + \text{FFN}(\text{LayerNorm}(h'))$$

**符号**：
- $h$：block 输入
- $h', h''$：中间和最终输出

详细的 Pre-Norm vs Post-Norm 见归一化篇。

---

## 8. 如果去掉残差或 LayerNorm 会怎样？

| 去掉什么 | 后果 |
|---|---|
| 残差 | 深层（>20）几乎训不动，梯度消失 |
| LayerNorm | 数值不稳，loss 容易爆 |
| 两个都去掉 | 直接发散 |

```text
残差 + LayerNorm 是深层 Transformer 的两个基石。
```

---

## 9. FFN 的 Dropout

**原始 Transformer**：在 FFN 中间层、attention 输出后都加 dropout。

**LLM 时代**：
- 预训练几乎不用 dropout（数据量大，不需要正则）
- SFT / 小模型可加少量 dropout（如 0.1）
- LLaMA、Qwen 预训练阶段 dropout = 0

---

## 10. 最简记忆

```text
FFN：每个位置独立的非线性变换
  原始：W2 · GELU(W1 · x)，中间维度 4d
  SwiGLU：W2 · [Swish(W1·x) ⊗ (W3·x)]，中间维度 8/3·d

FFN 是参数主体（约 65%）。

残差：y = x + F(x)
  梯度直通 → 深层可训
  缺一不可 + LayerNorm
```

---

## 🎯 高频追问

1. **FFN 能被替换吗**？MoE 就是把 FFN 替换为"多个专家 + 路由"；也有用 Mamba 替换的研究。

2. **FFN 是 token-wise 还是 sequence-wise**？token-wise（position-wise）。每个位置独立。token 间通信完全靠 Attention。

3. **为什么 FFN 只有 2 层不是更多**？2 层足够提供非线性变换；多了增加参数和梯度路径，ROI 低。

4. **GLU 系列为什么打败普通 FFN**？引入门控，类似 LSTM 的 gate，让模型学到"对哪些维度更敏感"。

5. **中间维度选大点会怎样**？参数翻倍，效果略升但 ROI 低。SwiGLU 的 $\frac{8}{3}d$ 是甜点。
