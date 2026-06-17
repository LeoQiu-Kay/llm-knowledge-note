# 手撕 MHA（Multi-Head Attention）

> 最高频的手撕题。能在白板上 5 分钟写出带 mask 的多头注意力是基本功。

---

## 1. 题目要求

实现 Multi-Head Attention：
- 支持 batch
- 支持 causal mask（decoder 用）
- 支持任意头数

---

## 2. 数学公式

**单头 Scaled Dot-Product Attention**：

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{Q K^T}{\sqrt{d_k}}\right) V$$

**多头**：把 $d$ 维拆成 $h$ 个 $d_k = d/h$ 维子空间，每头独立算，拼接后过输出投影：

$$\text{MultiHead}(Q,K,V) = \text{Concat}(\text{head}_1, \dots, \text{head}_h) W^O$$

---

## 3. 完整实现

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
import math


class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, n_heads, dropout=0.0):
        super().__init__()
        assert d_model % n_heads == 0
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads          # 每头维度

        # 一次性投影出 Q/K/V（合并成一个大矩阵更高效）
        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        self.W_o = nn.Linear(d_model, d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, mask=None):
        # x: [B, L, D]
        B, L, D = x.shape

        # 1. 投影 + 拆头：[B, L, D] -> [B, H, L, d_k]
        Q = self.W_q(x).view(B, L, self.n_heads, self.d_k).transpose(1, 2)
        K = self.W_k(x).view(B, L, self.n_heads, self.d_k).transpose(1, 2)
        V = self.W_v(x).view(B, L, self.n_heads, self.d_k).transpose(1, 2)

        # 2. 算注意力分数：[B, H, L, L]
        scores = Q @ K.transpose(-2, -1) / math.sqrt(self.d_k)

        # 3. 加 mask（causal 或 padding）
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float('-inf'))

        # 4. softmax + dropout
        attn = F.softmax(scores, dim=-1)       # [B, H, L, L]
        attn = self.dropout(attn)

        # 5. 加权求和：[B, H, L, d_k]
        out = attn @ V

        # 6. 合头 + 输出投影：[B, H, L, d_k] -> [B, L, D]
        out = out.transpose(1, 2).contiguous().view(B, L, D)
        return self.W_o(out)


def causal_mask(L):
    """下三角 mask，[1, 1, L, L]，1 可见，0 屏蔽"""
    return torch.tril(torch.ones(L, L)).view(1, 1, L, L)
```

---

## 4. 测试验证

```python
torch.manual_seed(0)
B, L, D, H = 2, 5, 64, 8
mha = MultiHeadAttention(D, H)
x = torch.randn(B, L, D)

# 无 mask
out = mha(x)
assert out.shape == (B, L, D), out.shape

# causal mask
mask = causal_mask(L)
out_causal = mha(x, mask)
assert out_causal.shape == (B, L, D)

# 验证 causal：第 0 个 token 的输出只依赖自己
# （改动 x 的后面 token，第 0 个输出不变）
x2 = x.clone()
x2[:, 1:] = torch.randn(B, L - 1, D)
out1 = mha(x, mask)
out2 = mha(x2, mask)
print("causal 检验（应接近 0）:", (out1[:, 0] - out2[:, 0]).abs().max().item())
print("✓ 通过")
```

---

## 5. 面试常见追问

**Q: 为什么除以 $\sqrt{d_k}$？**
A: 保持点积方差稳定。$q \cdot k$ 是 $d_k$ 项独立和，方差为 $d_k$；不除会让 softmax 输入跨度大、接近 one-hot、梯度消失。

**Q: `transpose(1,2)` 之后为什么要 `.contiguous()`？**
A: transpose 只改 stride 不改内存布局，`.view()` 要求内存连续，所以先 `.contiguous()`。

**Q: mask 为什么填 `-inf` 而不是 0？**
A: 要在 softmax **之前** 填 `-inf`，softmax 后变成 0；填 0 的话 softmax 后还有 $e^0=1$ 的权重。

**Q: 怎么改成 GQA？**
A: K/V 的头数改成 $g < h$，然后 K/V 用 `repeat_interleave(h//g, dim=1)` 扩展到 $h$ 个头再算。

**Q: Q/K/V 三个 Linear 能合并吗？**
A: 能。用一个 `nn.Linear(d, 3*d)` 然后 split，减少 kernel 启动开销（实际工程常这么做）。

> 📚 原理详解：[02-Transformer篇/02-注意力机制.md](../02-Transformer篇/02-注意力机制.md)
