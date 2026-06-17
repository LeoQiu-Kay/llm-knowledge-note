# 手撕 GAE（Generalized Advantage Estimation）

> PPO 的核心组件。重点是**反向递推**的简洁实现。

---

## 1. 题目要求

给定每步 reward、每步 value 估计，算出每步的 advantage 和 returns。

---

## 2. 数学公式

**TD 误差**：

$$\delta_t = r_t + \gamma V(s_{t+1}) - V(s_t)$$

**GAE advantage**（多步 TD 的指数加权）：

$$A_t = \sum_{l=0}^{T-t} (\gamma \lambda)^l \delta_{t+l}$$

**反向递推形式**（实现用这个）：

$$A_t = \delta_t + \gamma \lambda \, A_{t+1}$$

**returns**（critic 的回归目标）：

$$R_t = A_t + V(s_t)$$

**符号**：$\gamma$ 折扣因子（RLHF 常用 1.0），$\lambda$ GAE 平滑（典型 0.95）。

---

## 3. 完整实现

```python
import torch


def compute_gae(rewards, values, gamma=1.0, lam=0.95):
    """
    rewards: [T]   每步 reward
    values:  [T+1] 每步 value 估计（多一个 bootstrap value V(s_T)）
    返回 advantages [T], returns [T]
    """
    T = rewards.shape[0]
    advantages = torch.zeros(T)
    last_gae = 0.0

    # 反向递推
    for t in reversed(range(T)):
        delta = rewards[t] + gamma * values[t + 1] - values[t]
        last_gae = delta + gamma * lam * last_gae
        advantages[t] = last_gae

    returns = advantages + values[:-1]
    return advantages, returns


def compute_gae_batched(rewards, values, mask, gamma=1.0, lam=0.95):
    """
    批量版（处理变长序列）。
    rewards: [B, T], values: [B, T+1], mask: [B, T]（1 有效 0 padding）
    """
    B, T = rewards.shape
    advantages = torch.zeros(B, T)
    last_gae = torch.zeros(B)
    for t in reversed(range(T)):
        next_v = values[:, t + 1]
        delta = rewards[:, t] + gamma * next_v * mask[:, t] - values[:, t]
        last_gae = delta + gamma * lam * last_gae * mask[:, t]
        advantages[:, t] = last_gae
    returns = advantages + values[:, :-1]
    return advantages, returns
```

---

## 4. 测试验证

```python
torch.manual_seed(0)
T = 5
rewards = torch.tensor([0., 0., 0., 0., 1.])     # 只有最后一步有 reward（典型 RLHF）
values = torch.tensor([0.5, 0.5, 0.5, 0.5, 0.5, 0.0])  # T+1 个

adv, ret = compute_gae(rewards, values, gamma=1.0, lam=0.95)
print("advantages:", adv)
print("returns:   ", ret)

# 验证：returns = advantages + values[:-1]
assert torch.allclose(ret, adv + values[:-1])

# 验证反向递推 == 正向公式（小规模暴力验证）
def gae_bruteforce(rewards, values, gamma, lam):
    T = len(rewards)
    deltas = [rewards[t] + gamma * values[t+1] - values[t] for t in range(T)]
    adv = torch.zeros(T)
    for t in range(T):
        for l in range(T - t):
            adv[t] += (gamma * lam) ** l * deltas[t + l]
    return adv

adv_bf = gae_bruteforce(rewards, values, 1.0, 0.95)
print("递推 vs 暴力 误差:", (adv - adv_bf).abs().max().item())
assert torch.allclose(adv, adv_bf, atol=1e-5)
print("✓ 通过")
```

---

## 5. 面试常见追问

**Q: 为什么要 GAE，不直接用 returns - value？**
A: 直接用蒙特卡洛 returns 减 value，方差极大；用 1-step TD 偏差大。GAE 用 $\lambda$ 在两者间插值，平衡偏差和方差。

**Q: $\lambda$ 的两个极端是什么？**
A: $\lambda=0$ → 退化为 1-step TD（$A_t = \delta_t$，低方差高偏差）；$\lambda=1$ → 退化为蒙特卡洛（高方差无偏）。典型取 0.95。

**Q: 为什么 RLHF 里 $\gamma$ 常取 1.0？**
A: LLM 生成 episode 短（几百到几千 token），且最终 reward 才是关键，不需要折扣。

**Q: values 为什么是 T+1 个？**
A: 需要 $V(s_{T})$ 做 bootstrap（最后一步的"未来价值"）。如果 episode 自然结束，这个值设 0。

**Q: advantage 为什么要归一化？**
A: PPO 实战中常对 batch 内 advantage 做 `(A - mean) / std` 归一化，进一步稳定训练。

> 📚 原理详解：[03-训练与对齐篇/03-对齐与强化学习.md](../03-训练与对齐篇/03-对齐与强化学习.md)
