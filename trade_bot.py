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
from scipy.interpolate import make_interp_spline

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
        "palette": {
            "roi": "#4F46E5",
            "value": "#059669",
            "cost": "#D97706",
            "positive_fill": "#10B981",
            "negative_fill": "#EF4444"
        },
        "rc": {
            "font.family": "DejaVu Sans",
            "axes.titlesize": 18,
            "axes.labelsize": 13,
            "axes.titlecolor": "#1E293B",
            "axes.labelcolor": "#1E293B",
            "axes.edgecolor": "#CBD5F5",
            "xtick.color": "#334155",
            "ytick.color": "#334155",
            "grid.color": "#F1F5F9",
            "legend.frameon": True
        },
        "figure_facecolor": "#FFFFFF",
        "axes_facecolor": "#FFFFFF",
        "legend_facecolor": "#FFFFFF"
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
            "font.family": "DejaVu Sans",
            "axes.titlesize": 18,
            "axes.labelsize": 13,
            "axes.titlecolor": "#0F172A",
            "axes.labelcolor": "#1E293B",
            "axes.edgecolor": "#CBD5F5",
            "xtick.color": "#334155",
            "ytick.color": "#334155",
            "grid.color": "#E2E8F0",
            "legend.frameon": True
        },
        "figure_facecolor": "#F8FAFC",
        "axes_facecolor": "#FFFFFF",
        "legend_facecolor": "#FFFFFF"
    },
    "midnight": {
        "label": "Midnight Dashboard",
        "style": "seaborn-v0_8-darkgrid",
        "palette": {
            "roi": "#60A5FA",
            "value": "#34D399",
            "cost": "#FBBF24",
            "positive_fill": "#059669",
            "negative_fill": "#F87171"
        },
        "rc": {
            "font.family": "DejaVu Sans",
            "axes.titlesize": 18,
            "axes.labelsize": 13,
            "axes.titlecolor": "#E2E8F0",
            "axes.labelcolor": "#CBD5F5",
            "axes.edgecolor": "#1F2937",
            "xtick.color": "#94A3B8",
            "ytick.color": "#94A3B8",
            "grid.color": "#1F2937",
            "legend.frameon": True
        },
        "figure_facecolor": "#0F172A",
        "axes_facecolor": "#111827",
        "legend_facecolor": "#1F2937"
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
            "font.family": "DejaVu Sans",
            "axes.titlesize": 18,
            "axes.labelsize": 13,
            "axes.titlecolor": "#F8FAFC",
            "axes.labelcolor": "#E0F2FE",
            "axes.edgecolor": "#312E81",
            "xtick.color": "#C7D2FE",
            "ytick.color": "#C7D2FE",
            "grid.color": "#1E1B4B",
            "legend.frameon": True
        },
        "figure_facecolor": "#0B1120",
        "axes_facecolor": "#111827",
        "legend_facecolor": "#1E1B4B"
    }
}


def _resolve_chart_theme(theme_key):
    key = (theme_key or DEFAULT_CHART_THEME).lower().strip()
    if key not in CHART_THEMES:
        print(f"⚠️ Unknown chart theme '{theme_key}', falling back to '{DEFAULT_CHART_THEME}'.")
        key = DEFAULT_CHART_THEME
    return key, CHART_THEMES[key]

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

# --- NEW: Charting Sub-functions ---
def _smooth_curve(x, y, num_points=500):
    """使用样条插值创建平滑曲线"""
    if len(x) < 4:  # 样条插值至少需要4个点
        return x, y
    try:
        # 将日期转换为数值以便插值
        x_num = mdates.date2num(x)
        # 创建样条插值
        spl = make_interp_spline(x_num, y, k=min(3, len(x)-1))
        # 生成平滑的x值
        x_smooth_num = np.linspace(x_num.min(), x_num.max(), num_points)
        # 计算平滑的y值
        y_smooth = spl(x_smooth_num)
        # 将数值转回日期
        x_smooth = mdates.num2date(x_smooth_num)
        return x_smooth, y_smooth
    except Exception:
        return x, y

