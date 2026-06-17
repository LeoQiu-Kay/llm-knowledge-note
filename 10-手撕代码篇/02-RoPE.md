# 手撕 RoPE（旋转位置编码）

> 高频题。能写出 RoPE 的 cos/sin 缓存 + apply 函数，并解释"为什么是相对位置编码"。

---

## 1. 题目要求

实现 RoPE：
- 预计算 cos/sin 表
- 把旋转应用到 Q、K
- 解释相对位置性质

---

## 2. 数学公式

把 head_dim 的相邻两维看作一个 2D 向量，按位置 $m$ 旋转角度 $m\theta_i$：

$$R_m = \begin{pmatrix} \cos m\theta_i & -\sin m\theta_i \\ \sin m\theta_i & \cos m\theta_i \end{pmatrix}, \quad \theta_i = 10000^{-2i/d}$$

**相对位置性质**（核心）：

$$\langle R_m q, R_n k \rangle = q^T R_{n-m} k$$

→ 内积只依赖相对位置 $n - m$。

---

## 3. 完整实现

```python
import torch


def precompute_rope_cache(seq_len, head_dim, base=10000.0, device='cpu'):
    """预计算 cos/sin 表，shape: [seq_len, head_dim]"""
    # 每对维度的频率：theta_i = base^(-2i/d)，i = 0..d/2-1
    inv_freq = 1.0 / (base ** (torch.arange(0, head_dim, 2, device=device).float() / head_dim))
    # 位置索引 m = 0..seq_len-1
    pos = torch.arange(seq_len, device=device).float()
    # 外积：[seq_len, d/2]，freqs[m, i] = m * theta_i
    freqs = torch.outer(pos, inv_freq)
    # 复制成 [seq_len, d]（每对维度共用一个角度）
    emb = torch.cat([freqs, freqs], dim=-1)
    return emb.cos(), emb.sin()       # 各 [seq_len, head_dim]


def rotate_half(x):
    """把后一半维度取负放到前面：[x1, x2] -> [-x2, x1]"""
    d = x.shape[-1]
    x1, x2 = x[..., :d // 2], x[..., d // 2:]
    return torch.cat([-x2, x1], dim=-1)


def apply_rope(x, cos, sin):
    """
    x:   [B, H, L, head_dim]
    cos: [L, head_dim], sin: [L, head_dim]
    """
    # 广播到 [1, 1, L, head_dim]
    cos = cos.unsqueeze(0).unsqueeze(0)
    sin = sin.unsqueeze(0).unsqueeze(0)
    return x * cos + rotate_half(x) * sin
```

**为什么 `rotate_half` 实现的是旋转？**

旋转矩阵作用于 $(x_1, x_2)$：
$$x_1' = x_1 \cos\theta - x_2 \sin\theta, \quad x_2' = x_1 \sin\theta + x_2 \cos\theta$$

代码用 "前半 / 后半" 配对（HuggingFace 风格），等价于上式的向量化：
- `x * cos` → $x_1 \cos, x_2 \cos$
- `rotate_half(x) * sin` → $-x_2 \sin, x_1 \sin$
- 相加 → $(x_1\cos - x_2\sin, \; x_2\cos + x_1\sin)$ ✓

---

## 4. 测试验证

```python
torch.manual_seed(0)
B, H, L, d = 1, 2, 6, 8
cos, sin = precompute_rope_cache(L, d)

q = torch.randn(B, H, L, d)
k = torch.randn(B, H, L, d)
q_rot = apply_rope(q, cos, sin)
k_rot = apply_rope(k, cos, sin)
assert q_rot.shape == q.shape

# 验证"相对位置"性质：
# 位置 m,n 的 q,k 内积 应等于 把它们都平移 offset 后的内积
def qk_inner(qr, kr, m, n):
    return (qr[0, 0, m] * kr[0, 0, n]).sum()

# 用同一个向量放在不同绝对位置，看内积是否只依赖相对距离
vec_q = torch.randn(d)
vec_k = torch.randn(d)
def inner_at(m, n):
    qq = vec_q.view(1, 1, 1, d).expand(1, 1, 1, d)
    kk = vec_k.view(1, 1, 1, d).expand(1, 1, 1, d)
    cosm, sinm = cos[m:m+1], sin[m:m+1]
    cosn, sinn = cos[n:n+1], sin[n:n+1]
    qr = apply_rope(qq, cosm, sinm)
    kr = apply_rope(kk, cosn, sinn)
    return (qr * kr).sum().item()

# 相对距离都是 2，绝对位置不同
print("inner(0,2):", round(inner_at(0, 2), 5))
print("inner(1,3):", round(inner_at(1, 3), 5))
print("inner(2,4):", round(inner_at(2, 4), 5))
print("→ 三者应相等（只依赖相对距离 n-m=2）")
```

---

## 5. 面试常见追问

**Q: RoPE 为什么是相对位置编码？**
A: $\langle R_m q, R_n k \rangle = q^T R_m^T R_n k = q^T R_{n-m} k$（用 $R_m^T = R_{-m}$，$R_\alpha R_\beta = R_{\alpha+\beta}$），内积只依赖 $n - m$。

**Q: RoPE 加在哪？Q/K/V 都加吗？**
A: 只加 Q 和 K（在算 attention 分数前）。V 不加——V 是"内容"，位置信息已通过 attention 权重体现。

**Q: 为什么 head_dim 必须是偶数？**
A: 要两两配对做 2D 旋转。

**Q: base（10000）的作用？怎么扩展长上下文？**
A: base 控制频率分布。扩展上下文时调大 base（如 500000）或用 NTK/YaRN 缩放频率，让低频维度衰减更慢。

**Q: RoPE 为什么直接外推效果差？**
A: 推理长度超训练长度时，远距离的旋转角度落在训练分布之外，attention 分数变得不可预测。需要 YaRN/NTK/PI 修正。

> 📚 原理详解：[02-Transformer篇/04-位置编码.md](../02-Transformer篇/04-位置编码.md)
