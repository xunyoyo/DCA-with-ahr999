# trade_bot.py (Final Dashboard Version v6.0)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Investment Bot for OKX with Multi-Chart Dashboard
---------------------------------------------------------
This final version generates a full dashboard of charts:
1. Return on Investment (ROI) Curve
2. Portfolio Equity Curve (Net Asset Value)
3. Cumulative Cost vs. Portfolio Value
"""

import os
import math
import time
import datetime as dt
import requests
import pandas as pd
import numpy as np
import ccxt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.transforms as mtransforms
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import MaxNLocator

# ==============================================================================
# SECTION 1: FINAL STRATEGY PARAMETERS
# ==============================================================================
# 基准投资额：优先从环境变量读取，否则使用默认值
DEFAULT_BASELINE_INVESTMENT = 5.0
try:
    BASELINE_INVESTMENT = float(os.getenv("BASELINE_INVESTMENT", DEFAULT_BASELINE_INVESTMENT))
    if BASELINE_INVESTMENT <= 0:
        print(f"⚠️ Invalid BASELINE_INVESTMENT value: {BASELINE_INVESTMENT}, using default: {DEFAULT_BASELINE_INVESTMENT}")
        BASELINE_INVESTMENT = DEFAULT_BASELINE_INVESTMENT
    else:
        print(f"✅ Using BASELINE_INVESTMENT: ${BASELINE_INVESTMENT}")
except (ValueError, TypeError):
    print(f"⚠️ Invalid BASELINE_INVESTMENT format, using default: ${DEFAULT_BASELINE_INVESTMENT}")
    BASELINE_INVESTMENT = DEFAULT_BASELINE_INVESTMENT

OKX_SYMBOL = "BTC/USDT"
GENESIS = dt.date(2009, 1, 3)
ALPHA = 1.5
BETA = 0.8
DAILY_CAP_X = 4.0
PAUSE_THRESHOLD = 2.0
NEUTRAL_X = 1.0
MIN_TRADE_USD = 1.0
LOG_FILE = "trade_log.csv"
LOG_COLUMNS = ['date', 'buy_usd', 'buy_btc', 'price_usd']
DEFAULT_CHART_THEME = "professional"

# ==============================================================================
# MODERN CHART THEMES (New section)
# ==============================================================================
CHART_THEMES = {
    "professional": {
        "label": "Professional",
        "style": "seaborn-v0_8-whitegrid",
        # 三种语义色：蓝=自己的仓位，橙=投进去的钱，青=市场
        "palette": {
            "roi": "#2a78d6",
            "value": "#1baf7a",
            "cost": "#eb6834",
            "positive_fill": "#1baf7a",
            "negative_fill": "#e34948"
        },
        "rc": {
            "axes.titlesize": 13,
            "axes.labelsize": 10,
            "axes.titlecolor": "#0F172A",
            "axes.labelcolor": "#475569",
            "axes.edgecolor": "#CBD5E1",
            "xtick.color": "#64748B",
            "ytick.color": "#64748B",
            "grid.color": "#EEF1F5",
        },
        "figure_facecolor": "#F5F6F8",
        "axes_facecolor": "#FFFFFF",
        "hairline": "#E6E8EC"
    },
    "light": {
        "label": "Snowy Minimal",
        "style": "seaborn-v0_8-whitegrid",
        "palette": {
            "roi": "#2563EB",
            "value": "#16A34A",
            "cost": "#F97316",
            "positive_fill": "#22C55E",
            "negative_fill": "#F87171"
        },
        "rc": {
            "axes.titlesize": 13,
            "axes.labelsize": 10,
            "axes.titlecolor": "#0F172A",
            "axes.labelcolor": "#475569",
            "axes.edgecolor": "#CBD5E1",
            "xtick.color": "#64748B",
            "ytick.color": "#64748B",
            "grid.color": "#E2E8F0",
        },
        "figure_facecolor": "#F8FAFC",
        "axes_facecolor": "#FFFFFF",
        "hairline": "#E2E8F0"
    },
    "midnight": {
        "label": "Midnight Dashboard",
        "style": "seaborn-v0_8-darkgrid",
        "palette": {
            "roi": "#3987e5",
            "value": "#199e70",
            "cost": "#d95926",
            "positive_fill": "#199e70",
            "negative_fill": "#e66767"
        },
        "rc": {
            "axes.titlesize": 13,
            "axes.labelsize": 10,
            "axes.titlecolor": "#E2E8F0",
            "axes.labelcolor": "#CBD5E1",
            "axes.edgecolor": "#1F2937",
            "xtick.color": "#94A3B8",
            "ytick.color": "#94A3B8",
            "grid.color": "#1F2937",
        },
        "figure_facecolor": "#0B1120",
        "axes_facecolor": "#111827",
        "hairline": "#1F2937"
    },
    "neon": {
        "label": "Neon Tech",
        "style": "fast",
        "palette": {
            "roi": "#38BDF8",
            "value": "#22D3EE",
            "cost": "#F0ABFC",
            "positive_fill": "#34D399",
            "negative_fill": "#FB7185"
        },
        "rc": {
            "axes.titlesize": 13,
            "axes.labelsize": 10,
            "axes.titlecolor": "#F8FAFC",
            "axes.labelcolor": "#E0F2FE",
            "axes.edgecolor": "#312E81",
            "xtick.color": "#C7D2FE",
            "ytick.color": "#C7D2FE",
            "grid.color": "#1E1B4B",
        },
        "figure_facecolor": "#0B1120",
        "axes_facecolor": "#111827",
        "hairline": "#312E81"
    }
}


def _resolve_chart_theme(theme_key):
    key = (theme_key or DEFAULT_CHART_THEME).lower().strip()
    if key not in CHART_THEMES:
        print(f"⚠️ Unknown chart theme '{theme_key}', falling back to '{DEFAULT_CHART_THEME}'.")
        key = DEFAULT_CHART_THEME
    theme = dict(CHART_THEMES[key])
    # 深色主题用浅墨色，浅色主题用深墨色
    theme['ink'] = INK_DARK if key in ('midnight', 'neon') else INK_LIGHT
    return key, theme

# ==============================================================================
# SECTION 2: HELPERS (Now includes multiple chart functions)
# ==============================================================================
def create_github_issue(title: str, body: str):
    repo_slug=os.getenv("GITHUB_REPOSITORY"); token=os.getenv("GITHUB_TOKEN")
    if not repo_slug or not token: return
    url=f"https://api.github.com/repos/{repo_slug}/issues"
    headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    try:
        response=requests.post(url, headers=headers, json={"title": title, "body": body}, timeout=10)
        if response.status_code != 201: print(f"Failed to create GitHub issue: {response.status_code} {response.text}")
    except Exception as e: print(f"Error creating GitHub issue: {e}")

# --- Charting -----------------------------------------------------------------
# 墨色：所有文字、网格、坐标轴都用这套，不跟随数据色，保证视觉层级稳定。
INK_LIGHT = {"strong": "#0F172A", "secondary": "#475569", "muted": "#64748B",
             "faint": "#CBD5E1", "axis": "#CBD5E1", "grid": "#EEF1F5",
             "gain": "#0F8A5A", "loss": "#D03B3B"}
INK_DARK = {"strong": "#F1F5F9", "secondary": "#CBD5E1", "muted": "#94A3B8",
            "faint": "#334155", "axis": "#334155", "grid": "#1F2937",
            "gain": "#34D399", "loss": "#E66767"}

# CI 上装了 fonts-inter，本地不一定；按顺序挑第一个真正可用的字体，避免 findfont 警告
_FONT_CANDIDATES = ('Inter', 'Helvetica Neue', 'Arial', 'DejaVu Sans')
_MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
_MINUS = '−'


def _pick_font_family():
    installed = {face.name for face in font_manager.fontManager.ttflist}
    for name in _FONT_CANDIDATES:
        if name in installed:
            return name
    return 'DejaVu Sans'


def _fmt_signed(value, decimals=2, money=False, suffix=''):
    """带 +/− 的数字；正负靠符号表达，不只靠颜色。"""
    sign = _MINUS if value < 0 else ('+' if value > 0 else '')
    body = f'{abs(value):,.{decimals}f}'
    return f'{sign}{"$" if money else ""}{body}{suffix}'


def _fmt_money_tick(value, _=None):
    """坐标轴上的紧凑金额：$4K / $120K / $40。"""
    if abs(value) >= 1000:
        return f'${value / 1000:,.0f}K' if value % 1000 == 0 else f'${value / 1000:,.1f}K'
    return f'${value:,.0f}'


def _fmt_percent_tick(value, _=None):
    return f'{value:.0f}%'.replace('-', _MINUS)


def _fmt_btc_tick(value, _=None):
    text = f'{value:.2f}'.rstrip('0').rstrip('.')
    return text or '0'


def _fmt_month(value, _=None):
    """横轴月份写成 Nov '25，比 2025-11 更短也更好读。"""
    moment = mdates.num2date(value)
    return f"{_MONTHS[moment.month - 1]} '{moment.year % 100:02d}"