def _plot_roi_curve(ax, df, palette):
    # 平滑ROI曲线
    x_smooth, y_smooth = _smooth_curve(df['date'], df['roi'] * 100)
    
    # 绘制平滑曲线，增加渐变效果
    ax.plot(x_smooth, y_smooth, label="Portfolio ROI", color=palette['roi'], linewidth=2.8, alpha=0.9)
    
    # 添加所有原始数据点作为标记
    ax.scatter(df['date'], df['roi'] * 100, 
               color=palette['roi'], s=40, alpha=0.6, zorder=5, edgecolors='white', linewidths=0.5)
    
    # 填充正负区域
    ax.fill_between(x_smooth, 0, y_smooth, where=(np.array(y_smooth)>=0), 
                     facecolor=palette['positive_fill'], alpha=0.15, interpolate=True)
    ax.fill_between(x_smooth, 0, y_smooth, where=(np.array(y_smooth)<0), 
                     facecolor=palette['negative_fill'], alpha=0.15, interpolate=True)
    
    # 零线
    ax.axhline(0, color='grey', linewidth=1.2, linestyle='--', alpha=0.5)
    
    ax.set_title("1. Return on Investment (ROI)", fontsize=18, pad=15, fontweight='bold')
    ax.set_ylabel("ROI (%)", fontsize=14)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0f}%'))

def _plot_equity_curve(ax, df, palette):
    # 平滑权益曲线
    x_smooth, y_smooth = _smooth_curve(df['date'], df['value_usd'])
    
    # 绘制平滑曲线
    ax.plot(x_smooth, y_smooth, label="Portfolio Value", color=palette['value'], linewidth=2.8, alpha=0.9)
    
    # 添加所有数据点标记
    ax.scatter(df['date'], df['value_usd'], 
               color=palette['value'], s=40, alpha=0.6, zorder=5, edgecolors='white', linewidths=0.5)
    
    # 添加渐变填充效果
    ax.fill_between(x_smooth, 0, y_smooth, facecolor=palette['value'], alpha=0.1)
    
    # 添加阴影效果
    ax.plot(x_smooth, y_smooth, color=palette['value'], linewidth=6, alpha=0.1, zorder=1)
    
    ax.set_title("2. Portfolio Equity Curve", fontsize=18, pad=15, fontweight='bold')
    ax.set_ylabel("Portfolio Value (USD)", fontsize=14)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'${y:,.0f}'))

def _plot_value_vs_cost(ax, df, palette):
    # 平滑价值曲线和成本曲线
    x_smooth, y_value_smooth = _smooth_curve(df['date'], df['value_usd'])
    _, y_cost_smooth = _smooth_curve(df['date'], df['invest_cum'])
    
    # 绘制平滑曲线
    ax.plot(x_smooth, y_value_smooth, label="Portfolio Value", color=palette['value'], linewidth=2.8, alpha=0.9)
    ax.plot(x_smooth, y_cost_smooth, label="Cumulative Cost", color=palette['cost'], linewidth=2.8, alpha=0.9, linestyle='-')
    
    # 添加所有数据点标记
    ax.scatter(df['date'], df['value_usd'], 
               color=palette['value'], s=40, alpha=0.6, zorder=5, edgecolors='white', linewidths=0.5)
    ax.scatter(df['date'], df['invest_cum'], 
               color=palette['cost'], s=40, alpha=0.6, zorder=5, edgecolors='white', linewidths=0.5)
    
    # 填充盈亏区域（使用平滑数据）
    ax.fill_between(x_smooth, y_cost_smooth, y_value_smooth, 
                    where=(np.array(y_value_smooth) >= np.array(y_cost_smooth)), 
                    facecolor=palette['positive_fill'], alpha=0.25, interpolate=True, label='Profit Area')
    ax.fill_between(x_smooth, y_cost_smooth, y_value_smooth, 
                    where=(np.array(y_value_smooth) < np.array(y_cost_smooth)), 
                    facecolor=palette['negative_fill'], alpha=0.25, interpolate=True, label='Loss Area')
    
    # 添加阴影效果
    ax.plot(x_smooth, y_value_smooth, color=palette['value'], linewidth=6, alpha=0.08, zorder=1)
    ax.plot(x_smooth, y_cost_smooth, color=palette['cost'], linewidth=6, alpha=0.08, zorder=1)
    
    ax.set_title("3. Portfolio Value vs. Cumulative Cost", fontsize=18, pad=15, fontweight='bold')
    ax.set_ylabel("Amount (USD)", fontsize=14)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'${y:,.0f}'))

def _plot_daily_investment(ax, df, palette):
    baseline = df['buy_usd'].median()

    # 平滑投资额曲线
    x_smooth, y_smooth = _smooth_curve(df['date'], df['buy_usd'])
    
    # 绘制投资额曲线
    ax.plot(x_smooth, y_smooth, label="Daily Investment", color=palette['cost'], linewidth=2.8, alpha=0.9)
    
    # 添加所有数据点
    ax.scatter(df['date'], df['buy_usd'], 
               color=palette['cost'], s=40, alpha=0.6, zorder=5, edgecolors='white', linewidths=0.5)
    
    # 添加基准线
    ax.axhline(baseline, color='grey', linewidth=1.5, linestyle='--', alpha=0.6, label=f'Baseline (${baseline:.2f})')
    
    # 填充高于/低于基准的区域
    ax.fill_between(x_smooth, baseline, y_smooth, 
                    where=(np.array(y_smooth) >= baseline), 
                    facecolor=palette['cost'], alpha=0.15, interpolate=True, label='Above Baseline')
    ax.fill_between(x_smooth, baseline, y_smooth, 
                    where=(np.array(y_smooth) < baseline), 
                    facecolor=palette['negative_fill'], alpha=0.15, interpolate=True, label='Below Baseline')
    
    ax.set_title("4. Daily Investment Amount", fontsize=18, pad=15, fontweight='bold')
    ax.set_ylabel("Investment (USD)", fontsize=14)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'${y:.2f}'))

def _plot_btc_accumulation(ax, df, palette):
    # 平滑BTC累计曲线
    x_smooth, y_smooth = _smooth_curve(df['date'], df['hold_btc_cum'])
    
    # 绘制BTC累计曲线
    ax.plot(x_smooth, y_smooth, label="BTC Holdings", color=palette['roi'], linewidth=2.8, alpha=0.9)
    
    # 添加所有数据点
    ax.scatter(df['date'], df['hold_btc_cum'], 
               color=palette['roi'], s=40, alpha=0.6, zorder=5, edgecolors='white', linewidths=0.5)
    
    # 添加渐变填充
    ax.fill_between(x_smooth, 0, y_smooth, facecolor=palette['roi'], alpha=0.15)
    
    # 添加阴影效果
    ax.plot(x_smooth, y_smooth, color=palette['roi'], linewidth=6, alpha=0.1, zorder=1)
    
    ax.set_title("5. BTC Accumulation Over Time", fontsize=18, pad=15, fontweight='bold')
    ax.set_ylabel("BTC Amount", fontsize=14)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.6f}'))

