# trade_bot.py (The correct, non-interactive version for GitHub Actions)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Investment Bot for OKX with Persistent Logging & Charting
----------------------------------------------------------------
This bot executes a personalized AHR999 strategy, logs every transaction
to a CSV file in the repo, and regenerates an ROI chart after each run.
This version is designed for non-interactive, automated execution.
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
# SECTION 1: FINAL STRATEGY PARAMETERS
# ==============================================================================
BASELINE_INVESTMENT = 5.0
OKX_SYMBOL = "BTC/USDT"
GENESIS = dt.date(2009, 1, 3)
ALPHA = 1.5
BETA = 0.8
DAILY_CAP_X = 4.0
PULSE_THRESHOLD = 0.45
PAUSE_THRESHOLD = 2.0
NEUTRAL_X = 1.0
LOG_FILE = "trade_log.csv"
CHART_FILE = "roi_chart.png"

# ==============================================================================
# SECTION 2: GITHUB & CHARTING HELPERS
# ==============================================================================
def create_github_issue(title: str, body: str):
    repo_slug = os.getenv("GITHUB_REPOSITORY"); token = os.getenv("GITHUB_TOKEN")
    if not repo_slug or not token:
        print("Skipping issue creation: GitHub credentials not found.")
        return
    url = f"https://api.github.com/repos/{repo_slug}/issues"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    payload = {"title": title, "body": body}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 201:
            print(f"Successfully created GitHub issue: '{title}'")
        else:
            print(f"Failed to create GitHub issue. Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"An error occurred while creating GitHub issue: {e}")

def generate_roi_chart():
    if not os.path.exists(LOG_FILE):
        print("Log file not found, skipping chart generation.")
        return
    log_df = pd.read_csv(LOG_FILE)
    if len(log_df) < 2:
        print("Not enough data to generate a chart.")
        return
    log_df['date'] = pd.to_datetime(log_df['date'])
    log_df['invest_cum'] = log_df['buy_usd'].cumsum()
    log_df['hold_btc_cum'] = log_df['buy_btc'].cumsum()
    log_df['value_usd'] = log_df['hold_btc_cum'] * log_df['price_usd']
    log_df['roi'] = log_df['value_usd'] / log_df['invest_cum'] - 1
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.plot(log_df['date'], log_df['roi'] * 100, label="Portfolio ROI", color='dodgerblue')
    ax.axhline(0, color='grey', linewidth=0.8, linestyle='--')
    ax.set_title(f"Portfolio Return on Investment (ROI) - Last Updated: {dt.date.today().isoformat()}", fontsize=16)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Return on Investment (%)", fontsize=12)
    ax.yaxis.set_major_formatter(plt.FuncFormatter('{:.0f}%'.format))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    fig.autofmt_xdate()
    ax.grid(True, which='both', linestyle=':')
    ax.legend()
    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=120)
    print(f"✅ Successfully generated and saved ROI chart to {CHART_FILE}")
    plt.close()

# ==============================================================================
# SECTION 3: CORE LOGIC
# ==============================================================================
def index_growth_estimate(age_days: int) -> float:
    age_days = max(1, age_days)
    return 10 ** (5.84 * math.log10(age_days) - 17.01)

def calculate_continuous_multiplier(x: float) -> float:
    if not math.isfinite(x) or x <= 0: return 1.0
    if x < NEUTRAL_X:
        return 1.0 + ALPHA * math.log(NEUTRAL_X / x)
    else:
        return max(0.0, 1.0 - BETA * math.log1p(x - NEUTRAL_X))

def get_today_investment_amount(historical_df: pd.DataFrame, baseline: float) -> dict:
    prices = historical_df["price"].astype(float)
    dca200 = prices.rolling(window=200, min_periods=200).apply(lambda x: 200 / (1 / x).sum(), raw=True).iloc[-1]
    age_today = (dt.date.today() - GENESIS).days
    estimate_today = index_growth_estimate(age_today)
    price_today = prices.iloc[-1]
    ahr999_today = (price_today / dca200) * (price_today / estimate_today) if dca200 > 0 else np.nan
    buy_usd_ahr = baseline
    if np.isfinite(ahr999_today):
        if ahr999_today > PAUSE_THRESHOLD:
            buy_usd_ahr = 0.0
        else:
            multiplier = calculate_continuous_multiplier(ahr999_today)
            buy_usd_ahr = baseline * multiplier
            if ahr999_today < PULSE_THRESHOLD:
                buy_usd_ahr += baseline
            buy_usd_ahr = min(buy_usd_ahr, baseline * DAILY_CAP_X)
    return {
        "investment_usd": round(buy_usd_ahr, 4),
        "price_today": price_today,
        "ahr999_index": ahr999_today
    }

def main():
    start_time = dt.datetime.now(dt.timezone.utc)
    create_github_issue(
        f"🚀 Bot Run Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"Starting daily investment process..."
    )

    final_issue_title = "❓ Bot Run Status Unknown"
    final_issue_body = "The bot run did not complete as expected."

    try:
        api_key = os.getenv("OKX_API_KEY"); secret_key = os.getenv("OKX_SECRET_KEY"); password = os.getenv("OKX_PASSWORD")
        if not all([api_key, secret_key, password]):
            raise ValueError("API credentials not found.")

        exchange = ccxt.okx({'apiKey': api_key, 'secret': secret_key, 'password': password, 'options': {'defaultType': 'spot'}})
        
        print("Fetching historical data...")
        ohlcv = exchange.fetch_ohlcv(OKX_SYMBOL, '1d', limit=250)
        if len(ohlcv) < 200:
            raise ValueError(f"Not enough historical data. Got {len(ohlcv)}.")
        historical_df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        historical_df['price'] = historical_df['close']
        
        investment_data = get_today_investment_amount(historical_df, BASELINE_INVESTMENT)
        investment_amount = investment_data["investment_usd"]
        price_now = investment_data["price_today"]
        
        decision_log = (
            f"### Market Data\n"
            f"- **Current Price ({OKX_SYMBOL}):** ${price_now}\n"
            f"- **AHR999 Index:** {investment_data['ahr999_index']:.4f}\n\n"
            f"### Investment Decision\n"
            f"- **Calculated Investment:** `${investment_amount}`"
        )
        
        if investment_amount > 1:
            print(f"Placing market buy order for ${investment_amount}...")
            order = exchange.create_market_buy_order(OKX_SYMBOL, investment_amount)
            
            log_entry = {
                'date': dt.date.today().isoformat(),
                'buy_usd': order.get('cost', investment_amount),
                'buy_btc': order.get('filled', (investment_amount / price_now)),
                'price_usd': order.get('average', price_now)
            }
            header = not os.path.exists(LOG_FILE)
            pd.DataFrame([log_entry]).to_csv(LOG_FILE, mode='a', header=header, index=False)
            print(f"✅ Appended transaction to {LOG_FILE}")
            
            final_issue_title = f"✅ Trade Successful: Bought ${log_entry['buy_usd']:.2f} of {OKX_SYMBOL}"
            final_issue_body = f"{decision_log}\n\n### Trade Execution: `SUCCESS`\n- **Order ID:** `{order['id']}`"
        else:
            print("Investment amount too small, skipping trade and logging.")
            final_issue_title = f"🟡 Trade Skipped: Amount was ${investment_amount}"
            final_issue_body = f"{decision_log}\n\n### Trade Execution: `SKIPPED`"

    except Exception as e:
        final_issue_title = f"🔴 TRADE FAILED"
        final_issue_body = f"An error occurred: \n```\n{e}\n```"
        print(f"🔴🔴🔴 An error occurred: {e} 🔴🔴🔴")

    finally:
        generate_roi_chart()
        end_time = dt.datetime.now(dt.timezone.utc)
        duration = end_time - start_time
        final_issue_body += f"\n\n---\n*Bot run finished. Duration: `{str(duration).split('.')[0]}`.*"
        create_github_issue(final_issue_title, final_issue_body)
        
        print(f"\nBot finished at {end_time.isoformat()}")

if __name__ == "__main__":
    main()
