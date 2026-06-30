"""
MathBot UZ - Matematik render moduli
LaTeX formulalarni va grafiklarni rasm sifatida generatsiya qiladi
"""
import matplotlib
matplotlib.use('Agg')  # GUI siz rejim
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import io
import re

plt.rcParams['font.family'] = 'DejaVu Sans'

def render_latex_formula(latex_str, fontsize=24):
    """
    LaTeX formulani PNG rasm sifatida render qiladi.
    Masalan: r'$x^3 + x^2 - 3x + 1 = 0$'
    """
    fig = plt.figure(figsize=(8, 1.5))
    fig.patch.set_facecolor('white')
    text = fig.text(0.5, 0.5, latex_str, fontsize=fontsize,
                     ha='center', va='center', color='#0F172A')

    fig.canvas.draw()
    bbox = text.get_window_extent()
    width = bbox.width / fig.dpi + 0.5
    height = bbox.height / fig.dpi + 0.4
    fig.set_size_inches(width, height)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=200, bbox_inches='tight',
                pad_inches=0.15, facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf


def render_function_graph(func_str, x_range=(-10, 10), title=None,
                            points=None, vlines=None, hlines=None):
    """
    Funksiya grafigini chizadi.
    func_str: Python ifodasi, masalan "x**2 - 3*x + 2"
    points: [(x1,y1,'label'), ...] - belgilangan nuqtalar
    vlines: [x1, x2, ...] - vertikal chiziqlar (masalan asimptotalar)
    hlines: [y1, y2, ...] - gorizontal chiziqlar
    """
    fig, ax = plt.subplots(figsize=(7, 6))
    fig.patch.set_facecolor('white')

    x = np.linspace(x_range[0], x_range[1], 1000)

    safe_dict = {
        'x': x, 'np': np, 'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
        'exp': np.exp, 'log': np.log, 'sqrt': np.sqrt, 'abs': np.abs,
        'pi': np.pi, 'e': np.e
    }

    try:
        y = eval(func_str, {"__builtins__": {}}, safe_dict)
        y = np.where(np.abs(y) > 1e6, np.nan, y)
    except Exception as e:
        y = np.zeros_like(x)

    ax.plot(x, y, color='#1B4FD8', linewidth=2.5, label=f'y = {func_str}')

    ax.axhline(y=0, color='#94A3B8', linewidth=1)
    ax.axvline(x=0, color='#94A3B8', linewidth=1)
    ax.grid(True, linestyle='--', alpha=0.3, color='#CBD5E1')

    if vlines:
        for vx in vlines:
            ax.axvline(x=vx, color='#DC2626', linestyle='--', linewidth=1.2, alpha=0.7)

    if hlines:
        for hy in hlines:
            ax.axhline(y=hy, color='#D97706', linestyle='--', linewidth=1.2, alpha=0.7)

    if points:
        for px, py, label in points:
            ax.plot(px, py, 'o', color='#059669', markersize=9, zorder=5)
            ax.annotate(label, (px, py), textcoords="offset points",
                       xytext=(8, 8), fontsize=10, color='#059669', fontweight='bold')

    ax.set_xlabel('x', fontsize=12)
    ax.set_ylabel('y', fontsize=12)
    if title:
        ax.set_title(title, fontsize=13, fontweight='bold', color='#0F172A', pad=12)
    ax.legend(fontsize=11, loc='best')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf


def render_geometry_triangle(a=5, b=6, c=7, labels=None, title="Uchburchak"):
    """Uchburchak chizadi, tomonlar bilan"""
    fig, ax = plt.subplots(figsize=(6, 5.5))
    fig.patch.set_facecolor('white')

    # Cosine rule to place points
    A = np.array([0, 0])
    B = np.array([c, 0])
    cos_angle = (b**2 + c**2 - a**2) / (2*b*c)
    cos_angle = np.clip(cos_angle, -1, 1)
    angle = np.arccos(cos_angle)
    C = np.array([b*np.cos(angle), b*np.sin(angle)])

    triangle = plt.Polygon([A, B, C], fill=True, facecolor='#EEF2FF',
                            edgecolor='#1B4FD8', linewidth=2.5)
    ax.add_patch(triangle)

    label_names = labels or ['A', 'B', 'C']
    for point, name, offset in [(A, label_names[0], (-0.3,-0.3)),
                                  (B, label_names[1], (0.15,-0.3)),
                                  (C, label_names[2], (0.1,0.15))]:
        ax.plot(*point, 'o', color='#0F172A', markersize=6)
        ax.annotate(name, point, textcoords="offset points",
                   xytext=(offset[0]*30, offset[1]*30), fontsize=14,
                   fontweight='bold', color='#0F172A')

    mid_AB = (A+B)/2
    mid_BC = (B+C)/2
    mid_AC = (A+C)/2
    ax.annotate(f'{c}', mid_AB, textcoords="offset points", xytext=(0,-18),
               fontsize=12, color='#DC2626', fontweight='bold', ha='center')
    ax.annotate(f'{a}', mid_BC, textcoords="offset points", xytext=(15,5),
               fontsize=12, color='#DC2626', fontweight='bold')
    ax.annotate(f'{b}', mid_AC, textcoords="offset points", xytext=(-20,5),
               fontsize=12, color='#DC2626', fontweight='bold')

    ax.set_title(title, fontsize=13, fontweight='bold', pad=12)
    ax.set_aspect('equal')
    ax.axis('off')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf


def render_bar_chart(categories, values, title="Statistika", ylabel="Qiymat"):
    """Statistik ustunli diagramma"""
    fig, ax = plt.subplots(figsize=(7, 5))
    fig.patch.set_facecolor('white')

    colors = ['#1B4FD8', '#059669', '#D97706', '#DC2626', '#6D28D9', '#0891B2']
    bars = ax.bar(categories, values, color=colors[:len(categories)], edgecolor='white', linewidth=1)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.02,
               str(val), ha='center', fontsize=11, fontweight='bold', color='#0F172A')

    ax.set_title(title, fontsize=13, fontweight='bold', pad=12)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, axis='y', linestyle='--', alpha=0.3)

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf
