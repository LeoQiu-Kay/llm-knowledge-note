"""生成激活函数示意图 (用于 D:/Data/Transformer/01-基础篇/05-激活函数.md)"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_DIR = r"D:/Data/Transformer/01-基础篇/assets"
os.makedirs(OUT_DIR, exist_ok=True)


def gelu(x):
    return 0.5 * x * (1 + np.tanh(np.sqrt(2 / np.pi) * (x + 0.044715 * x ** 3)))


def swish(x):
    return x / (1 + np.exp(-x))


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


# ---------- Figure 1: activation curves ----------
x = np.linspace(-4, 4, 600)

fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))

# Panel A: 现代主流（非饱和 / 平滑系）
ax = axes[0]
ax.plot(x, np.maximum(0, x), label="ReLU", lw=2)
ax.plot(x, np.where(x > 0, x, 0.1 * x), label="Leaky ReLU (alpha=0.1)", lw=2, linestyle="--")
ax.plot(x, gelu(x), label="GELU", lw=2)
ax.plot(x, swish(x), label="Swish / SiLU", lw=2)
ax.set_title("Modern activations (used in LLMs)")
ax.set_xlabel("x")
ax.set_ylabel("f(x)")
ax.axhline(0, color="gray", lw=0.5)
ax.axvline(0, color="gray", lw=0.5)
ax.legend(loc="upper left")
ax.grid(alpha=0.3)
ax.set_ylim(-1.5, 4)

# Panel B: 经典饱和函数
ax = axes[1]
ax.plot(x, sigmoid(x), label="Sigmoid", lw=2)
ax.plot(x, np.tanh(x), label="Tanh", lw=2)
ax.set_title("Saturating activations (early models)")
ax.set_xlabel("x")
ax.set_ylabel("f(x)")
ax.axhline(0, color="gray", lw=0.5)
ax.axvline(0, color="gray", lw=0.5)
ax.axhline(1, color="gray", lw=0.3, linestyle=":")
ax.axhline(-1, color="gray", lw=0.3, linestyle=":")
ax.legend(loc="lower right")
ax.grid(alpha=0.3)
ax.set_ylim(-1.2, 1.2)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "activations.png"), dpi=150, bbox_inches="tight")
plt.close()
print("saved activations.png")


# ---------- Figure 2: softmax with different temperatures ----------
logits = np.array([3.0, 1.5, 1.0, 0.5, -0.5])
labels = ["A", "B", "C", "D", "E"]


def softmax(z, T=1.0):
    z = z / T
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


fig, axes = plt.subplots(1, 3, figsize=(13, 4))
for ax, T, title in zip(
    axes,
    [0.5, 1.0, 3.0],
    ["T=0.5 (sharp, closer to argmax)", "T=1.0 (default)", "T=3.0 (smooth, closer to uniform)"],
):
    p = softmax(logits, T)
    bars = ax.bar(labels, p, color="#3b82f6")
    ax.set_title(title)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Probability")
    ax.grid(axis="y", alpha=0.3)
    for i, v in enumerate(p):
        ax.text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)

plt.suptitle(
    "Softmax with logits = " + str(list(logits)) + "   (subtract max for numerical stability)",
    y=1.02,
    fontsize=11,
)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "softmax_temperature.png"), dpi=150, bbox_inches="tight")
plt.close()
print("saved softmax_temperature.png")


# ---------- Figure 3: SwiGLU gating illustration ----------
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))

x_ = np.linspace(-4, 4, 400)
# 左：Swish(x) = x * sigmoid(x) 作为门控强度的基函数
ax = axes[0]
ax.plot(x_, swish(x_), label="Swish(x) = x * sigma(x)", lw=2, color="#3b82f6")
ax.plot(x_, sigmoid(x_), label="sigma(x) (gate)", lw=1.5, linestyle="--", color="#f97316")
ax.axhline(0, color="gray", lw=0.5)
ax.axvline(0, color="gray", lw=0.5)
ax.set_title("Component: Swish vs Sigmoid gate")
ax.set_xlabel("x")
ax.legend()
ax.grid(alpha=0.3)

# 右：SwiGLU(a, b) = Swish(a) * b，作为 a 与 b 的乘积示意（取 a=Swish(x), b=x）
ax = axes[1]
a = np.linspace(-3, 3, 100)
b = np.linspace(-3, 3, 100)
A, B = np.meshgrid(a, b)
Z = swish(A) * B  # SwiGLU 形式
im = ax.imshow(
    Z,
    extent=(a.min(), a.max(), b.min(), b.max()),
    origin="lower",
    aspect="auto",
    cmap="RdBu_r",
)
ax.set_title("SwiGLU(a, b) = Swish(a) * b")
ax.set_xlabel("a (W1 x)")
ax.set_ylabel("b (W3 x)")
plt.colorbar(im, ax=ax, label="output")

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "swiglu_gating.png"), dpi=150, bbox_inches="tight")
plt.close()
print("saved swiglu_gating.png")
