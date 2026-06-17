# 手撕 AdamW

> 优化器手撕题。重点：一阶/二阶动量 + 偏差修正 + **解耦权重衰减**（这是 AdamW 区别于 Adam 的关键）。

---

## 1. 题目要求

实现 AdamW 优化器：
- 一阶动量 $m$、二阶动量 $v$
- 偏差修正
- **解耦的权重衰减**（与梯度路径分离）

---

## 2. 数学公式

**Adam 主体**（$g_t$ 是梯度）：

$$m_t = \beta_1 m_{t-1} + (1 - \beta_1) g_t$$
$$v_t = \beta_2 v_{t-1} + (1 - \beta_2) g_t^2$$
$$\hat m_t = \frac{m_t}{1 - \beta_1^t}, \quad \hat v_t = \frac{v_t}{1 - \beta_2^t}$$

**AdamW 的更新**（权重衰减解耦，不进梯度）：

$$\theta_t = \theta_{t-1} - \eta\left(\frac{\hat m_t}{\sqrt{\hat v_t} + \epsilon} + \lambda \theta_{t-1}\right)$$

**对比原始 Adam**（L2 正则塞进梯度）：

$$g_t \leftarrow g_t + \lambda \theta_{t-1} \quad \text{(错误做法，被} \sqrt{v} \text{扭曲)}$$

---

## 3. 完整实现

```python
import torch


class AdamW:
    def __init__(self, params, lr=1e-3, betas=(0.9, 0.999),
                 eps=1e-8, weight_decay=0.01):
        self.params = list(params)
        self.lr = lr
        self.beta1, self.beta2 = betas
        self.eps = eps
        self.weight_decay = weight_decay
        self.t = 0
        # 为每个参数维护 m, v
        self.m = [torch.zeros_like(p) for p in self.params]
        self.v = [torch.zeros_like(p) for p in self.params]

    @torch.no_grad()
    def step(self):
        self.t += 1
        for i, p in enumerate(self.params):
            if p.grad is None:
                continue
            g = p.grad

            # 1. 更新一阶/二阶动量
            self.m[i].mul_(self.beta1).add_(g, alpha=1 - self.beta1)
            self.v[i].mul_(self.beta2).addcmul_(g, g, value=1 - self.beta2)

            # 2. 偏差修正
            m_hat = self.m[i] / (1 - self.beta1 ** self.t)
            v_hat = self.v[i] / (1 - self.beta2 ** self.t)

            # 3. AdamW 更新：先解耦权重衰减，再加 Adam 步
            #    关键：weight_decay 直接作用在参数上，不进梯度！
            if self.weight_decay != 0:
                p.mul_(1 - self.lr * self.weight_decay)   # θ ← (1-ηλ)θ

            # 4. Adam 主更新
            p.addcdiv_(m_hat, v_hat.sqrt().add_(self.eps), value=-self.lr)

    def zero_grad(self):
        for p in self.params:
            if p.grad is not None:
                p.grad = None
```

---

## 4. 测试验证

```python
import torch.nn as nn

torch.manual_seed(0)

# 用一个简单回归任务对拍 PyTorch 官方 AdamW
def train_with(optimizer_cls, **kwargs):
    torch.manual_seed(0)
    model = nn.Linear(5, 1)
    X = torch.randn(100, 5)
    y = X @ torch.randn(5, 1) + 0.1 * torch.randn(100, 1)

    if optimizer_cls == 'mine':
        opt = AdamW(model.parameters(), lr=0.01, weight_decay=0.01)
    else:
        opt = torch.optim.AdamW(model.parameters(), lr=0.01, weight_decay=0.01)

    for _ in range(200):
        opt.zero_grad()
        loss = ((model(X) - y) ** 2).mean()
        loss.backward()
        opt.step()
    return loss.item(), [p.detach().clone() for p in model.parameters()]

loss_mine, params_mine = train_with('mine')
loss_torch, params_torch = train_with('torch')

print("我的 AdamW 最终 loss:    ", round(loss_mine, 6))
print("PyTorch AdamW 最终 loss: ", round(loss_torch, 6))

# 参数应高度接近
max_diff = max((pm - pt).abs().max().item()
               for pm, pt in zip(params_mine, params_torch))
print("参数最大差异:", max_diff)
assert max_diff < 1e-4, "应与官方实现一致"
print("✓ 通过：与 torch.optim.AdamW 数值一致")
```

---

## 5. 面试常见追问

**Q: AdamW 和 Adam 的唯一区别是什么？**
A: **权重衰减的位置**。Adam 把 L2 正则塞进梯度（$g \leftarrow g + \lambda\theta$），会被自适应分母 $\sqrt{v}$ 扭曲；AdamW 把权重衰减**解耦**，直接作用在参数上（$\theta \leftarrow (1-\eta\lambda)\theta$），不受 $\sqrt{v}$ 影响。

**Q: 偏差修正为什么需要？**
A: $m, v$ 初始化为 0，训练初期偏向 0（被低估）。除以 $1-\beta^t$ 修正：$t$ 小时分母小、放大修正，$t$ 大时分母趋 1、几乎不修正。

**Q: $m$ 和 $v$ 分别是什么直觉？**
A: $m$ 是梯度的滑动平均（"动量/速度"，让一致方向加速）；$v$ 是梯度平方的滑动平均（"梯度的方差"，作分母实现每参数自适应学习率）。

**Q: $\beta_2$ 为什么 LLM 常调到 0.95？**
A: 默认 0.999 记忆窗口太长（~1000 步），长尾极大梯度会让 $v$ 失真。调到 0.95 缩短窗口，让 $v$ 反应更快，训练更稳。

**Q: Adam 的显存开销？**
A: 每个参数要额外存 $m, v$ + FP32 主权重 = 12 字节/参数（FP32），约 4 倍参数显存。7B 模型优化器状态约 84 GB——这是 ZeRO 要切分的大头。

**Q: `addcdiv_` 和 `addcmul_` 是什么？**
A: 原地融合操作。`addcmul_(a,b,value=v)` 算 `self += v*a*b`；`addcdiv_(a,b,value=v)` 算 `self += v*a/b`。比分步写更快、省显存。

> 📚 原理详解：[01-基础篇/03-优化与训练.md](../01-基础篇/03-优化与训练.md)