def _plot_avg_cost_vs_price(ax, df, palette):
    # 计算平均成本
    df['avg_cost'] = df['invest_cum'] / df['hold_btc_cum']
    
    # 平滑曲线
    x_smooth, y_price_smooth = _smooth_curve(df['date'], df['price_usd'])
    _, y_cost_smooth = _smooth_curve(df['date'], df['avg_cost'])
    
    # 绘制价格和平均成本
    ax.plot(x_smooth, y_price_smooth, label="BTC Price", color=palette['value'], linewidth=2.8, alpha=0.9)
    ax.plot(x_smooth, y_cost_smooth, label="Average Cost", color=palette['cost'], linewidth=2.8, alpha=0.9)
    
    # 添加所有数据点
    ax.scatter(df['date'], df['price_usd'], 
               color=palette['value'], s=40, alpha=0.6, zorder=5, edgecolors='white', linewidths=0.5)
    ax.scatter(df['date'], df['avg_cost'], 
               color=palette['cost'], s=40, alpha=0.6, zorder=5, edgecolors='white', linewidths=0.5)
    
    # 填充盈亏区域
    ax.fill_between(x_smooth, y_cost_smooth, y_price_smooth,
                    where=(np.array(y_price_smooth) >= np.array(y_cost_smooth)),
                    facecolor=palette['positive_fill'], alpha=0.2, interpolate=True, label='In Profit')
    ax.fill_between(x_smooth, y_cost_smooth, y_price_smooth,
                    where=(np.array(y_price_smooth) < np.array(y_cost_smooth)),
                    facecolor=palette['negative_fill'], alpha=0.2, interpolate=True, label='In Loss')
    
    ax.set_title("6. BTC Price vs. Average Cost", fontsize=18, pad=15, fontweight='bold')
    ax.set_ylabel("Price (USD)", fontsize=14)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'${y:,.0f}'))

def _plot_strategy_comparison(ax, df, palette):
    # 计算普通定投（固定金额）
    baseline = df['buy_usd'].median()
    df['regular_dca_cost'] = baseline * np.arange(1, len(df) + 1)
    df['regular_dca_btc'] = (baseline / df['price_usd']).cumsum()
    df['regular_dca_value'] = df['regular_dca_btc'] * df['price_usd']
    df['regular_roi'] = (df['regular_dca_value'] / df['regular_dca_cost'] - 1).fillna(0)
    
    # 平滑曲线
    x_smooth, y_smart_smooth = _smooth_curve(df['date'], df['roi'] * 100)
    _, y_regular_smooth = _smooth_curve(df['date'], df['regular_roi'] * 100)
    
    # 绘制两种策略的ROI
    ax.plot(x_smooth, y_smart_smooth, label="Smart DCA (AHR999)", color=palette['roi'], linewidth=2.8, alpha=0.9)
    ax.plot(x_smooth, y_regular_smooth, label="Regular DCA (Fixed)", color=palette['cost'], linewidth=2.8, alpha=0.9, linestyle='--')
    
    # 添加所有数据点
    ax.scatter(df['date'], df['roi'] * 100, 
               color=palette['roi'], s=40, alpha=0.6, zorder=5, edgecolors='white', linewidths=0.5)
    ax.scatter(df['date'], df['regular_roi'] * 100, 
               color=palette['cost'], s=40, alpha=0.6, zorder=5, edgecolors='white', linewidths=0.5)
    
    # 填充优势区域
    ax.fill_between(x_smooth, y_regular_smooth, y_smart_smooth,
                    where=(np.array(y_smart_smooth) >= np.array(y_regular_smooth)),
                    facecolor=palette['positive_fill'], alpha=0.15, interpolate=True, label='Smart DCA Advantage')
    ax.fill_between(x_smooth, y_regular_smooth, y_smart_smooth,
                    where=(np.array(y_smart_smooth) < np.array(y_regular_smooth)),
                    facecolor=palette['negative_fill'], alpha=0.15, interpolate=True, label='Regular DCA Advantage')
    
    # 零线
    ax.axhline(0, color='grey', linewidth=1.2, linestyle='--', alpha=0.5)
    
    ax.set_title("7. Strategy Comparison: Smart vs Regular DCA", fontsize=18, pad=15, fontweight='bold')
    ax.set_ylabel("ROI (%)", fontsize=14)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0f}%'))

def _finalize_axis(ax, legend_face, fontsize=10, ncol=1):
    ax.legend(facecolor=legend_face, framealpha=0.9, edgecolor='none', fontsize=fontsize, loc='best', ncol=ncol)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')