_NICE_STEPS = (5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 150, 200, 250, 300,
               400, 500, 750, 1000, 1500, 2000, 2500, 5000)


def _nice_ceil(value):
    """把坐标轴上限抬到一个整齐的刻度。"""
    for step in _NICE_STEPS:
        if value <= step:
            return float(step)
    return float(np.ceil(value / 1000.0) * 1000)


def _prepare_chart_data(log_df: pd.DataFrame) -> pd.DataFrame:
    """按自然日聚合后补齐日历。

    日志里一行是一笔交易，但每张图讲的是「一天」。一天里成交多笔时，
    旧代码会在同一个横坐标上叠多个点，再交给样条插值，结果就是图中
    那种夸张的竖刺。补齐全日历还能让「当天没投」变成可见的平地，
    而不是横坐标上的一个跳空。
    """
    df = log_df.copy()
    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.normalize()
    for column in ('buy_usd', 'buy_btc', 'price_usd'):
        df[column] = pd.to_numeric(df[column], errors='coerce')
    df = df.dropna(subset=['date', 'buy_usd', 'buy_btc', 'price_usd'])
    df = df[(df['price_usd'] > 0) & (df['buy_usd'] >= 0) & (df['buy_btc'] >= 0)]
    if df.empty:
        return df.reset_index(drop=True)

    # 跳过日也会写一行 buy_usd=0，笔数只数真正成交的行
    df['_bought'] = (df['buy_usd'] > 0).astype(int)
    daily = (
        df.groupby('date')
        .agg(
            buy_usd=('buy_usd', 'sum'),
            buy_btc=('buy_btc', 'sum'),
            price_usd=('price_usd', 'last'),
            trades=('_bought', 'sum'),
        )
        .sort_index()
    )

    calendar = pd.date_range(daily.index.min(), daily.index.max(), freq='D')
    daily = daily.reindex(calendar)
    daily['trades'] = daily['trades'].fillna(0).astype(int)
    daily['buy_usd'] = daily['buy_usd'].fillna(0.0)
    daily['buy_btc'] = daily['buy_btc'].fillna(0.0)
    daily['price_usd'] = daily['price_usd'].ffill().bfill()

    daily['invest_cum'] = daily['buy_usd'].cumsum()
    daily['hold_btc_cum'] = daily['buy_btc'].cumsum()
    daily['value_usd'] = daily['hold_btc_cum'] * daily['price_usd']
    daily['avg_cost'] = np.where(
        daily['hold_btc_cum'] > 0,
        daily['invest_cum'] / daily['hold_btc_cum'].replace(0, np.nan),
        np.nan,
    )
    daily['roi'] = np.where(
        daily['invest_cum'] > 0,
        daily['value_usd'] / daily['invest_cum'].replace(0, np.nan) - 1.0,
        0.0,
    )
    daily.index.name = 'date'
    return daily.reset_index()


CARD_PAD = 0.22        # 卡片内边距（英寸）
CARD_TITLE_H = 0.62    # 卡片里标题 + 副标题占的高度
AXIS_GUTTER_Y = 0.60   # 左边留给纵轴刻度的位置
AXIS_GUTTER_X = 0.34   # 底部留给横轴刻度的位置


def _card(fig, x, y, w, h, surface, hairline):
    """圆角卡片。用英寸坐标画，圆角在横竖方向才是等半径的。"""
    width, height = fig.get_size_inches()
    inches = mtransforms.Affine2D().scale(1.0 / width, 1.0 / height) + fig.transFigure
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.10",
                           facecolor=surface, edgecolor=hairline, linewidth=0.8,
                           transform=inches, zorder=-10, clip_on=False)
    fig.add_artist(patch)


def _axes_at(fig, rect):
    x, y, w, h = rect
    width, height = fig.get_size_inches()
    ax = fig.add_axes([x / width, y / height, w / width, h / height])
    ax.set_facecolor('none')
    return ax


def _style_axes(ax, theme):
    ink = theme['ink']
    for side in ax.spines.values():
        side.set_visible(False)
    ax.spines['bottom'].set_visible(True)
    ax.spines['bottom'].set_color(ink['axis'])
    ax.spines['bottom'].set_linewidth(0.8)
    ax.grid(axis='y', color=ink['grid'], linewidth=0.8, linestyle='-')
    ax.grid(axis='x', visible=False)
    ax.set_axisbelow(True)
    ax.tick_params(axis='both', which='both', length=0, labelsize=9, colors=ink['muted'])
    ax.tick_params(axis='x', pad=7)
    ax.tick_params(axis='y', pad=6)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4))


def _format_time_axis(ax, ink, months=2):
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=months))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_fmt_month))
    for label in ax.get_xticklabels():
        label.set_color(ink['muted'])


def _end_dot(ax, x_series, y_series, color, surface):
    """只在最后一个点上放一个带卡片色描边的圆点。"""
    value = float(y_series.iloc[-1])
    if not np.isfinite(value):
        return
    ax.plot([x_series.iloc[-1]], [value], linestyle='none', marker='o',
            markersize=5.5, color=color, markeredgecolor=surface,
            markeredgewidth=1.4, zorder=7, clip_on=False)


def _panel_frame(fig, x, y, w, h, title, subtitle, value, value_color, ink, theme, legend=None):
    """画一张图表卡片并返回绘图区（英寸坐标）。

    标题、副标题、当前值、图例都放在卡片内，所以卡片要按文字重新留边。
    """
    _card(fig, x, y, w, h, theme['axes_facecolor'], theme['hairline'])
    width, height = fig.get_size_inches()
    inner = CARD_PAD
    top = y + h - inner
    fig.text((x + inner) / width, top / height, title, fontsize=13, fontweight='semibold',
             color=ink['strong'], ha='left', va='top')
    fig.text((x + inner) / width, (top - 0.31) / height, subtitle, fontsize=9,
             color=ink['muted'], ha='left', va='top')
    if value:
        fig.text((x + w - inner) / width, (top + 0.01) / height, value, fontsize=12.5,
                 fontweight='semibold', color=value_color, ha='right', va='top')
    if legend:
        handles = [Line2D([], [], color=color, linewidth=1.6, linestyle=style,
                          solid_capstyle='round') for _, color, style in legend]
        labels = [label for label, _, _ in legend]
        fig.legend(handles, labels, loc='center right', ncol=len(labels),
                   bbox_to_anchor=((x + w - inner) / width, (top - 0.38) / height),
                   bbox_transform=fig.transFigure, frameon=False, fontsize=9,
                   labelcolor=ink['muted'], handlelength=1.3, handletextpad=0.5,
                   borderpad=0, borderaxespad=0, columnspacing=1.4)
    return (x + inner + AXIS_GUTTER_Y, y + inner + AXIS_GUTTER_X,
            w - 2 * inner - AXIS_GUTTER_Y, h - 2 * inner - AXIS_GUTTER_X - CARD_TITLE_H)


def _draw_stat_tiles(fig, x, y, w, h, tiles, ink, theme, gap=0.26):
    """顶部五个等宽指标卡。"""
    width, height = fig.get_size_inches()
    tile_w = (w - gap * (len(tiles) - 1)) / len(tiles)
    for index, (label, value, sub, color) in enumerate(tiles):
        left = x + index * (tile_w + gap)
        _card(fig, left, y, tile_w, h, theme['axes_facecolor'], theme['hairline'])
        fig.text((left + 0.22) / width, (y + h - 0.20) / height, label, fontsize=9.5,
                 color=ink['muted'], ha='left', va='top')
        fig.text((left + 0.22) / width, (y + h - 0.46) / height, value, fontsize=17,
                 fontweight='semibold', color=color, ha='left', va='top')
        fig.text((left + 0.22) / width, (y + h - 0.86) / height, sub, fontsize=9,
                 color=ink['muted'], ha='left', va='top')


def _mark_axis_break(ax_hi, ax_lo, ink):
    """断轴标记：在断层两侧的左轴线各画一道短斜线。"""
    width, height = ax_hi.figure.get_size_inches()
    for ax, edge in ((ax_hi, 0.0), (ax_lo, 1.0)):
        box = ax.get_position()
        # 换算成英寸，斜线才不会被拉成横线；短一点，上下两道不会连成一条
        dx = 0.035 / (box.width * width)
        dy = 0.035 / (box.height * height)
        ax.plot((-dx, dx), (edge - dy, edge + dy), transform=ax.transAxes,
                color=ink['muted'], linewidth=1.1, clip_on=False, zorder=10)


def _plot_roi_curve(ax, df, palette, ink, surface):
    x, y = df['date'], df['roi'] * 100
    ax.fill_between(x, 0, y, where=y >= 0, color=palette['positive_fill'],
                    alpha=0.12, linewidth=0, interpolate=True, zorder=2)
    ax.fill_between(x, 0, y, where=y < 0, color=palette['negative_fill'],
                    alpha=0.10, linewidth=0, interpolate=True, zorder=2)
    ax.plot(x, y, color=palette['roi'], linewidth=1.5, solid_capstyle='round', zorder=3)
    ax.axhline(0, color=ink['axis'], linewidth=0.9, zorder=4)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_fmt_percent_tick))
    low, high = float(np.nanmin(y)), float(np.nanmax(y))
    span = max(high - low, 1.0)
    ax.set_ylim(min(low, 0.0) - span * 0.10, max(high, 0.0) + span * 0.10)
    _end_dot(ax, x, y, palette['roi'], surface)


def _plot_equity_curve(ax, df, palette, ink, surface):
    x, y = df['date'], df['value_usd']
    ax.fill_between(x, 0, y, color=palette['value'], alpha=0.10, linewidth=0, zorder=2)
    ax.plot(x, y, color=palette['value'], linewidth=1.5, solid_capstyle='round', zorder=3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_fmt_money_tick))
    ax.set_ylim(0, float(y.max()) * 1.08)
    _end_dot(ax, x, y, palette['value'], surface)


def _plot_value_vs_cost(ax, df, palette, ink, surface):
    x, value, cost = df['date'], df['value_usd'], df['invest_cum']
    ax.fill_between(x, cost, value, where=value >= cost, color=palette['positive_fill'],
                    alpha=0.12, linewidth=0, interpolate=True, zorder=2)
    ax.fill_between(x, cost, value, where=value < cost, color=palette['negative_fill'],
                    alpha=0.10, linewidth=0, interpolate=True, zorder=2)
    ax.plot(x, cost, color=palette['cost'], linewidth=1.5, solid_capstyle='round', zorder=3)
    ax.plot(x, value, color=palette['value'], linewidth=1.5, solid_capstyle='round', zorder=4)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_fmt_money_tick))
    ax.set_ylim(0, max(float(value.max()), float(cost.max())) * 1.08)
    _end_dot(ax, x, cost, palette['cost'], surface)
    _end_dot(ax, x, value, palette['value'], surface)
def _daily_split(amounts):
    """找出纵轴该断开的位置；没有离群值时返回 None。"""
    positive = amounts[amounts > 0]
    if positive.size < 10:
        return None
    split = _nice_ceil(float(np.percentile(positive, 99)) * 1.15)
    return split if amounts.max() > split * 1.5 else None


def _plot_daily_investment(ax_lo, ax_hi, df, palette, ink, split):
    """每日投入额，用柱状而非折线。

    投资额是离散事件，折线会把「当天没投」画成斜着下降。更麻烦的是
    一天里跑了十几次、总额是平常日二十几倍的那种日子：一根柱子会把
    其余四百天压成贴地的一条线。有这种断档时把纵轴断开，两端都看得清。
    """
    x = df['date']
    amount = df['buy_usd'].to_numpy()
    trades = df['trades'].to_numpy()
    positive = amount[amount > 0]
    baseline = float(np.median(positive)) if positive.size else 0.0
    top = _nice_ceil(float(amount.max()))

    axes = [ax_lo] if ax_hi is None else [ax_hi, ax_lo]
    for ax in axes:
        ax.bar(x, amount, width=0.78, color=palette['cost'], alpha=0.92, linewidth=0, zorder=3)

    ax_lo.set_ylim(0, split if split else top)
    if ax_hi is not None:
        ax_hi.set_ylim(split, top)

    if baseline > 0:
        ax_lo.axhline(baseline, color=ink['faint'], linestyle=(0, (4, 3)),
                      linewidth=1.0, zorder=5)

    # 一天多笔的日子标个 ×N；离得太近或贴着右边缘的就不标，免得字叠在一起
    last_labelled = None
    for day, value, count in zip(x, amount, trades):
        if count <= 1 or (split and value >= split):
            continue
        if (x.iloc[-1] - day).days < 12:
            continue
        if last_labelled is not None and (day - last_labelled).days < 20:
            continue
        last_labelled = day
        ax_lo.annotate(f'×{count}', xy=(day, value), xytext=(0, 3), textcoords='offset points',
                       ha='center', va='bottom', fontsize=8, color=ink['muted'], zorder=6)

    if ax_hi is not None:
        peak = int(np.argmax(amount))
        label = f'${amount[peak]:,.2f}'
        if trades[peak] > 1:
            label += f' · {int(trades[peak])} buys'
        # 断轴上方的柱子很高，标签放在柱顶左侧的空处，避免顶到坐标轴
        ax_hi.annotate(label, xy=(x.iloc[peak], amount[peak]), xytext=(-7, -3),
                       textcoords='offset points', ha='right', va='top',
                       fontsize=8.5, fontweight='semibold', color=palette['cost'], zorder=6)


def _plot_btc_accumulation(ax, df, palette, ink, surface):
    x, y = df['date'], df['hold_btc_cum']
    ax.fill_between(x, 0, y, color=palette['roi'], alpha=0.10, linewidth=0, zorder=2)
    ax.plot(x, y, color=palette['roi'], linewidth=1.5, solid_capstyle='round', zorder=3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_fmt_btc_tick))
    ax.set_ylim(0, float(y.max()) * 1.08)
    _end_dot(ax, x, y, palette['roi'], surface)


def _plot_avg_cost_vs_price(ax, df, palette, ink, surface):
    x, price, cost = df['date'], df['price_usd'], df['avg_cost']
    ax.fill_between(x, cost, price, where=price >= cost, color=palette['positive_fill'],
                    alpha=0.12, linewidth=0, interpolate=True, zorder=2)
    ax.fill_between(x, cost, price, where=price < cost, color=palette['negative_fill'],
                    alpha=0.10, linewidth=0, interpolate=True, zorder=2)
    ax.plot(x, price, color=palette['value'], linewidth=1.5, solid_capstyle='round', zorder=4)
    ax.plot(x, cost, color=palette['cost'], linewidth=1.5, solid_capstyle='round', zorder=5)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_fmt_money_tick))
    ax.set_ylim(min(float(price.min()), float(cost.min())) * 0.96, float(price.max()) * 1.04)
    _end_dot(ax, x, price, palette['value'], surface)
    _end_dot(ax, x, cost, palette['cost'], surface)


def _plot_strategy_comparison(ax, df, palette, ink, surface):
    x = df['date']
    price = df['price_usd'].to_numpy(dtype=float)
    positive = df.loc[df['buy_usd'] > 0, 'buy_usd']
    baseline = float(np.median(positive)) if len(positive) else 0.0
    regular_cost = baseline * np.arange(1, len(df) + 1)
    regular_btc = np.cumsum(baseline / price)
    regular_roi = np.where(regular_cost > 0, regular_btc * price / regular_cost - 1.0, np.nan) * 100
    smart = (df['roi'] * 100).to_numpy(dtype=float)

    ax.fill_between(x, regular_roi, smart, where=smart >= regular_roi,
                    color=palette['positive_fill'], alpha=0.12, linewidth=0, interpolate=True, zorder=2)
    ax.fill_between(x, regular_roi, smart, where=smart < regular_roi,
                    color=palette['negative_fill'], alpha=0.10, linewidth=0, interpolate=True, zorder=2)
    ax.axhline(0, color=ink['axis'], linewidth=0.9, zorder=1)
    ax.plot(x, regular_roi, color=palette['cost'], linewidth=1.5, linestyle=(0, (4, 3)),
            dash_capstyle='round', zorder=3)
    ax.plot(x, smart, color=palette['roi'], linewidth=1.5, solid_capstyle='round', zorder=4)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(_fmt_percent_tick))
    low = float(np.nanmin(np.concatenate([smart, regular_roi])))
    high = float(np.nanmax(np.concatenate([smart, regular_roi])))
    span = max(high - low, 1.0)
    ax.set_ylim(min(low, 0.0) - span * 0.10, max(high, 0.0) + span * 0.10)
    _end_dot(ax, x, pd.Series(smart), palette['roi'], surface)
    _end_dot(ax, x, pd.Series(regular_roi), palette['cost'], surface)


