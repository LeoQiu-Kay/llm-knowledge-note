# On-Policy Distillation（OPD）

> Thinking Machines Lab 2025 年提出。
> 把 SFT 的"密集监督"和 RL 的"on-policy 采样"合到一起：
> **学生自己生成轨迹 → 教师给每个 token 打 KL 分 → 用 RL 的 policy gradient 更新**。

> 参考资料：
> - [Thinking Machines Lab - On-Policy Distillation](https://thinkingmachines.ai/blog/on-policy-distillation/)
> - [SFT, RL, and OPD Through a Distributional Lens](https://nrehiew.github.io/blog/sft_rl_opd/)
> - [Tinker cookbook 实现](https://github.com/thinking-machines-lab/tinker-cookbook)
> - [A Survey of On-Policy Distillation for LLMs](https://arxiv.org/pdf/2604.00626)

---

## 1. 一句话定位

```text
SFT     = off-policy + 密集（每 token 都学）
RL      = on-policy  + 稀疏（episode 级 1 个奖励信号）
OPD     = on-policy  + 密集（每 token 都有教师打分）
```

OPD 拿走了 RL 的 on-policy 采样、丢掉了它的稀疏奖励，换上了 SFT 风格的 per-token 监督。

---

## 2. 三种方法的核心对比

| 维度 | SFT | RL（PPO/GRPO） | OPD |
|---|---|---|---|
| 训练数据从哪来 | 教师 / 人写的固定轨迹 | 学生自己 rollout | **学生自己 rollout** |
| 监督信号 | 每 token 的 NLL（硬标签） | episode 级 reward + KL 罚 | **每 token 的 reverse KL** |
| 信号密度 | $O(N)$ | $O(1)$ per episode | $O(N)$ |
| 是否需要 RM | 否 | 是（或规则奖励） | **否，教师就是 RM** |
| 是否需要 critic | 否 | PPO 需要、GRPO 不需要 | 否 |
| 误差累积 | **有**（学生进入教师没去过的区） | 无 | 无 |
| 探索成本 | 低 | **高**（信号稀疏，需大量样本） | 低 |
| 典型成本 | 中 | 高 | RL 的 ~10% |

```text
SFT 像看录像学：教师怎么走、就让你按教师轨迹学每一步。
RL 像考试：自己走、走完只告诉你"对/错"，要靠自己复盘。
OPD 像家教全程陪练：你自己写、老师在每一步告诉你"这步偏了多少"。
```

---

## 3. 为什么 SFT 不够？— Compounding Error

**Compounding error（误差累积）**：

SFT 让学生学的是"教师走过的状态"（teacher distribution），但**推理时学生进入的是自己生成的状态**（student distribution）。

```text
教师从不犯的早期错误，学生一旦犯了 → 进入教师从没见过的状态
→ 学生不知道怎么纠正 → 越走越偏。
```

这就是 SFT 模型经常表现出来的"风格像、事实错"。Thinking Machines 原文：

> "the student can learn to imitate the teacher's style and confidence but not necessarily its factual accuracy."

OPD 直接在学生的 rollout 上训练，所以学生学到的是"如何从自己可能进入的状态恢复"。

---

## 4. 为什么 RL 太贵？— 信号密度

**信息论视角**：
- **RL**：一个 episode 只有最后一个标量奖励 → 每 episode 提供 $O(1)$ 比特
- **OPD**：每个 token 都有教师打分 → 每 episode 提供 $O(N)$ 比特（$N$ = token 数）

**符号说明**：
- $N$：一条 rollout 的 token 数
- 一个长 CoT 可能 $N = 5000$，差距是几千倍

```text
RL 告诉你"答案错了"，但不知道是哪步错。
OPD 告诉你"第 137 个 token 那里你应该说 'wait' 而不是 'therefore'"。
```

这就是为什么 OPD 用 RL 的 ~10% 算力就能达到同等效果。

---

## 5. OPD 的核心公式

**Per-token reverse KL**：

$$\mathcal{L}_{\text{OPD}}(\theta) = \mathbb{E}_{x \sim \pi_\theta}\left[\sum_{t=1}^{N} \big(\log \pi_\theta(x_t \mid x_{<t}) - \log \pi_{\text{teacher}}(x_t \mid x_{<t})\big)\right]$$

**符号说明**：
- $\pi_\theta$：学生模型（被训练的 policy）
- $\pi_{\text{teacher}}$：教师模型（冻结）
- $x_t$：第 $t$ 个 token
- $x \sim \pi_\theta$：**从学生模型采样**（on-policy 的关键）
- $\log \pi_\theta(x_t \mid x_{<t})$：学生给这个 token 打的 log 概率
- $\log \pi_{\text{teacher}}(x_t \mid x_{<t})$：教师给同一 token 打的 log 概率
- 求和括号内：每个 token 的 reverse KL 贡献

**为什么是 reverse KL？**（对比 SFT 的前向 KL）

| | 等价的 KL 形式 |
|---|---|
| SFT（off-policy） | $D_{KL}(\pi_{\text{teacher}} \| \pi_\theta)$ —— 前向 KL，mode-covering |
| **OPD（on-policy）** | $D_{KL}(\pi_\theta \| \pi_{\text{teacher}})$ —— **反向 KL，mode-seeking** |

反向 KL 是"学生的概率不要放到教师认为不可能的地方" → 学生**收敛到教师的高概率模式**，不会被教师的低概率噪声带偏。原文："the reverse KL is 'unhackable'"——教师就是奖励信号本身，没法被 hack。

---

## 6. 实现：在 RL 框架上"一行改动"

Thinking Machines 强调：OPD 就是 RL + KL 正则，**把"KL 约束的参考模型"换成"教师模型"**。

**伪代码**：
```python
for step in range(num_steps):
    # 1. 学生 rollout（和 RL 一样）
    trajectories = student.sample(prompts)
    student_logprobs = student.compute_logprobs(trajectories)

    # 2. 教师打分（仅需 1 次 forward）
    teacher_logprobs = teacher.compute_logprobs(trajectories)

    # 3. 把负的 reverse KL 当作 per-token advantage
    advantages = -(student_logprobs - teacher_logprobs)

    # 4. 用 PPO/GRPO 的 policy gradient 更新
    loss = ppo_loss(student, trajectories, advantages)
    loss.backward()
    optimizer.step()
```

**关键点**：
- **教师只前向、不反传** → 显存比 RL 还省（不需要 critic / RM）
- 折扣因子 $\gamma = 0$：只看当前 token 的 KL，不做时间折扣
- 把"教师 logprob - 学生 logprob"当 advantage，直接喂 PPO 框架

---

## 7. 实验结果（数学推理 AIME'24）

从 SFT-400K 初始化的 8B 学生 → 教师是 32B（Qwen3）：

| 方法 | AIME'24 | 相对计算效率 |
|---|---|---|
| SFT-2M | ~70% | 1× |
| RL | 68% | ≈1× |
| **OPD** | **70%** | **9-30×** |

**Qwen3 官方对比**：

| 方法 | AIME'24 | GPU Hours |
|---|---|---|
| + RL | 67.6% | 17,920 |
| + OPD | **74.4%** | **1,800** |

**~10× GPU 时间换更好的效果**。

---

## 8. 另一个杀手锏：Continual Learning

**问题**：在内部文档上做 mid-train 后，模型会**忘记**指令遵循能力（IF-eval 从 85% → 79%）。

**OPD 解法**：用模型的早期版本（继续训练前）当教师，做 OPD 恢复。

| 阶段 | 内部 QA | IF-eval |
|---|---|---|
| Qwen3-8B | 18% | 85% |
| + mid-train | 36% | **79%（掉了）** |
| + mid-train + OPD | **41%** | **83%（基本恢复）** |

```text
对抗"灾难性遗忘"的实用工具：
  新能力（内部 QA）+ 老能力（IF-eval）可以同时保住。
```

---

## 9. 与现有方法的全景对比

| 方法 | 数据来源 | 信号 | 是否要 RM | 适用 |
|---|---|---|---|---|
| **SFT** | 教师固定输出 | 硬 token | 否 | 起步、风格、格式 |
| **KD（off-policy）** | 教师固定输出 + soft labels | 软 token（前向 KL） | 否 | 压缩、能力转移 |
| **DPO** | 静态偏好对 | 对级偏好 | 否 | 对齐 |
| **PPO（RLHF）** | 学生 rollout | episode reward + KL 罚 | **是**（RM） | 复杂对齐 |
| **GRPO** | 学生 rollout | 组归一化 advantage | 是（RM 或规则） | 推理 RL |
| **OPD** | 学生 rollout | **per-token reverse KL** | 否（教师就是 RM） | **能力蒸馏 + 防遗忘** |

---

## 10. 何时用 OPD？

**适合**：
- 有一个**比学生强**的教师（更大模型、推理模型、专家模型）
- 想要 RL 级效果但算力有限
- 微调后要"找回"原有能力（continual learning）
- 不想训练 reward model

**不适合**：
- 没有更强的教师（如要训练 frontier 模型）
- 教师比学生还弱
- 需要从环境（执行结果、用户反馈）拿新知识，而不是 transfer

---

## 11. 最简记忆

```text
SFT  = 看教师录像          → off-policy + 每 token 硬标签
RL   = 自己走，最后打分    → on-policy  + episode-level reward
OPD  = 自己走，教师每步打分 → on-policy  + 每 token reverse KL

公式：advantage_t = -(log π_θ(x_t) - log π_teacher(x_t))
       直接喂进 PPO/GRPO loss

收益：
  ~10× RL 的算力 → 同等或更好效果
  自然防"灾难性遗忘"
  教师 = RM，不可 hack
```

---

## 🎯 高频追问

1. **OPD 和 RLHF 中"KL 约束 ref 模型"什么关系**？OPD 把"KL 约束项"提升为**主要损失**，并且 ref 换成"更强的教师"。RLHF 里 KL 是辅助项（防偏离 SFT），OPD 里 KL 就是全部信号。

2. **为什么不直接 SFT 教师的输出就好**？compounding error：SFT 在教师分布上训，推理时学生进入自己的分布，遇到没见过的状态就跑偏。OPD 在学生分布上训，从源头避开这个问题。

3. **教师必须比学生大吗**？通常是。OPD 的本质是"学生收敛到教师"，所以教师必须更强。Continual learning 场景是例外：教师可以是"自己的早期版本"，目的是保留行为。

4. **为什么用反向 KL 而不是前向 KL**？前向 KL 是 mode-covering（学生要覆盖教师所有模式），容易把教师的低概率噪声也学进来；反向 KL 是 mode-seeking（学生聚焦教师高概率区），更稳定，且天然不可 hack。

5. **和 R1-Distill 有什么区别**？R1-Distill 是用 R1 生成数据再 SFT（off-policy）。OPD 是学生自己 rollout、教师按 token 打分（on-policy + dense）。OPD 期望效果更好但实现略复杂。

6. **能和 GRPO 组合吗**？可以，且 thinking machines 的实现就是基于 GRPO 框架，只把 advantage 从"组归一化奖励"换成"负 reverse KL"。

---

## 来源

- [Thinking Machines Lab - On-Policy Distillation 原博客](https://thinkingmachines.ai/blog/on-policy-distillation/)
- [SFT, RL, and On-Policy Distillation Through a Distributional Lens](https://nrehiew.github.io/blog/sft_rl_opd/)
- [Tinker cookbook（参考实现）](https://github.com/thinking-machines-lab/tinker-cookbook)
- [A Survey of On-Policy Distillation for LLMs](https://arxiv.org/pdf/2604.00626)
- [Decoupling KL and Trajectories: Unified Perspective for SFT/DAgger/Offline-RL/OPD](https://arxiv.org/html/2605.16826)
- [Awesome-LLM-On-Policy-Distillation 资源合集](https://github.com/nick7nlp/Awesome-LLM-On-Policy-Distillation)