def _style_axes(ax, theme_config: dict):
    axes_face = theme_config.get("axes_facecolor")
    if axes_face:
        ax.set_facecolor(axes_face)
    
    # 美化边框
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1.2)
        spine.set_color(theme_config.get("rc", {}).get("axes.edgecolor", "#CBD5F5"))
    
    # 增强网格效果
    ax.grid(True, which='major', linestyle='-', linewidth=0.8, alpha=0.3)
    ax.grid(True, which='minor', linestyle=':', linewidth=0.5, alpha=0.2)
    ax.minorticks_on()
    
    # 设置刻度样式
    ax.tick_params(axis='both', which='major', labelsize=11, length=6, width=1.2)
    ax.tick_params(axis='both', which='minor', length=3, width=0.8)
    
    # 添加水印
    ax.text(0.5, 0.5, 'Github @xunyoyo', 
            transform=ax.transAxes, fontsize=20, color='gray',
            alpha=0.15, ha='center', va='center', rotation=30, zorder=0)


def generate_dashboard_charts(log_df: pd.DataFrame, theme_key=None):
    if log_df is None or len(log_df) == 0:
        print("⚠️ No data to generate charts.")
        return
    
    try:
        df = log_df.dropna(subset=['date', 'price_usd'])
        df = df[(df['price_usd'] > 0) & (df['buy_usd'] > 0)].reset_index(drop=True).copy()

        if df.empty:
            print("⚠️ No investment data yet. Charts will be generated after first trade.")
            return

        df['date'] = pd.to_datetime(df['date'])
        df['invest_cum'] = df['buy_usd'].cumsum()
        df['hold_btc_cum'] = df['buy_btc'].cumsum()
        df['value_usd'] = df['hold_btc_cum'] * df['price_usd']
        df['roi'] = (df['value_usd'] / df['invest_cum'] - 1).fillna(0)

        theme_key, theme_config = _resolve_chart_theme(theme_key)
        palette = theme_config['palette']
        figure_face = theme_config.get("figure_facecolor", "white")
        legend_face = theme_config.get("legend_facecolor", figure_face)
        rc_override = theme_config.get("rc", {})

        style_context = plt.style.context(theme_config.get("style", "seaborn-v0_8-darkgrid"))
        with plt.rc_context(rc_override):
            with style_context:
                # 创建综合仪表盘 - 4行2列布局，顶部留出空间给统计信息
                fig = plt.figure(figsize=(24, 30), dpi=150)
                fig.patch.set_facecolor(figure_face)
                
                # 添加总标题
                fig.suptitle('DCA Investment Dashboard - AHR999 Strategy', fontsize=28, fontweight='bold', y=0.988)
                
                # 计算关键统计数据
                total_invested = df['invest_cum'].iloc[-1]
                total_btc = df['hold_btc_cum'].iloc[-1]
                current_value = df['value_usd'].iloc[-1]
                avg_cost = total_invested / total_btc if total_btc > 0 else 0.0
                current_price = df['price_usd'].iloc[-1]
                total_profit = current_value - total_invested
                roi_pct = (total_profit / total_invested) * 100 if total_invested > 0 else 0.0
                
                # 计算普通定投对比
                baseline = df['buy_usd'].median()
                regular_invested = baseline * len(df)
                regular_btc = (baseline / df['price_usd']).sum()
                regular_value = regular_btc * current_price
                regular_profit = regular_value - regular_invested
                regular_roi = (regular_profit / regular_invested) * 100
                
                # 策略优势
                strategy_advantage = roi_pct - regular_roi
                profit_advantage = total_profit - regular_profit
                
                # 添加统计信息面板 - 居中显示，带双横线
                stats_y = 0.965
                
                # 上横线
                fig.text(0.5, stats_y + 0.002, '─' * 220, ha='center', fontsize=8, color='gray', alpha=0.5)
                
                # 第一行统计数据 - 居中对齐布局
                col1_x = 0.12
                fig.text(col1_x, stats_y - 0.012, 'Investment:', fontsize=13, fontweight='bold', color=palette['roi'], ha='center')
                fig.text(col1_x, stats_y - 0.025, f'${total_invested:,.2f}', fontsize=11, ha='center')
                fig.text(col1_x, stats_y - 0.036, f'{len(df)} days', fontsize=10, alpha=0.8, ha='center')
                
                col2_x = 0.28
                fig.text(col2_x, stats_y - 0.012, 'Holdings:', fontsize=13, fontweight='bold', color=palette['roi'], ha='center')
                fig.text(col2_x, stats_y - 0.025, f'{total_btc:.6f} BTC', fontsize=11, ha='center')
                fig.text(col2_x, stats_y - 0.036, f'${current_value:,.2f}', fontsize=10, alpha=0.8, ha='center')
                
                col3_x = 0.46
                profit_color = palette['value'] if total_profit >= 0 else palette['negative_fill']
                fig.text(col3_x, stats_y - 0.012, 'Performance:', fontsize=13, fontweight='bold', color=profit_color, ha='center')
                fig.text(col3_x, stats_y - 0.025, f'{roi_pct:+.2f}% ROI', fontsize=11, fontweight='bold', color=profit_color, ha='center')
                fig.text(col3_x, stats_y - 0.036, f'${total_profit:+,.2f}', fontsize=10, color=profit_color, ha='center')
                
                col4_x = 0.62
                fig.text(col4_x, stats_y - 0.012, 'Price:', fontsize=13, fontweight='bold', color=palette['cost'], ha='center')
                fig.text(col4_x, stats_y - 0.025, f'${current_price:,.0f}', fontsize=11, ha='center')
                fig.text(col4_x, stats_y - 0.036, f'Avg: ${avg_cost:,.0f}', fontsize=10, alpha=0.8, ha='center')
                
                col5_x = 0.80
                adv_color = palette['value'] if strategy_advantage >= 0 else palette['negative_fill']
                fig.text(col5_x, stats_y - 0.012, 'vs Regular DCA:', fontsize=13, fontweight='bold', color=palette['roi'], ha='center')
                fig.text(col5_x, stats_y - 0.025, f'{roi_pct:.2f}% vs {regular_roi:.2f}%', fontsize=11, ha='center')
                fig.text(col5_x, stats_y - 0.036, f'{strategy_advantage:+.2f}% ({profit_advantage:+,.0f})', fontsize=10, 
                        fontweight='bold', color=adv_color, ha='center')
                
                # 下横线
                fig.text(0.5, stats_y - 0.045, '─' * 220, ha='center', fontsize=8, color='gray', alpha=0.5)
                
                # 创建子图 - 图表进一步下移
                gs = fig.add_gridspec(4, 2, hspace=0.35, wspace=0.25, top=0.88, bottom=0.02, left=0.06, right=0.94)
                
                panels = [
                    (gs[0, 0], _plot_roi_curve, {}),
                    (gs[0, 1], _plot_equity_curve, {}),
                    (gs[1, 0], _plot_value_vs_cost, {}),
                    (gs[1, 1], _plot_daily_investment, {}),
                    (gs[2, 0], _plot_btc_accumulation, {}),
                    (gs[2, 1], _plot_avg_cost_vs_price, {}),
                    (gs[3, :], _plot_strategy_comparison, {"fontsize": 11, "ncol": 2}),
                ]
                for spec, plot_fn, finalize_kwargs in panels:
                    ax = fig.add_subplot(spec)
                    _style_axes(ax, theme_config)
                    plot_fn(ax, df, palette)
                    _finalize_axis(ax, legend_face, **finalize_kwargs)
                
                # 保存综合仪表盘
                output_dashboard = "dashboard_comprehensive.png"
                plt.savefig(output_dashboard, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
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