def _portfolio_stats(df: pd.DataFrame) -> dict:
    """算出顶部数据条要用到的所有数字。"""
    total_invested = float(df['invest_cum'].iloc[-1])
    total_btc = float(df['hold_btc_cum'].iloc[-1])
    current_value = float(df['value_usd'].iloc[-1])
    current_price = float(df['price_usd'].iloc[-1])
    total_profit = current_value - total_invested
    roi_pct = (total_profit / total_invested) * 100 if total_invested > 0 else 0.0

    positive = df.loc[df['buy_usd'] > 0, 'buy_usd']
    baseline = float(np.median(positive)) if len(positive) else 0.0
    regular_invested = baseline * len(df)
    regular_btc = float((baseline / df['price_usd']).sum())
    regular_profit = regular_btc * current_price - regular_invested
    regular_roi = (regular_profit / regular_invested) * 100 if regular_invested > 0 else 0.0

    return {
        'total_invested': total_invested,
        'total_btc': total_btc,
        'current_value': current_value,
        'current_price': current_price,
        'avg_cost': total_invested / total_btc if total_btc > 0 else 0.0,
        'total_profit': total_profit,
        'roi_pct': roi_pct,
        'regular_roi': regular_roi,
        'strategy_advantage': roi_pct - regular_roi,
        'profit_advantage': total_profit - regular_profit,
        'buy_days': int((df['trades'] > 0).sum()),
        'span_days': len(df),
    }


def _draw_page_header(fig, df, stats, ink, left=0.42):
    """页面标题 + 一行副标题，左边和卡片网格对齐。"""
    width, height = fig.get_size_inches()
    fig.text(left / width, (height - 0.30) / height, 'DCA Investment Dashboard',
             fontsize=23, fontweight='semibold', color=ink['strong'], ha='left', va='top')
    fig.text(left / width, (height - 0.68) / height,
             f'AHR999 adaptive strategy  ·  {df["date"].iloc[0]:%Y-%m-%d}'
             f' – {df["date"].iloc[-1]:%Y-%m-%d}  ·  {stats["span_days"]} days',
             fontsize=10.5, color=ink['muted'], ha='left', va='top')


def generate_dashboard_charts(log_df: pd.DataFrame, theme_key=None):
    if log_df is None or len(log_df) == 0:
        print("⚠️ No data to generate charts.")
        return

    try:
        df = _prepare_chart_data(log_df)
        if df.empty:
            print("⚠️ No investment data yet. Charts will be generated after first trade.")
            return
        if float(df['invest_cum'].iloc[-1]) <= 0:
            # 只有跳过日、没有任何成交时，所有图都是零，没有画的意义
            print("⚠️ No investment data yet. Charts will be generated after first trade.")
            return
        if df['date'].nunique() < 2:
            # 单日数据没有时间跨度，画出来是一张空白图，不如等第二天
            print("⚠️ Need at least two days of history before drawing charts.")
            return

        theme_key, theme = _resolve_chart_theme(theme_key)
        palette, ink = theme['palette'], theme['ink']
        surface, page = theme['axes_facecolor'], theme['figure_facecolor']
        stats = _portfolio_stats(df)
        split = _daily_split(df['buy_usd'].to_numpy())

        rc = dict(theme.get('rc', {}))
        rc.update({
            'font.family': _pick_font_family(),
            'font.size': 10,
            'text.parse_math': False,   # 金额里的 $ 按普通字符处理
            'axes.unicode_minus': False,
            'axes.facecolor': 'none',   # 让圆角卡片当底色
            'figure.facecolor': page,
            'savefig.facecolor': page,
        })
        with plt.style.context(theme.get('style', 'seaborn-v0_8-whitegrid')):
            with plt.rc_context(rc):
                fig = plt.figure(figsize=(15.0, 20.6), dpi=200)
                fig.patch.set_facecolor(page)
                width, height = fig.get_size_inches()

                pad, gap_x, gap_y = 0.42, 0.26, 0.26
                card_w = (width - 2 * pad - gap_x) / 2
                full_w = width - 2 * pad
                tile_h = 1.14
                grid_top = height - 0.98 - tile_h - 0.30
                grid_bottom = 0.40
                row_h = (grid_top - grid_bottom - 3 * gap_y) / 4
                # 四行卡片的底边，行距和列距一致
                rows = [grid_top - i * (row_h + gap_y) - row_h for i in range(4)]

                _draw_page_header(fig, df, stats, ink, left=pad)

                gain_color = ink['gain'] if stats['roi_pct'] >= 0 else ink['loss']
                adv_color = ink['gain'] if stats['strategy_advantage'] >= 0 else ink['loss']
                profit_color = ink['gain'] if stats['total_profit'] >= 0 else ink['loss']
                positive = df.loc[df['buy_usd'] > 0, 'buy_usd']
                median_day = float(np.median(positive)) if len(positive) else 0.0
                peak_day = float(df['buy_usd'].max())

                tiles = [
                    ('Invested', f'${stats["total_invested"]:,.2f}',
                     f'{stats["buy_days"]} buy days', ink['strong']),
                    ('Holdings', f'{stats["total_btc"]:.6f} BTC',
                     f'worth ${stats["current_value"]:,.2f}', ink['strong']),
                    ('Return', _fmt_signed(stats['roi_pct'], 2, suffix='%'),
                     _fmt_signed(stats['total_profit'], 2, money=True), gain_color),
                    ('BTC price', f'${stats["current_price"]:,.0f}',
                     f'avg cost ${stats["avg_cost"]:,.0f}', ink['strong']),
                    ('vs flat DCA', _fmt_signed(stats['strategy_advantage'], 2, suffix=' pp'),
                     _fmt_signed(stats['profit_advantage'], 0, money=True), adv_color),
                ]
                _draw_stat_tiles(fig, pad, height - 0.98 - tile_h, full_w, tile_h, tiles, ink, theme)

                col = [pad, pad + card_w + gap_x]

                # 1. ROI
                rect = _panel_frame(fig, col[0], rows[0], card_w, row_h,
                                    'Return on investment', 'Unrealised return on total invested',
                                    _fmt_signed(stats['roi_pct'], 1, suffix='%'),
                                    gain_color, ink, theme)
                ax_roi = _axes_at(fig, rect)
                _style_axes(ax_roi, theme)
                _plot_roi_curve(ax_roi, df, palette, ink, surface)
                _format_time_axis(ax_roi, ink)

                # 2. 组合市值
                rect = _panel_frame(fig, col[1], rows[0], card_w, row_h,
                                    'Portfolio equity', 'Market value of everything you hold',
                                    f'${stats["current_value"]:,.0f}', ink['strong'], ink, theme)
                ax_equity = _axes_at(fig, rect)
                _style_axes(ax_equity, theme)
                _plot_equity_curve(ax_equity, df, palette, ink, surface)
                _format_time_axis(ax_equity, ink)

                # 3. 市值 vs 投入
                rect = _panel_frame(fig, col[0], rows[1], card_w, row_h,
                                    'Value vs. invested', 'Market value against money put in',
                                    _fmt_signed(stats['total_profit'], 0, money=True),
                                    profit_color, ink, theme,
                                    legend=[('Market value', palette['value'], '-'),
                                            ('Invested', palette['cost'], '-')])
                ax_value = _axes_at(fig, rect)
                _style_axes(ax_value, theme)
                _plot_value_vs_cost(ax_value, df, palette, ink, surface)
                _format_time_axis(ax_value, ink)

                # 4. 每日投入：有离群日时拆成上下两段
                rect = _panel_frame(fig, col[1], rows[1], card_w, row_h,
                                    'Daily investment',
                                    'Amount bought each day; dashed = median, ×N = multiple buys',
                                    f'median ${median_day:,.2f}', ink['strong'], ink, theme)
                if split:
                    x0, y0, w0, h0 = rect
                    ax_daily_hi = _axes_at(fig, (x0, y0 + h0 - 0.62, w0, 0.62))
                    ax_daily = _axes_at(fig, (x0, y0, w0, h0 - 0.76))
                    ax_daily.sharex(ax_daily_hi)
                    _style_axes(ax_daily_hi, theme)
                    _style_axes(ax_daily, theme)
                    ax_daily_hi.spines['bottom'].set_visible(False)
                    ax_daily_hi.tick_params(labelbottom=False)
                    ax_daily_hi.set_yticks([_nice_ceil(peak_day)])
                    ax_daily_hi.yaxis.set_major_formatter(plt.FuncFormatter(_fmt_money_tick))
                    _mark_axis_break(ax_daily_hi, ax_daily, ink)
                else:
                    ax_daily_hi, ax_daily = None, _axes_at(fig, rect)
                    _style_axes(ax_daily, theme)
                ax_daily.yaxis.set_major_formatter(plt.FuncFormatter(_fmt_money_tick))
                _plot_daily_investment(ax_daily, ax_daily_hi, df, palette, ink, split)
                _format_time_axis(ax_daily, ink)

                # 5. BTC 持仓
                rect = _panel_frame(fig, col[0], rows[2], card_w, row_h,
                                    'BTC accumulation', 'Total BTC held over time',
                                    f'{stats["total_btc"]:.6f} BTC', ink['strong'], ink, theme)
                ax_btc = _axes_at(fig, rect)
                _style_axes(ax_btc, theme)
                _plot_btc_accumulation(ax_btc, df, palette, ink, surface)
                _format_time_axis(ax_btc, ink)

                # 6. 价格 vs 均价
                rect = _panel_frame(fig, col[1], rows[2], card_w, row_h,
                                    'Price vs. average cost', 'BTC price against your average cost',
                                    f'${stats["current_price"]:,.0f} vs ${stats["avg_cost"]:,.0f}',
                                    ink['strong'], ink, theme,
                                    legend=[('BTC price', palette['value'], '-'),
                                            ('Average cost', palette['cost'], '-')])
                ax_cost = _axes_at(fig, rect)
                _style_axes(ax_cost, theme)
                _plot_avg_cost_vs_price(ax_cost, df, palette, ink, surface)
                _format_time_axis(ax_cost, ink)

                # 7. 策略对比，整行宽
                rect = _panel_frame(fig, pad, rows[3], full_w, row_h,
                                    'Smart DCA vs. regular DCA',
                                    f'Return against a flat ${median_day:,.2f}/day plan',
                                    _fmt_signed(stats['strategy_advantage'], 2, suffix=' pp'),
                                    adv_color, ink, theme,
                                    legend=[('Smart DCA', palette['roi'], '-'),
                                            ('Regular DCA', palette['cost'], (0, (4, 3)))])
                ax_compare = _axes_at(fig, rect)
                _style_axes(ax_compare, theme)
                _plot_strategy_comparison(ax_compare, df, palette, ink, surface)

                # 横轴只覆盖有数据的月份，右侧多留几天放端点
                span_start = df['date'].iloc[0] - pd.Timedelta(days=1)
                span_end = df['date'].iloc[-1] + pd.Timedelta(days=4)
                for ax in (ax_roi, ax_equity, ax_value, ax_daily, ax_btc, ax_cost, ax_compare):
                    ax.set_xlim(span_start, span_end)

                _format_time_axis(ax_compare, ink, months=1)

                fig.text((width - pad) / width, 0.18 / height, 'github.com/xunyoyo',
                         fontsize=8.5, color=ink['muted'], ha='right', va='bottom')

                output_dashboard = "dashboard_comprehensive.png"
                fig.savefig(output_dashboard, dpi=200, facecolor=page)
                plt.close(fig)
                print(f"✅ Comprehensive Dashboard generated ({theme_key}): {output_dashboard}")

    except Exception as e:
        print(f"Could not generate dashboard charts: {e}")


