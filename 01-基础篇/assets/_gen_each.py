"""为每个激活函数生成单图，插入对应章节使用。"""
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


def relu(x):
    return np.maximum(0, x)


def leaky_relu(x, a=0.1):
    return np.where(x > 0, x, a * x)


x = np.linspace(-4, 4, 600)


def plot_single(fn, name, color, fname, ylim=None, extra_lines=None, subtitle=None):
    """画单个激活函数曲线 + 导数曲线。"""
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))

    # 左：函数本体
    ax = axes[0]
    ax.plot(x, fn(x), lw=2.2, color=color, label=name)
    if extra_lines:
        for label, ys, kw in extra_lines:
            ax.plot(x, ys, label=label, **kw)
    ax.axhline(0, color="gray", lw=0.5)
    ax.axvline(0, color="gray", lw=0.5)
    ax.set_xlabel("x")
    ax.set_ylabel("f(x)")
    ax.set_title(f"{name}" + (f"\n{subtitle}" if subtitle else ""))
    if ylim:
        ax.set_ylim(*ylim)
    ax.grid(alpha=0.3)
    ax.legend(loc="best")

    # 右：数值导数
    dx = x[1] - x[0]
    dy = np.gradient(fn(x), dx)
    ax = axes[1]
    ax.plot(x, dy, lw=2.2, color=color, linestyle="-", label=f"f'(x)")
    ax.axhline(0, color="gray", lw=0.5)
    ax.axvline(0, color="gray", lw=0.5)
    ax.set_xlabel("x")
    ax.set_ylabel("f'(x)")
    ax.set_title(f"{name}  derivative (gradient)")
    ax.grid(alpha=0.3)
    ax.legend(loc="best")

    plt.tight_layout()
    out = os.path.join(OUT_DIR, fname)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"saved {out}")


# 1. Sigmoid
plot_single(
    sigmoid,
    "Sigmoid",
    "#ef4444",
    "act_sigmoid.png",
    ylim=(-0.1, 1.1),
    subtitle="f(x) = 1 / (1 + exp(-x))",
)

# 2. Tanh
plot_single(
    np.tanh,
    "Tanh",
    "#f59e0b",
    "act_tanh.png",
    ylim=(-1.1, 1.1),
    subtitle="f(x) = tanh(x)",
)

# 3. ReLU
plot_single(
    relu,
    "ReLU",
    "#3b82f6",
    "act_relu.png",
    ylim=(-0.5, 4),
    subtitle="f(x) = max(0, x)",
)

# 4. Leaky ReLU
plot_single(
    leaky_relu,
    "Leaky ReLU (alpha=0.1)",
    "#06b6d4",
    "act_leaky_relu.png",
    ylim=(-1, 4),
    subtitle="f(x) = max(alpha·x, x),  alpha = 0.1",
)

# 5. GELU
plot_single(
    gelu,
    "GELU",
    "#10b981",
    "act_gelu.png",
    ylim=(-0.5, 4),
    subtitle="f(x) = x · Phi(x)  (Phi = standard normal CDF)",
)

# 6. Swish / SiLU
plot_single(
    swish,
    "Swish / SiLU",
    "#8b5cf6",
    "act_swish.png",
    ylim=(-0.5, 4),
    subtitle="f(x) = x · sigma(x)",
)

print("done.")
