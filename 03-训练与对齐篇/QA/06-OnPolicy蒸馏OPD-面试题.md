# On-Policy Distillation（OPD）· 面试题

> 对应原理文档：[06-OnPolicy蒸馏OPD.md](../06-OnPolicy蒸馏OPD.md)
> 标注说明：难度 ⭐(简单)→⭐⭐⭐⭐(难)；高频 🔥(偶尔)→🔥🔥🔥(必问)

---

## Q1: OPD（On-Policy Distillation，在策略蒸馏）一句话定位
> 难度 ⭐⭐ ｜ 高频 🔥🔥

```text
SFT  = off-policy + 密集（每 token 都学）
RL   = on-policy  + 稀疏（episode 级 1 个奖励信号）
OPD  = on-policy  + 密集（每 token 都有教师打分）
```

OPD 拿走了 RL 的 on-policy 采样、丢掉了它的稀疏奖励，换上 SFT 风格的 per-token 监督——综合二者优势。

**类比**：
- SFT 像看教师录像学
- RL 像考试（走完只告诉对/错）
- **OPD 像家教全程陪练**（你自己写、老师每步告诉"这步偏了多少"）

**追问：OPD 谁提的？** Thinking Machines Lab 2025 年提出，[博客原文](https://thinkingmachines.ai/blog/on-policy-distillation/)。

---

## Q2: 为什么 SFT 不够？什么是 Compounding Error？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥🔥

**Compounding Error（误差累积）**：

SFT 让学生学的是"**教师走过的状态**"（teacher distribution），但推理时学生进入"**自己生成的状态**"（student distribution）。

```text
学生一旦犯了教师从不犯的早期错误
→ 进入教师没见过的状态
→ 学生不知道怎么纠正
→ 错误连锁放大、越走越偏。
```

**Thinking Machines 原话**：

> "the student can learn to imitate the teacher's style and confidence but not necessarily its factual accuracy."

**这就是 SFT 模型"风格像、事实错"的根因**。OPD 直接在学生 rollout 上训练，学生学到的是"如何从自己可能进入的状态恢复"，从源头避开 compounding error。

---

## Q3: 为什么 RL 太贵？信号密度怎么对比？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

**信息论视角**：
- **RL**：一个 episode 只有最后一个标量 reward → $O(1)$ 比特 / episode
- **OPD**：每个 token 都有教师打分 → $O(N)$ 比特 / episode

**符号**：$N$ 是 rollout 的 token 数，长 CoT 可达 $N=5000$，**密度差几千倍**。

```text
RL  告诉你"答案错了"     —— 不知道是哪步错的
OPD 告诉你"第 137 个 token 应该说 'wait' 而不是 'therefore'"
```

**结果**：OPD 用 RL 的 **~10% 算力**就能达到同等甚至更好效果。

---

## Q4: OPD 的核心公式？为什么是 reverse KL（反向 KL）？
> 难度 ⭐⭐⭐⭐ ｜ 高频 🔥🔥🔥

**Per-token reverse KL 损失**：

$$\mathcal{L}_{\text{OPD}}(\theta) = \mathbb{E}_{x \sim \pi_\theta}\Big[\sum_{t=1}^{N} \big(\log \pi_\theta(x_t \mid x_{<t}) - \log \pi_{\text{teacher}}(x_t \mid x_{<t})\big)\Big]$$

**符号**：
- $\pi_\theta$：学生（被训）
- $\pi_{\text{teacher}}$：教师（冻结）
- $x \sim \pi_\theta$：**从学生采样**（on-policy 关键）

**为什么是反向 KL（mode-seeking）**：

| | 等价 KL 形式 | 行为 |
|---|---|---|
| SFT（off-policy） | $D_{KL}(\pi_{\text{teacher}} \| \pi_\theta)$ — 前向 KL | **mode-covering**（要覆盖教师所有模式） |
| **OPD（on-policy）** | $D_{KL}(\pi_\theta \| \pi_{\text{teacher}})$ — **反向 KL** | **mode-seeking**（聚焦教师高概率模式） |

反向 KL 是"学生的概率不要放到教师认为不可能的地方" → 学生收敛到教师的**高概率**模式，不会被低概率噪声带偏。

**Thinking Machines 原话**："the reverse KL is 'unhackable'"——**教师就是奖励信号本身，没法被 hack**。

---

## Q5: OPD 实现里"一行改动"是什么意思？伪代码？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

Thinking Machines 强调：OPD 就是 RL 框架 + 一行改动——**把 KL 约束的参考模型换成"教师模型"，并把它当主要损失**。

```python
for step in range(num_steps):
    # 1. 学生 rollout（同 RL）
    trajectories = student.sample(prompts)
    student_logprobs = student.compute_logprobs(trajectories)

    # 2. 教师打分（1 次 forward，不反传）
    teacher_logprobs = teacher.compute_logprobs(trajectories)

    # 3. 把 "教师 logprob - 学生 logprob" 当 per-token advantage
    advantages = -(student_logprobs - teacher_logprobs)

    # 4. 直接喂 PPO/GRPO 的 policy gradient
    loss = ppo_loss(student, trajectories, advantages)
    loss.backward()
    optimizer.step()
```

**关键工程点**：
- 教师**只前向、不反传** → 显存比 RL 还省（不需要 critic / RM）
- 折扣因子 $\gamma = 0$：只看当前 token 的 KL，不做时间折扣
- 用 GRPO/PPO 框架几乎零改动

---

## Q6: OPD 在 AIME'24 上的实验效果？算力优势多大？
> 难度 ⭐⭐ ｜ 高频 🔥

**Thinking Machines 实验**：8B 学生 + 32B（Qwen3）教师，AIME'24 数学测评：

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

**~10× GPU 时间换更好的效果**——这是 OPD 最直观的卖点。

---

## Q7: OPD 怎么解决"灾难性遗忘"（Continual Learning）？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

**典型问题**：在内部文档上做 mid-train 后，模型**忘记指令遵循能力**（IF-eval 从 85% 掉到 79%）。

**OPD 解法**：用**模型的早期版本**（继续训练前）当教师，做 OPD 恢复。

| 阶段 | 内部 QA | IF-eval |
|---|---|---|
| Qwen3-8B（原始） | 18% | 85% |
| + mid-train | 36% | **79%（掉了）** |
| + mid-train + OPD | **41%** | **83%（基本恢复）** |

**意义**：
- 新能力（内部 QA）+ 老能力（IF-eval）**可以同时保住**
- 教师不一定要比学生强，"自己的早期版本"也行
- 对抗灾难性遗忘的实用工具

---

## Q8: OPD 和 SFT、RL、DPO、PPO、GRPO 的全景对比？
> 难度 ⭐⭐⭐ ｜ 高频 🔥🔥

| 方法 | 数据来源 | 信号 | 是否要 RM | 适用 |
|---|---|---|---|---|
| **SFT** | 教师固定输出 | 硬 token | 否 | 起步、风格、格式 |
| **KD（off-policy 蒸馏）** | 教师固定输出 + soft label | 软 token（前向 KL） | 否 | 压缩、能力迁移 |
| **DPO** | 静态偏好对 | 对级偏好 | 否 | 对齐 |
| **PPO（RLHF）** | 学生 rollout | episode reward + KL 罚 | **是** | 复杂对齐 |
| **GRPO** | 学生 rollout | 组归一化 advantage | 是（RM 或规则） | 推理 RL |
| **OPD** | 学生 rollout | **per-token reverse KL** | 否（教师即 RM） | **能力蒸馏 + 防遗忘** |

```text
OPD 独到之处：
  on-policy（避 compounding error） + 密集（每 token 信号） + 不需要 RM
```

---

## Q9: OPD 适合什么场景？什么时候用不了？
> 难度 ⭐⭐ ｜ 高频 🔥

**适合**：
- 有一个**比学生强**的教师（更大模型、推理模型、专家模型）
- 想要 RL 级效果但算力有限
- 微调后要"找回"原有能力（continual learning）
- 不想训 reward model

**不适合**：
- 没有更强的教师（要训 frontier 模型时）
- 教师比学生还弱
- 需要从**环境**（执行结果、用户反馈）拿**新知识**，而非 transfer——这种场景必须 RL

**对比 R1-Distill**：R1-Distill 是用 R1 生成数据再 SFT（off-policy）。OPD 是学生自己 rollout、教师按 token 打分（on-policy + dense）。OPD 期望效果更好但工程略复杂。

---

## 🎯 自测清单

- [ ] 能用一句话定位 OPD = on-policy + 密集 per-token reverse KL
- [ ] 能讲清 SFT 的 compounding error 为什么是核心痛点
- [ ] 能默写 OPD 的 per-token reverse KL 公式
- [ ] 能说清为什么用反向 KL（mode-seeking + unhackable）
- [ ] 能讲 OPD 防"灾难性遗忘"的做法（用早期版本当教师）
- [ ] 能说出 OPD vs RL 的 ~10× 算力优势