def calculate_portfolio_summary(log_df: pd.DataFrame, current_price: float) -> str:
    if log_df is None or log_df.empty: return "### 📊 Portfolio Summary\n- No trading history found yet."
    try:
        total_invested_usd=log_df['buy_usd'].sum(); total_holdings_btc=log_df['buy_btc'].sum()
        if total_invested_usd <= 0 or total_holdings_btc <= 0: return "### 📊 Portfolio Summary\n- No valid investment recorded."
        current_value_usd=total_holdings_btc*current_price; average_buy_price=total_invested_usd/total_holdings_btc
        profit_loss_usd=current_value_usd-total_invested_usd; roi_percentage=(profit_loss_usd/total_invested_usd)*100
        pl_sign="+" if profit_loss_usd >= 0 else ""; pl_emoji="🟢" if profit_loss_usd >= 0 else "🔴"
        return (f"### 📊 Portfolio Summary\n"+f"- **Total Invested:** `${total_invested_usd:,.2f}`\n"
                +f"- **Total Holdings:** `{total_holdings_btc:.8f}` BTC\n"+f"- **Current Value:** `${current_value_usd:,.2f}`\n"
                +f"- **Avg. Buy Price:** `${average_buy_price:,.2f}`\n"+f"- **Total P/L:** {pl_emoji} `{pl_sign}${profit_loss_usd:,.2f}`\n"
                +f"- **ROI:** `{pl_sign}{roi_percentage:.2f}%`")
    except Exception as e: return f"### 📊 Portfolio Summary\n- Error calculating summary: {e}"

