# 监督微调 SFT 与 PEFT · 面试题

> 对应原理文档：[02-监督微调SFT.md](../02-监督微调SFT.md)
> 标注说明：难度 ⭐(简单)→⭐⭐⭐⭐(难)；高频 🔥(偶尔)→🔥🔥🔥(必问)

---

## Q1: SFT（Supervised Fine-Tuning，监督微调）和预训练 CLM 的 loss 有什么区别？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

**预训练 CLM**：对**所有 token** 算 loss。

**SFT**：只对 **assistant 部分** token 算 loss，user/system 部分 mask 掉。

$$\mathcal{L}_{\text{SFT}} = -\sum_{t \in A} \log P(x_t \mid x_{<t}; \theta)$$

其中 $A$ 是 assistant 回答的 token 位置集合。

**为什么 mask 掉 user/system**：
- 用户输入是"给定的输入"，让模型学"生成用户问题"毫无意义
- 会污染对话格式学习

**工程实现**：构造 `loss_mask`，user/system 部分填 0、assistant 部分填 1，相乘即可。

**追问：assistant 的 special token（如 `<|im_start|>assistant\n`）算 loss 吗？** 习惯做法是把 role marker 也算入 loss，让模型学会主动生成 assistant 标记。

---

## Q2: 全参 SFT vs LoRA vs QLoRA 的显存对比和适用场景？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

**7B 模型 BF16 + Adam 显存对比**：

| 方法 | 显存 | 硬件门槛 |
|---|---|---|
| 全参 SFT | ~140 GB | A100 80G × 2+ 或 H100 |
| LoRA SFT | ~20 GB | 单 RTX 4090 (24G) 可跑 |
| QLoRA SFT | ~6 GB | 单 RTX 4090 充裕，甚至 3090 |

**显存来源**（全参）：参数 14GB + 梯度 14GB + Adam $m,v$ 28GB + FP32 主权重 28GB + 激活 ≈ 总 ~140GB。

**适用**：
- **小数据少 epoch**：LoRA 足够，性价比高
- **大数据多任务**：全参；或多个 LoRA adapter 共享 base
- **超大模型（>30B）+ 单卡**：必须 QLoRA

---

## Q3: LoRA（Low-Rank Adaptation）原理，写出公式
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

**核心假设**：微调带来的参数更新 $\Delta W$ 是**低秩**的，可分解为两个低秩矩阵乘积：

$$W' = W + \Delta W = W + BA$$

**前向**：

$$y = Wx + \frac{\alpha}{r} BAx$$

**符号**：
- $W \in \mathbb{R}^{d \times d}$：冻结的预训练权重
- $A \in \mathbb{R}^{r \times d}$：下投影，**高斯初始化**
- $B \in \mathbb{R}^{d \times r}$：上投影，**零初始化**
- $r$：LoRA 秩（典型 4-64）
- $\alpha$：缩放系数（典型 $\alpha = 2r$）

**关键设计**：
- $B$ 初始化为 0 → 训练起始时 $BA = 0$，不破坏 base 模型
- 渐进式学习增量更新

**参数量缩减**：$d=4096, r=16$ → 原 $d^2 = 16.7M$ vs LoRA $2dr = 131K$，**~128× 缩减**。

---

## Q4: LoRA 为什么要 A 高斯初始化、B 零初始化？反过来行吗？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

**目的**：训练开始时 $BA = 0$，模型输出 = 预训练原输出，不会引入随机扰动破坏 base。

**为什么不能两个都零**：
- 都零 → 梯度对称问题：$\frac{\partial L}{\partial A} \propto B^T$、$\frac{\partial L}{\partial B} \propto A$
- 若 $A=B=0$ → 两个梯度都恒为 0 → 永远学不出

**为什么不是 A 零、B 高斯**：
- 理论上对称可行
- 但梯度量级会不同，PyTorch 实现里默认是"$A$ 随机，$B$ 零"，沿用即可

**追问：$\alpha / r$ 起什么作用？** 真正的 LoRA 强度由 $\alpha/r$ 决定。固定 $\alpha=2r$ 等价于"调 $r$ 时不用重调 LR"，让超参解耦。调大 $\alpha$ ≈ 调大 LoRA 学习率。

---

## Q5: LoRA 加在哪些层效果最好？秩 $r$ 怎么选？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

**加在哪**：
- 论文初版：仅 Attention 的 $W^Q, W^V$
- 经验：**QKVO + FFN（gate/up/down）全加效果最好**
- 极致：所有 linear 层
- HF peft 库默认就是 QKVO + FFN

