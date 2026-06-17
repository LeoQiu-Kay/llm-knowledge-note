# 手撕 GRPO

> DeepSeek 的明星算法。重点：**组内归一化算 advantage** + **clip loss** + **k3 KL**。

---

## 1. 题目要求

实现 GRPO 的核心：
- 组内归一化算 advantage
- PPO 风格 clip 损失
- KL 正则项

---

## 2. 数学公式

**组内归一化 advantage**（同一 prompt 采 $G$ 个答案）：

$$A_i = \frac{r_i - \text{mean}(\{r_1, \dots, r_G\})}{\text{std}(\{r_1, \dots, r_G\})}$$

**GRPO 目标**（整个答案的所有 token 共享 $A_i$）：

$$\mathcal{L} = -\frac{1}{G}\sum_i \frac{1}{|y_i|}\sum_t \min\big(\rho_{i,t} A_i,\ \text{clip}(\rho_{i,t}, 1-\epsilon, 1+\epsilon) A_i\big) + \beta\, D_{KL}$$

其中 $\rho_{i,t} = \dfrac{\pi_\theta(y_{i,t})}{\pi_{\theta_\text{old}}(y_{i,t})}$。

---

## 3. 完整实现

```python
import torch
import torch.nn.functional as F


def grpo_advantages(rewards):
    """
    组内归一化算 advantage。
    rewards: [G]  同一 prompt 的 G 个答案的奖励
    返回 [G]，每个答案一个标量 advantage
    """
    mean = rewards.mean()
    std = rewards.std() + 1e-8         # 防除零
    return (rewards - mean) / std


def grpo_loss(logp_new, logp_old, logp_ref, advantages, response_mask,
              clip_eps=0.2, kl_coef=0.04):
    """
    logp_new:  [G, T] 当前策略对每个 token 的 log-prob
    logp_old:  [G, T] 采样时旧策略的 log-prob
    logp_ref:  [G, T] 参考模型的 log-prob
    advantages: [G]   每个答案的组内归一化 advantage
    response_mask: [G, T] 1=回答 token, 0=padding/prompt
    """
    # 1. 重要性采样比 ρ = exp(logp_new - logp_old)
    ratio = torch.exp(logp_new - logp_old)        # [G, T]

    # 2. advantage 广播到每个 token（整个答案共享）
    adv = advantages.unsqueeze(1)                  # [G, 1] -> 广播 [G, T]

    # 3. PPO clip
    unclipped = ratio * adv
    clipped = torch.clamp(ratio, 1 - clip_eps, 1 + clip_eps) * adv
    policy_loss = -torch.min(unclipped, clipped)   # [G, T]

    # 4. KL 正则（k3 估计器，恒非负）
    r = logp_ref - logp_new
    kl = torch.exp(r) - 1 - r                       # [G, T]

    # 5. 合并 + 按 mask 求平均（只在回答 token 上）
    per_token_loss = policy_loss + kl_coef * kl
    loss = (per_token_loss * response_mask).sum() / response_mask.sum()
    return loss


# ===== 完整训练步骤示意 =====
def grpo_step(prompt, policy, ref_model, reward_fn, G=8):
    """伪代码：演示一次 GRPO 更新的流程"""
    # 1. 同一 prompt 采样 G 个答案
    responses = [policy.generate(prompt) for _ in range(G)]

    # 2. 每个答案打分（规则奖励或 RM）
    rewards = torch.tensor([reward_fn(prompt, r) for r in responses])  # [G]

    # 3. 组内归一化算 advantage
    advantages = grpo_advantages(rewards)                              # [G]

    # 4. 算 log-prob（old 在采样时已存，new 是当前 policy）
    logp_old = torch.stack([policy.log_prob(prompt, r) for r in responses])
    logp_ref = torch.stack([ref_model.log_prob(prompt, r) for r in responses])
    # ... 多轮 inner epoch 中 logp_new 会变 ...
    logp_new = torch.stack([policy.log_prob(prompt, r) for r in responses])

    mask = torch.ones_like(logp_new)  # 简化：全部是回答 token
    loss = grpo_loss(logp_new, logp_old, logp_ref, advantages, mask)
    return loss
```

---

## 4. 测试验证

```python
torch.manual_seed(0)
G, T = 8, 10

# 模拟：8 个答案，reward 是 4 对 4 错
rewards = torch.tensor([1., 1., 0., 1., 0., 0., 1., 0.])
adv = grpo_advantages(rewards)
print("rewards:   ", rewards.tolist())
print("advantages:", adv.round(decimals=3).tolist())
print("→ 答对(1)的 advantage>0 被鼓励，答错(0)的<0 被抑制")

# 验证：均值约 0，标准差约 1
print("adv mean:", adv.mean().item(), " std:", adv.std().item())

# loss 计算 sanity check
logp_new = torch.randn(G, T) * 0.1
logp_old = logp_new.clone()           # 初始 ratio=1
logp_ref = logp_new.clone()           # 初始 KL=0
mask = torch.ones(G, T)
loss = grpo_loss(logp_new, logp_old, logp_ref, adv, mask)
print("初始 loss（ratio=1, KL=0）:", loss.item())
print("✓ 通过")
```

---

## 5. 面试常见追问

**Q: GRPO 比 PPO 省了什么？**
A: 省掉 **critic 模型**。PPO 要 4 个模型（actor/critic/RM/ref），GRPO 只要 3 个（actor/RM/ref）。

**Q: 没有 critic 怎么算 advantage？**
A: 用**组内归一化**——同一 prompt 采 $G$ 个答案，用组内均值当 baseline，$(r_i - \text{mean})/\text{std}$。

**Q: GRPO 的 advantage 粒度和 PPO 有什么区别？**
A: GRPO 是 **per-episode**（一个答案一个标量，所有 token 共享）；PPO 是 **per-token**（GAE 算每步）。

**Q: 组内全对或全错怎么办？**
A: std → 0，advantage 失效（除零）。代码里加 `eps`；实际中这种 prompt 对训练无贡献，可过滤。

**Q: KL 为什么直接作 loss 而不是塞进 reward？**
A: GRPO 把 KL 作为独立 loss 项（用 k3 估计器），比 PPO 塞进 reward 的方式更直接、更稳定。

**Q: $G$ 怎么选？**
A: 典型 8-16，DeepSeek-R1 用 64。太小组内统计噪声大，太大算力开销 $G$ 倍。

> 📚 原理详解：[03-训练与对齐篇/03-对齐与强化学习.md](../03-训练与对齐篇/03-对齐与强化学习.md)