# ==============================================================================
# SECTION 2.5: RESILIENT MARKET DATA FETCHING
# ==============================================================================
# ``ccxt.fetch_ohlcv`` (and order placement) implicitly call ``load_markets()``,
# which sorts the markets/currencies dictionaries. When OKX's live feed
# momentarily contains an instrument/currency that ccxt parses with a missing
# symbol/code, that dict gains a ``None`` key and Python's ``sorted()`` raises
# ``'<' not supported between instances of 'NoneType' and 'str'`` — crashing the
# whole run before any price is even read. We can't fix ccxt internals or the
# exchange feed, so we (1) retry, and (2) fall back to OKX's public candles REST
# endpoint, which needs no market metadata at all.
OKX_PUBLIC_CANDLES_URL = "https://www.okx.com/api/v5/market/candles"


def _okx_public_candles(symbol: str, limit: int = 250, bar: str = "1Dutc") -> list:
    """Fetch OHLCV candles directly from OKX's public REST API.

    Returns rows as ``[ts, open, high, low, close, volume]`` sorted oldest-first,
    matching the contract of ``ccxt.fetch_ohlcv`` so the rest of the pipeline is
    unchanged. Rows that cannot be parsed into numbers are skipped rather than
    poisoning the dataset.
    """
    inst_id = symbol.replace("/", "-")
    params = {"instId": inst_id, "bar": bar, "limit": str(limit)}
    response = requests.get(OKX_PUBLIC_CANDLES_URL, params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if str(payload.get("code")) != "0":
        raise ValueError(f"OKX candles API error: code={payload.get('code')} msg={payload.get('msg')}")
    raw = payload.get("data") or []
    rows = []
    for item in raw:
        if not (hasattr(item, "__len__") and len(item) >= 6):
            continue
        try:
            rows.append([
                int(item[0]),
                float(item[1]), float(item[2]), float(item[3]), float(item[4]),
                float(item[5]),
            ])
        except (TypeError, ValueError):
            continue
    rows.sort(key=lambda r: r[0])  # OKX returns newest-first; ccxt yields oldest-first
    return rows


def fetch_ohlcv_resilient(exchange, symbol: str, timeframe: str = "1d", limit: int = 250, retries: int = 3) -> list:
    """Fetch OHLCV via ccxt, retrying then falling back to OKX's public REST API.

    Any ccxt failure — including the ``None``-vs-``str`` ``TypeError`` raised by
    ``load_markets()`` when the exchange feed has a malformed entry — triggers a
    short retry loop and, ultimately, a direct public-API fetch so a transient
    metadata glitch never blocks the daily price read.
    """
    last_error = None
    for attempt in range(retries):
        try:
            data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if isinstance(data, list) and len(data) >= 200:
                return data
            last_error = ValueError(
                f"fetch_ohlcv returned {len(data) if isinstance(data, list) else type(data)} rows"
            )
            print(f"⚠️ ccxt fetch_ohlcv attempt {attempt + 1}/{retries} returned insufficient data: {last_error}")
        except Exception as e:  # noqa: BLE001 - includes the None<str TypeError from load_markets()
            last_error = e
            print(f"⚠️ ccxt fetch_ohlcv attempt {attempt + 1}/{retries} failed: {e}")
        if attempt < retries - 1:
            time.sleep(2 ** attempt)
    print(f"⚠️ Falling back to OKX public candles API after ccxt failures (last error: {last_error}).")
    bar = "1Dutc" if timeframe == "1d" else timeframe
    return _okx_public_candles(symbol, limit=limit, bar=bar)


def ensure_markets_loaded(exchange, retries: int = 3) -> None:
    """Load ccxt markets with retries, forcing a fresh reload after the first try.

    Order placement requires ccxt market metadata. Because the ``None``-key sort
    failure in ``load_markets()`` is driven by transient exchange data, reloading
    a moment later usually succeeds; we surface the error only if it persists.
    """
    last_error = None
    for attempt in range(retries):
        try:
            exchange.load_markets(reload=(attempt > 0))
            return
        except Exception as e:  # noqa: BLE001
            last_error = e
            print(f"⚠️ load_markets attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise last_error


# ==============================================================================
# SECTION 3: CORE LOGIC
# ==============================================================================
def index_growth_estimate(age_days: int) -> float:
    age_days=max(1, age_days); return 10**(5.84*math.log10(age_days)-17.01)
def calculate_continuous_multiplier(x: float) -> float:
    if not math.isfinite(x) or x <= 0: return 1.0
    if x < NEUTRAL_X: return 1.0 + ALPHA * math.log(NEUTRAL_X/x)
    else: return max(0.0, 1.0 - BETA * math.log1p(x-NEUTRAL_X))
def _harmonic_mean(values: np.ndarray) -> float:
    """Return the harmonic mean of positive, finite values.

    The original implementation used ``200/(1/x).sum()`` which worked for
    strictly-positive data but collapsed to zero or ``nan`` when a zero or
    invalid value slipped into the window. That behaviour propagated downstream
    and broke the AHR999 index calculation. We explicitly ignore non-positive or
    non-finite entries so a single bad tick does not poison the rolling mean.
    """

    arr=np.asarray(values, dtype=float)
    mask=np.isfinite(arr) & (arr>0)
    if not mask.any():
        return np.nan
    reciprocal_sum=np.sum(1.0/arr[mask])
    if reciprocal_sum==0:
        return np.nan
    return mask.sum()/reciprocal_sum


def get_today_investment_amount(historical_df: pd.DataFrame, baseline: float) -> dict:
    if "price" not in historical_df.columns:
        print("⚠️ historical_df missing 'price' column.")
        return {"investment_usd": np.nan, "price_today": np.nan, "ahr999_index": np.nan}

    prices=pd.to_numeric(historical_df["price"], errors="coerce")
    valid_prices=prices.dropna()
    if valid_prices.empty:
        print("⚠️ No valid numeric price data after coercion.")
        return {"investment_usd": np.nan, "price_today": np.nan, "ahr999_index": np.nan}

    last_window=valid_prices.tail(200)
    if len(last_window) < 200:
        print(f"⚠️ Insufficient valid numeric price points for 200-day window: {len(last_window)}")
        return {"investment_usd": np.nan, "price_today": valid_prices.iloc[-1], "ahr999_index": np.nan}
    dca200=_harmonic_mean(last_window.to_numpy())
    age_today=(dt.date.today()-GENESIS).days; estimate_today=index_growth_estimate(age_today)
    price_today=valid_prices.iloc[-1]
    if not np.isfinite(dca200) or not np.isfinite(price_today): return {"investment_usd": np.nan, "price_today": price_today, "ahr999_index": np.nan}
    ahr999_today=(price_today/dca200)*(price_today/estimate_today)
    buy_usd_ahr=baseline
    if np.isfinite(ahr999_today):
        if ahr999_today>PAUSE_THRESHOLD: buy_usd_ahr=0.0
        else:
            multiplier=calculate_continuous_multiplier(ahr999_today)
            buy_usd_ahr=baseline*multiplier
            buy_usd_ahr=min(buy_usd_ahr, baseline*DAILY_CAP_X)
    else: buy_usd_ahr = np.nan
    return {"investment_usd": round(buy_usd_ahr, 4) if np.isfinite(buy_usd_ahr) else np.nan, "price_today": price_today, "ahr999_index": ahr999_today}

def main():
    start_time = dt.datetime.now(dt.timezone.utc)
    create_github_issue(f"🚀 Bot Run Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC", "Starting daily investment process...")
    
    final_issue_title = "❓ Bot Run Status Unknown"
    execution_log = ""
    investment_data = {}
    price_now = None
    log_df = None

    try:
        api_key=os.getenv("OKX_API_KEY"); secret_key=os.getenv("OKX_SECRET_KEY"); password=os.getenv("OKX_PASSWORD")
        if not all([api_key, secret_key, password]): raise ValueError("API credentials not found.")
        exchange=ccxt.okx({'apiKey': api_key, 'secret': secret_key, 'password': password, 'options': {'defaultType': 'spot'}})
        print("Fetching historical data...")
        ohlcv=fetch_ohlcv_resilient(exchange, OKX_SYMBOL, '1d', limit=250)
        if not isinstance(ohlcv, list):
            sample=ohlcv if isinstance(ohlcv, (dict, str, bytes, int, float, type(None))) else repr(ohlcv)[:400]
            print(f"⚠️ Unexpected OHLCV payload type from fetch_ohlcv: {type(ohlcv)}")
            print(f"⚠️ OHLCV payload sample: {sample}")
            raise ValueError(f"fetch_ohlcv returned unexpected payload type {type(ohlcv)} with sample {sample}")
        malformed_rows=[row for row in ohlcv if not (hasattr(row, "__len__") and len(row) >= 6)]
        if malformed_rows:
            sample=ohlcv[:5]
            print(f"⚠️ Unexpected OHLCV rows sample (first 5): {sample}")
            raise ValueError(f"fetch_ohlcv returned malformed OHLCV rows (first 5): {sample}")
        if len(ohlcv)<200: raise ValueError(f"Not enough historical data. Got {len(ohlcv)}.")
        historical_df=pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        historical_df['price']=historical_df['close']
        
        investment_data=get_today_investment_amount(historical_df, BASELINE_INVESTMENT)
        investment_amount=investment_data["investment_usd"]; price_now=investment_data["price_today"]

        if investment_amount is not None and math.isfinite(investment_amount) and investment_amount > MIN_TRADE_USD:
            print(f"Placing market buy order to SPEND ${investment_amount}...")
            ensure_markets_loaded(exchange)
            order = exchange.create_market_buy_order_with_cost(OKX_SYMBOL, investment_amount)
            
            final_cost = order.get('cost', 0) or investment_amount
            final_filled = order.get('filled', 0)
            final_average = order.get('average', 0) or price_now
            if not final_filled and final_cost > 0 and final_average > 0: final_filled = final_cost / final_average
            new_log_entry = {'date': dt.date.today().isoformat(), 'buy_usd': final_cost, 'buy_btc': final_filled, 'price_usd': final_average}
            
            final_issue_title = f"✅ Trade Successful: Spent ${new_log_entry['buy_usd']:.2f} on {OKX_SYMBOL}"
            execution_log = f"### 📈 Trade Execution\n- **Status:** `SUCCESS`\n- **Order ID:** `{order.get('id', 'N/A')}`"
        else:
            new_log_entry = {'date': dt.date.today().isoformat(), 'buy_usd': 0.0, 'buy_btc': 0.0, 'price_usd': price_now}
            final_issue_title = f"🟡 Trade Skipped: Amount was `{investment_amount}`"
            execution_log = "### 📈 Trade Execution\n- **Status:** `SKIPPED`"
            print("Investment amount invalid or too small, skipping trade.")

        try:
            existing = pd.read_csv(LOG_FILE)
        except (FileNotFoundError, pd.errors.EmptyDataError):
            existing = pd.DataFrame(columns=LOG_COLUMNS)
        log_df = pd.concat([existing, pd.DataFrame([new_log_entry])], ignore_index=True)
        log_df.to_csv(LOG_FILE, index=False)
        print(f"✅ Appended to {LOG_FILE}: {new_log_entry}")

    except Exception as e:
        final_issue_title = "🔴 TRADE FAILED"
        execution_log = f"### 📈 Trade Execution\n- **Status:** `FAILED`\n\nAn error occurred: \n```\n{e}\n```"
        print(f"🔴🔴🔴 An error occurred: {e} 🔴🔴🔴")

    finally:
        if log_df is None:
            try:
                log_df = pd.read_csv(LOG_FILE)
            except (FileNotFoundError, pd.errors.EmptyDataError):
                log_df = None
        final_log_df = None
        if log_df is not None:
            final_log_df = log_df.dropna(subset=['date'])
            final_log_df = final_log_df[final_log_df['price_usd'] > 0].reset_index(drop=True)

        if price_now and math.isfinite(price_now) and final_log_df is not None and len(final_log_df) > 0:
            portfolio_summary_log = calculate_portfolio_summary(final_log_df, price_now)
            try:
                generate_dashboard_charts(final_log_df, theme_key=os.getenv("DCA_CHART_THEME", DEFAULT_CHART_THEME))
                print("✅ Dashboard charts generated successfully")
            except Exception as e:
                print(f"⚠️ Error generating charts: {e}")
        else:
            portfolio_summary_log = "### 📊 Portfolio Summary\n- Could not fetch current price or no valid data to generate summary."

        market_data_log = (f"### Market Data\n- **Timestamp:** `{start_time.strftime('%Y-%m-%d %H:%M:%S')}` UTC\n"
                           f"- **Price ({OKX_SYMBOL}):** `{price_now}`\n- **AHR999 Index:** `{investment_data.get('ahr999_index', 'N/A')}`")
        decision_log = (f"### 🤖 Investment Decision\n- **Calculated Investment:** `{investment_data.get('investment_usd', 'N/A')}`")

        final_issue_body = "\n\n".join(filter(None, [portfolio_summary_log, market_data_log, decision_log, execution_log]))
        
        end_time = dt.datetime.now(dt.timezone.utc); duration = end_time - start_time
        final_issue_body += f"\n\n---\n*Bot run finished. Duration: `{str(duration).split('.')[0]}`.*"
        create_github_issue(final_issue_title, final_issue_body)
        print(f"\nBot finished at {end_time.isoformat()}")

if __name__ == "__main__":
    main()