**$r$ 选择**：
- 简单任务（指令格式）：$r = 4 \sim 8$
- 复杂任务（领域知识）：$r = 16 \sim 64$
- 经验甜点：$r = 8$，再往上**边际递减**

**学习率**：LoRA 的 LR 通常比全参微调**大几倍**（如 $1e^{-4} \sim 5e^{-4}$），因为参数少、可激进。

---

## Q6: QLoRA 的三个关键创新是什么？怎么做到单卡微调 65B？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

**核心**：把 base 模型量化到 4-bit（冻结），LoRA 部分保持 BF16（可训练）。

**三大创新**：

1. **NF4（Normal Float 4-bit）**：针对正态分布权重最优的 4-bit 数据类型；普通 INT4 假设均匀分布，NF4 在每个 4-bit bucket 上让正态分布等概率，量化误差更小
2. **Double Quantization**：把量化常数（每 64 个权重一个 scale）**也量化** → 再省 ~0.4 bits/参数
3. **Paged Optimizers**：用 NVIDIA unified memory，OOM 时把 optimizer state 暂存到 CPU 内存，避免梯度爆显存

**流程**：
1. Base 模型量化到 4-bit（冻结）
2. 前向时**即时反量化**到 BF16 计算
3. LoRA 保持 BF16，梯度只流到 LoRA
4. 反向不更新 base

**效果**：65B 在单张 48GB A6000 上可微调，效果接近 16-bit LoRA。

---

## Q7: LoRA 训完怎么部署？多个 LoRA 能合并吗？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

**两种部署方式**：

| 方式 | 流程 | 适用 |
|---|---|---|
| **合并部署** | 把 $BA$ 加回 $W$，得到单个完整模型 | 单任务、最佳推理速度 |
| **分离部署** | base 模型 + 多个 adapter，运行时切换 / 加权 | 多任务、A/B 测试 |

**多 LoRA 合并**（多任务）：
- 简单加权平均：$\Delta W = \sum_i w_i B_i A_i$
- 有效果损失（任务间冲突）
- 更好方案：TIES-Merging、DARE 等（保留高幅值参数、去冲突）

**追问：LoRA 能合并到量化后的 base 吗？** 不行——量化是有损的，合并需要 BF16 base。QLoRA 部署时通常先反量化 base 再合并。

---

## Q8: SFT 容易出现哪些坑？
> 难度 ⭐⭐ ｜ 高频 🔥🔥

| 坑 | 表现 | 解法 |
|---|---|---|
| **过拟合** | 几个 epoch 后 loss 暴跌但效果下降 | 早停、低 LR、1-3 epoch |
| **灾难遗忘** | 忘记预训练知识（数学、代码能力掉） | 小 LR、混入预训练数据、用 PEFT |
| **重复输出** | 生成同一短语 | 数据质量检查、推理时 repetition penalty |
| **格式过拟合** | 只会答固定格式 | 增加格式多样性 |
| **数据偏见** | GPT-4 蒸馏数据带 OpenAI 风格 | 多源数据 |

**追问：LIMA 论文说 1000 条数据就够，为什么 LLaMA-3.1 用 10M？** LIMA 强调质量优于数量、复制 base 模型已有能力即可；工业级模型需要覆盖更多 task、format、多语种，1000 条不够覆盖长尾。

---

## Q9: SFT 之后为什么还要 RL（RLHF / DPO）？
> 难度 ⭐⭐ ｜ 高频 🔥🔥🔥

**SFT 的本质局限**：
- 只能模仿"标准答案"
- 无法表达"答案 A 比 B 好多少"
- 不能学"避免说什么"
- 偏好信息（哪种回复更受欢迎）无法注入

**RL 的价值**：
- 利用偏好数据 $(y_w, y_l)$ —— $y_w$ 比 $y_l$ 好
- 学习"避免低质 / 有害输出"
- 让答案更贴合人类喜好（helpfulness / harmlessness）

**当前最佳实践流水线**：

```text
Pretrain → SFT → DPO（或 PPO/GRPO）→ 持续迭代
```

更详见 [03-对齐与强化学习](../03-对齐与强化学习.md)。

---

## 🎯 自测清单

- [ ] 能白板写 SFT loss + 解释为何 mask user
- [ ] 能写 LoRA 公式 $W' = W + BA$ 并说清初始化
- [ ] 能算 LoRA 参数量缩减比（$d^2$ vs $2dr$）
- [ ] 能讲清 QLoRA 三大创新（NF4 / Double Quant / Paged Opt）
- [ ] 能说出 SFT 5 个常见坑及解法
