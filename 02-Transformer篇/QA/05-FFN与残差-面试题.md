# FFN 与残差 · 面试题

> 对应原理文档：[05-FFN与残差.md](../05-FFN与残差.md)
> 标注说明：难度 ⭐(简单)→⭐⭐⭐⭐(难)；高频 🔥(偶尔)→🔥🔥🔥(必问)

---

## Q1: Transformer 里 FFN 的角色是什么？为什么不能去掉？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

**FFN**（Feed-Forward Network）的两个角色：
1. **提供非线性**：Attention 本身是线性的（softmax 加权 + 线性投影），没有 FFN 的 GELU/SwiGLU 激活，Transformer 会退化为线性模型
2. **每个位置独立做特征变换**：token 间不通信（position-wise）

**和 Attention 的分工**：

```
Attention: token 之间通信（横向，混合信息）
FFN:       token 自己变换（纵向，提取特征）
```

**追问：softmax 不是非线性吗？** softmax 是非线性，但它作用在"权重"上，不直接作用在特征向量上。所以仍需 FFN 给特征本身引入非线性。

---

## Q2: 写出朴素 FFN 公式，为什么中间维度是 $4d$？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

$$\text{FFN}(x) = W_2 \cdot \text{GELU}(W_1 x + b_1) + b_2$$

**符号**：$x \in \mathbb{R}^d$，$W_1 \in \mathbb{R}^{d_{ff} \times d}$，$W_2 \in \mathbb{R}^{d \times d_{ff}}$，典型 $d_{ff} = 4d$。

**三步**：
1. $W_1 x$：$d$ 维扩展到 $d_{ff}$ 维（4×）
2. GELU 激活（或 ReLU/Swish）
3. $W_2$：投影回 $d$ 维

**为什么是 $4d$**：
- 原始 Transformer（"Attention is All You Need"）：$d=512, d_{ff}=2048=4d$
- 经验值，没有严格理论
- 直觉：扩展到高维提供"工作空间"，类似 SVM 高维映射或非线性表征
- 现代 LLM 沿袭这个比例

**追问：SwiGLU 为什么变成 $\frac{8}{3}d$？** SwiGLU 用 3 个矩阵（多一个 gate 投影）。为了对齐原始 FFN 总参数量 $8d^2$，把中间维度从 $4d$ 缩到 $\frac{8}{3}d$ → $3 \cdot d \cdot \frac{8}{3}d = 8d^2$。

---

## Q3: Attention 和 FFN 的参数量比例是多少？为什么 MoE 优先稀疏化 FFN？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

**每个 Block**：

| 模块 | 参数量 |
|---|---|
| Attention（$W^Q, W^K, W^V, W^O$，各 $d \times d$） | $4d^2$ |
| FFN（原始 $W_1, W_2$；或 SwiGLU 3 矩阵） | $\approx 8d^2$ |

**比例**：FFN ≈ Attention 的 **2 倍**，占 Block 参数约 2/3。
**全模型**：FFN 约占总参数的 **65%**。

**MoE 优先替换 FFN 的原因**：
1. FFN 是参数主体 → 把 FFN 替换为"多个专家 + 路由"能最大化稀疏化收益
2. FFN 是 position-wise 的，每个 token 独立 → 路由设计天然，专家间无 token 通信耦合
3. Attention 的 KV Cache 仍是稠密的，不适合稀疏化

代表：Mixtral 8x7B、DeepSeek-MoE、Qwen-MoE 都把每层 FFN 改成多专家 MoE。

---

## Q4: FFN 是 token-wise 还是 sequence-wise？为什么？
> 难度 ⭐⭐ ｜ 高频 🔥

**Token-wise**（也叫 position-wise）。

每个位置独立计算：

$$y_i = W_2 \cdot \text{GELU}(W_1 x_i + b_1) + b_2, \quad \forall i \in [1, n]$$

不同位置之间的 FFN 计算**完全独立**，参数共享。

**为什么这样设计**：
- token 间通信完全交给 Attention 一项任务
- FFN 专注做"每个 token 自己的特征变换"，分工清晰
- 实现上可以 reshape 成 $(B \cdot n, d)$ 一次矩阵乘搞定，并行度极高

**对比**：CNN 是局部 sequence-wise（卷积核覆盖局部邻域），RNN 是 sequence-wise 但串行。

---

## Q5: FFN 的 key-value 记忆视角是什么？为什么模型越大记得越多？
> 难度 ⭐⭐⭐ ｜ 高频 🔥

**论文**（Geva et al. 2021，"Transformer FFN Layers Are Key-Value Memories"）发现：

$$\text{FFN}(x) = W_2 \cdot \text{activation}(W_1 x)$$

