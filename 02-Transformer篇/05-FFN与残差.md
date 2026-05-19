# FFN 与残差

> FFN 是参数主体，残差是训练稳定性的关键。

---

## Q1: FFN（Feed-Forward Network）的作用是什么？

**答**：
**结构**（原始 Transformer）：
$$\text{FFN}(x) = W_2 \cdot \text{ReLU}(W_1 x + b_1) + b_2$$

- $W_1: d \to 4d$（扩展）
- $W_2: 4d \to d$（投影回）
- 每个位置独立计算（position-wise），所以叫 "Position-wise FFN"。

**作用**：
1. **非线性变换**：attention 是线性组合（softmax 加权求和 + 线性投影），FFN 提供必要的非线性。
2. **key-value 存储**：论文 "Transformer Feed-Forward Layers Are Key-Value Memories"（Geva et al., 2021）认为 FFN 中 $W_1$ 是 keys，$W_2$ 是 values，存储了大量事实知识。
3. **特征变换**：把 attention 混合后的表示映射到更适合下游的语义空间。

**没有 FFN 会怎样**：模型退化为纯线性（即使有 softmax 也表达力弱），效果暴跌。

---

## Q2: 为什么 FFN 中间维度通常是 4×hidden？

**答**：
- **原始 Transformer**：$d=512, d_{ff}=2048 = 4d$。
- **GPT/BERT 沿袭**：4 倍是经验值，没有严格理论。
- **直觉**：扩展到更大维度提供"工作空间"，类似 SVM 中的高维映射。
- **参数权衡**：FFN 参数 $2 \cdot 4d \cdot d = 8d^2$，attention 参数 $4d^2$。FFN 约占 2/3 参数。

**SwiGLU 下变成 8/3**：
- SwiGLU 有 3 个权重矩阵，参数量为 $3 \cdot h \cdot d$。
- 为对齐原始 $8d^2$ 参数量，取 $h = 8d/3$（实际取 64 倍数对齐 GPU）。

---

## Q3: 为什么需要残差连接？

**答**：
**核心动机**：解决深层网络的训练困难（梯度消失、表示退化）。

**形式**：
$$y = x + F(x)$$

**好处**：
1. **梯度高速通路**：反向传播时 $\partial L / \partial x = (1 + \partial F / \partial x) \cdot \partial L / \partial y$，恒有 $1$ 这一项，避免梯度消失。
2. **恒等映射兜底**：如果 $F$ 学不出有用的东西，至少不会让信号丢失。
3. **训练更深的网络**：ResNet 让 100+ 层成为可能，Transformer 100+ 层也依赖残差。
4. **可视化为"细化"**：每层在前一层基础上做一个小修正。

**Transformer 中的具体位置**：
- 每个 Sublayer（Attention、FFN）后都有残差：$x = x + \text{Sublayer}(x)$
- 与 LayerNorm 组合：Pre-Norm 或 Post-Norm

---

## Q4: 如果去掉残差或 LayerNorm 会怎样？

**答**：
**去掉残差**：
- 深层网络几乎训不动
- 即使训得动，效果暴跌（梯度消失）
- 极少数情况下可以用极仔细的初始化弥补（如 Fixup），但实践不可行

**去掉 LayerNorm**：
- 训练数值不稳定，loss 容易爆掉
- 深层后激活值分布漂移严重

**去掉残差 + LayerNorm**：
- 训练直接发散

**结论**：残差 + LayerNorm 是深层 Transformer 的两个基石。

---

## Q5: FFN 中的 dropout 怎么用？

**答**：
**原始 Transformer**：在 FFN 的两层之间、attention 输出后都加 dropout。
**LLM 时代**：
- 预训练大模型几乎不用 dropout（数据量大不需要正则）
- SFT / 小模型可加少量 dropout（如 0.1）
- LLaMA、Qwen 预训练阶段 dropout = 0

---

## Q6: FFN 占多少参数？

**答**：
**每个 Block 的参数量**：
- Attention（QKV + O）：$4d^2$
- FFN（原始）：$2 \cdot 4d \cdot d = 8d^2$
- FFN（SwiGLU）：$3 \cdot (8d/3) \cdot d = 8d^2$

**比例**：FFN ≈ Attention 的 2 倍，约占 Block 参数的 2/3。

**全模型**：Embedding + Block + LM Head 中，Block 主导，FFN 是主导中的主导（约 65%）。

---

## Q7: 为什么 FFN 不共享，每层都独立？

**答**：
- 早期工作（Universal Transformer）尝试过层间共享 FFN，效果略差但参数省。
- LLM 走 scaling 路线，参数越多越好，所以**不共享**。
- 共享方案在边缘场景（手机端）仍有研究价值。

---

## Q8: Pre-Norm 还是 Post-Norm 中残差怎么走？

**答**：

**Post-Norm**（原版）：
```
y = LayerNorm(x + Sublayer(x))
```
残差 → 加法 → LayerNorm，**LayerNorm 在残差之外**

**Pre-Norm**（现代）：
```
y = x + Sublayer(LayerNorm(x))
```
LayerNorm → 子层 → 加残差，**LayerNorm 在子层之内**，残差通路上没有 LN

**关键差异**：Pre-Norm 中残差路径**始终是恒等映射**，梯度可直接反传到最浅层，深层训练稳定性显著好于 Post-Norm。

---

## 🎯 高频追问

1. **FFN 能否被替换成其他模块**？可以，MoE 就是把 FFN 替换为多个专家 + 路由；也有用 Mamba 替换的研究。
2. **FFN 是 token-wise 还是 sequence-wise**？token-wise（position-wise），每个位置独立。这意味着 FFN 不做位置间通信，通信完全靠 Attention。
3. **为什么 FFN 用 2 层不用更多**？2 层足够提供非线性变换；更多层会增加参数与梯度路径，得不偿失。
4. **GLU 系列（SwiGLU、GeGLU）为什么更好**？引入门控机制，类似 LSTM 的 gate，控制信息流；实验证明系统性优于普通 FFN。
5. **FFN 中间维度选大点会怎样**？参数翻倍，效果略升但 ROI 低；现代模型在 4d 与 8d 之间已收敛于约 2.7d（SwiGLU 8/3）。
