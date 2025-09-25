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
import json
import math
import datetime as dt
import requests
import pandas as pd
import numpy as np
import ccxt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ==============================================================================
# SECTION 1: FINAL STRATEGY PARAMETERS (Unchanged)
# ==============================================================================
BASELINE_INVESTMENT = 5.0
OKX_SYMBOL = "BTC/USDT"
GENESIS = dt.date(2009, 1, 3)
ALPHA = 1.5
BETA = 0.8
DAILY_CAP_X = 4.0
PAUSE_THRESHOLD = 2.0
NEUTRAL_X = 1.0
LOG_FILE = "trade_log.csv"

# ==============================================================================
# SECTION 2: HELPERS (Now includes multiple chart functions)
# ==============================================================================
def create_github_issue(title: str, body: str):
    # (This function is perfect and remains unchanged)
    repo_slug=os.getenv("GITHUB_REPOSITORY"); token=os.getenv("GITHUB_TOKEN")
    if not repo_slug or not token: return
    url=f"https://api.github.com/repos/{repo_slug}/issues"
    headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    payload={"title": title, "body": body}
    try:
        response=requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code != 201: print(f"Failed to create GitHub issue: {response.status_code} {response.text}")
    except Exception as e: print(f"Error creating GitHub issue: {e}")

# --- NEW: Charting Sub-functions ---
def _plot_roi_curve(ax, df):
    ax.plot(df['date'], df['roi'] * 100, label="Portfolio ROI", color='dodgerblue')
    ax.axhline(0, color='grey', linewidth=0.8, linestyle='--')
    ax.set_title("1. Return on Investment (ROI)", fontsize=16)
    ax.set_ylabel("ROI (%)")
    ax.yaxis.set_major_formatter(plt.FuncFormatter('{:.0f}%'.format))

def _plot_equity_curve(ax, df):
    ax.plot(df['date'], df['value_usd'], label="Portfolio Value", color='green')
    ax.set_title("2. Portfolio Equity Curve", fontsize=16)
    ax.set_ylabel("Portfolio Value (USD)")
    ax.yaxis.set_major_formatter(plt.FuncFormatter('${:,.0f}'.format))

def _plot_value_vs_cost(ax, df):
    ax.plot(df['date'], df['value_usd'], label="Portfolio Value", color='green')
    ax.plot(df['date'], df['invest_cum'], label="Cumulative Cost", color='red', linestyle='--')
    ax.fill_between(df['date'], df['invest_cum'], df['value_usd'], 
                    where=df['value_usd'] >= df['invest_cum'], 
                    facecolor='green', alpha=0.3, interpolate=True)
    ax.fill_between(df['date'], df['invest_cum'], df['value_usd'], 
                    where=df['value_usd'] < df['invest_cum'], 
                    facecolor='red', alpha=0.3, interpolate=True)
    ax.set_title("3. Portfolio Value vs. Cumulative Cost", fontsize=16)
    ax.set_ylabel("Amount (USD)")
    ax.yaxis.set_major_formatter(plt.FuncFormatter('${:,.0f}'.format))

def generate_dashboard_charts(log_df: pd.DataFrame):
    if log_df is None or len(log_df) < 2:
        print("Not enough data to generate charts.")
        return
    
    try:
        df = log_df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df['invest_cum'] = df['buy_usd'].cumsum()
        df['hold_btc_cum'] = df['buy_btc'].cumsum()
        df['value_usd'] = df['hold_btc_cum'] * df['price_usd']
        df['roi'] = (df['value_usd'] / df['invest_cum'] - 1).fillna(0)

        plt.style.use('seaborn-v0_8-darkgrid')
        
        # --- Plot 1: ROI Curve (Saves to roi_chart.png) ---
        fig1, ax1 = plt.subplots(figsize=(12, 7))
        _plot_roi_curve(ax1, df)
        ax1.legend(); ax1.grid(True, which='both', linestyle=':')
        fig1.autofmt_xdate(); plt.tight_layout()
        plt.savefig("roi_chart.png", dpi=120); plt.close(fig1)
        print(f"✅ Chart generated: roi_chart.png")

        # --- Plot 2: Equity Curve (Saves to equity_curve.png) ---
        fig2, ax2 = plt.subplots(figsize=(12, 7))
        _plot_equity_curve(ax2, df)
        ax2.legend(); ax2.grid(True, which='both', linestyle=':')
        fig2.autofmt_xdate(); plt.tight_layout()
        plt.savefig("equity_curve.png", dpi=120); plt.close(fig2)
        print(f"✅ Chart generated: equity_curve.png")

        # --- Plot 3: Value vs Cost (Saves to value_vs_cost.png) ---
        fig3, ax3 = plt.subplots(figsize=(12, 7))
        _plot_value_vs_cost(ax3, df)
        ax3.legend(); ax3.grid(True, which='both', linestyle=':')
        fig3.autofmt_xdate(); plt.tight_layout()
        plt.savefig("value_vs_cost.png", dpi=120); plt.close(fig3)
        print(f"✅ Chart generated: value_vs_cost.png")

    except Exception as e:
        print(f"Could not generate dashboard charts: {e}")