可以重新解读：
- $W_1$ 的每一行 → "**key**"（描述什么模式触发激活）
- $W_2$ 的每一列 → "**value**"（激活后输出什么内容）
- $\text{activation}(W_1 x)$ → 软门控（哪些 key 被当前 $x$ 匹配上）

**含义**：FFN 像一个软联想记忆，存储了大量"模式 → 输出"的映射。模型把事实知识、常识等存在 FFN 权重里。

**为什么模型越大记得越多**：$d_{ff} = 4d$ 越大，能存的 key-value pair 越多。这也部分解释 scaling law——参数量上去后，模型容量（"记忆库容量"）随之增加。

**应用**：ROME、MEMIT 等知识编辑方法直接定位并修改 FFN 中存储某个事实的权重行。

---

## Q6: 残差连接的公式是什么？为什么没有它深层 Transformer 训不动？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

$$y = x + F(x)$$

**符号**：$x$ 是子层输入，$F(x)$ 是子层（Attention 或 FFN）输出。

**梯度高速通路**：

$$\frac{\partial y}{\partial x} = I + \frac{\partial F}{\partial x}$$

恒有 $I$ 这一项 → 梯度可直接反传，**不会指数衰减**。

**没有残差的后果**：深层网络反向传播是连乘 $\prod_l \frac{\partial x_{l+1}}{\partial x_l}$，每项 < 1 → 梯度消失 → 深层（> 20 层）几乎训不动。

**直觉**：
- 如果 $F$ 学不出有用东西，至少 $x$ 直接通过（信息不丢）
- 每层在前一层基础上做"小修正"，而不是完全替换

**追问：现代 Transformer 残差具体加在哪？** Pre-Norm 形式：
$$h' = h + \text{Attention}(\text{RMSNorm}(h))$$
$$h'' = h' + \text{FFN}(\text{RMSNorm}(h'))$$
每个子层（Attention、FFN）外都包一层残差，**LN 在残差里面**——这就是 Pre-Norm。

---

## Q7: Pre-Norm 和 Post-Norm 有什么区别？为什么现代 LLM 都用 Pre-Norm？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

| | Pre-Norm | Post-Norm |
|---|---|---|
| 公式 | $h' = h + F(\text{LN}(h))$ | $h' = \text{LN}(h + F(h))$ |
| LN 位置 | 子层**前** | 子层**后** |
| 残差路径 | LN 不切断残差（梯度直通） | LN 在残差外（梯度被 LN 缩放） |
| 训练稳定性 | **稳定**（深层也好训） | 不稳定（深层需精细 warmup） |
| 代表 | LLaMA、GPT、Qwen | 原始 Transformer、BERT |

**Pre-Norm 的核心优势**：残差路径 $x \to x'$ 之间没有 LN——梯度可以无损直通到底层，**Warmup 要求大幅降低**，可以训到 100+ 层。

**Post-Norm 的代价**：LN 把残差路径切断了，深层梯度会被反复缩放，训练不稳。原始 Transformer 必须配大 warmup 才能勉强收敛。

**追问：Pre-Norm 有什么缺点？** 顶层表征量级会越来越大（每层都加一份残差但 LN 没归一化它），最终需要在最后加一个 final LN 修正——这正是 LLaMA 在 lm_head 前加 final RMSNorm 的原因。

---

## Q8: FFN 时代为什么不用 Dropout 了？
> 难度 ⭐⭐ ｜ 高频 🔥

**原始 Transformer / BERT**：FFN 中间层、attention 输出后都加 dropout（典型 0.1）。

**现代 LLM 预训练**：
- LLaMA、Qwen、DeepSeek 预训练阶段 **dropout = 0**
- 原因：数据量极大（TB 级 token），不存在过拟合问题，dropout 反而拖慢收敛

**什么时候还用**：
- SFT / 微调阶段：数据量小，可加 0.05~0.1 防过拟合
- 小模型（< 1B）：数据相对充足度不够时也会用
- LoRA 适配器内部：常用 0.05~0.1

**核心原则**：Dropout 是数据稀缺时代的正则化工具；数据极度充足时它的边际收益为负。

---

## 🎯 自测清单

- [ ] 能说清 FFN 的两个角色（非线性 + position-wise 变换）
- [ ] 能算 Attention $4d^2$、FFN $8d^2$，FFN ≈ Attention 的 2 倍
- [ ] 能讲清为什么 MoE 优先稀疏化 FFN（参数主体 + position-wise）
- [ ] 能讲 FFN 的 key-value memory 视角
- [ ] 能白板写残差梯度 $\partial y / \partial x = I + \partial F/\partial x$
- [ ] 能区分 Pre-Norm vs Post-Norm + 解释残差路径是否被 LN 切断
