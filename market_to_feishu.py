import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime

# --- 配置区 ---
# 建议在 GitHub Actions 中设置环境变量，不要直接把 Webhook 写在代码里
WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK", "这里填写你的飞书Webhook地址")

ASSETS = {
    "美元": "DX-Y.NYB", "2年美债": "^IRX", "10年美债": "^TNX", "TLT": "TLT",
    "标普500": "^GSPC", "纳指": "^IXIC", "道指": "^DJI", "黄金": "GC=F",
    "WTI原油": "CL=F", "VIX": "^VIX", "罗素2000": "^RUT", "比特币": "BTC-USD",
    "科技(XLK)": "XLK", "芯片(SOXX)": "SOXX", "金融(XLF)": "XLF", "医疗(XLV)": "XLV"
}

def get_market_data():
    all_tickers = list(ASSETS.values())
    raw = yf.download(all_tickers, period="2y", interval="1d", progress=False)
    data = raw['Close'] if isinstance(raw.columns, pd.MultiIndex) else raw
    
    today = data.index[-1]
    date_str = today.strftime('%Y-%m-%d')
    
    results = []
    for name, symbol in ASSETS.items():
        try:
            series = data[symbol].dropna()
            curr = series.iloc[-1]
            
            # 计算函数 (收益率算绝对变动，其他算%)
            def calc(old):
                val = (curr - old) if "^" in symbol and "G" not in symbol else (curr / old - 1) * 100
                return round(val, 2)

            results.append({
                "name": name,
                "price": round(curr, 2),
                "d1": calc(series.iloc[-2]),
                "w1": calc(series.iloc[-6]),
                "ytd": calc(series.loc[series.index >= pd.Timestamp(datetime(today.year, 1, 1))].iloc[0])
            })
        except: continue
    return results, date_str

def send_feishu_card(data_list, date_str):
    # 构造卡片内容
    rows = []
    for item in data_list:
        # 根据涨跌选择 emoji 和 颜色
        color = "🟢" if item['d1'] >= 0 else "🔴"
        row_str = f"{color} **{item['name']}**: {item['price']} | 1D: **{item['d1']}%** | YTD: {item['ytd']}%"
        rows.append(row_str)

    # 飞书卡片 JSON 结构
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"📊 美股市场日报 {date_str}"},
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": "\n".join(rows)}
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [{"tag": "plain_text", "content": "数据来源: Yahoo Finance | 自动推送"}]
                }
            ]
        }
    }
    
    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code == 200:
        print("卡片发送成功！")
    else:
        print(f"发送失败: {response.text}")

if __name__ == "__main__":
    results, date_header = get_market_data()
    send_feishu_card(results, date_header)