def calculate_portfolio_summary(log_df: pd.DataFrame, current_price: float) -> str:
    # (This function is perfect and remains unchanged)
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
# SECTION 3: CORE LOGIC (Unchanged, it is robust)
# ==============================================================================
# (This entire section is correct and remains unchanged)
def index_growth_estimate(age_days: int) -> float:
    age_days=max(1, age_days); return 10**(5.84*math.log10(age_days)-17.01)
def calculate_continuous_multiplier(x: float) -> float:
    if not math.isfinite(x) or x <= 0: return 1.0
    if x < NEUTRAL_X: return 1.0 + ALPHA * math.log(NEUTRAL_X/x)
    else: return max(0.0, 1.0 - BETA * math.log1p(x-NEUTRAL_X))
def get_today_investment_amount(historical_df: pd.DataFrame, baseline: float) -> dict:
    prices=historical_df["price"].astype(float)
    dca200=prices.rolling(window=200, min_periods=200).apply(lambda x: 200/(1/x).sum(), raw=True).iloc[-1]
    age_today=(dt.date.today()-GENESIS).days; estimate_today=index_growth_estimate(age_today)
    price_today=prices.iloc[-1]
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

    try:
        api_key=os.getenv("OKX_API_KEY"); secret_key=os.getenv("OKX_SECRET_KEY"); password=os.getenv("OKX_PASSWORD")
        if not all([api_key, secret_key, password]): raise ValueError("API credentials not found.")
        exchange=ccxt.okx({'apiKey': api_key, 'secret': secret_key, 'password': password, 'options': {'defaultType': 'spot'}})
        print("Fetching historical data...")
        ohlcv=exchange.fetch_ohlcv(OKX_SYMBOL, '1d', limit=250)
        if len(ohlcv)<200: raise ValueError(f"Not enough historical data. Got {len(ohlcv)}.")
        historical_df=pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        historical_df['price']=historical_df['close']
        
        investment_data=get_today_investment_amount(historical_df, BASELINE_INVESTMENT)
        investment_amount=investment_data["investment_usd"]; price_now=investment_data["price_today"]

        if investment_amount is not None and math.isfinite(investment_amount) and investment_amount > 1:
            print(f"Placing market buy order to SPEND ${investment_amount}...")
            order = exchange.create_market_buy_order_with_cost(OKX_SYMBOL, investment_amount)
            
            final_cost = order.get('cost', 0) or investment_amount
            final_filled = order.get('filled', 0)
            final_average = order.get('average', 0) or price_now
            if not final_filled and final_cost > 0 and final_average > 0: final_filled = final_cost / final_average
            new_log_entry = {'date': dt.date.today().isoformat(), 'buy_usd': final_cost, 'buy_btc': final_filled, 'price_usd': final_average}
            
            try:
                log_df = pd.read_csv(LOG_FILE) if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0 else pd.DataFrame()
                log_df = pd.concat([log_df, pd.DataFrame([new_log_entry])], ignore_index=True)
                log_df.to_csv(LOG_FILE, index=False)
                print(f"✅ Appended transaction to {LOG_FILE}: {new_log_entry}")
            except Exception as e: print(f"Error while updating CSV log: {e}")
            
            final_issue_title = f"✅ Trade Successful: Spent ${new_log_entry['buy_usd']:.2f} on {OKX_SYMBOL}"
            execution_log = f"### 📈 Trade Execution\n- **Status:** `SUCCESS`\n- **Order ID:** `{order.get('id', 'N/A')}`"
        else:
            final_issue_title = f"🟡 Trade Skipped: Amount was `{investment_amount}`"
            execution_log = f"### 📈 Trade Execution\n- **Status:** `SKIPPED`"
            print("Investment amount invalid or too small, skipping trade.")

    except Exception as e:
        final_issue_title = f"🔴 TRADE FAILED"
        execution_log = f"### 📈 Trade Execution\n- **Status:** `FAILED`\n\nAn error occurred: \n```\n{e}\n```"
        print(f"🔴🔴🔴 An error occurred: {e} 🔴🔴🔴")
    
    finally:
        final_log_df = None
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0:
            final_log_df = pd.read_csv(LOG_FILE)
            
        if price_now and math.isfinite(price_now):
            portfolio_summary_log = calculate_portfolio_summary(final_log_df, price_now)
            generate_dashboard_charts(final_log_df) # Call the new main charting function
        else:
            portfolio_summary_log = "### 📊 Portfolio Summary\n- Could not fetch current price to generate summary."

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
