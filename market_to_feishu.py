import yfinance as yf
import pandas as pd
import requests
import os
import sys
from datetime import datetime

# --- 配置 ---
WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK")

# 缩减资产列表，确保在手机窄屏上也能完美对齐
ASSETS = {
    "标普500": "^GSPC", "纳指100": "^NDX", "道琼斯": "^DJI", "罗素2000": "^RUT",
    "10年美债": "^TNX", "2年美债": "^IRX", "美元指数": "DX-Y.NYB", "TLT(债)": "TLT",
    "现货黄金": "GC=F", "WTI原油": "CL=F", "比特币": "BTC-USD",
    "半导体": "SOXX", "科技股": "XLK", "金融股": "XLF", "医疗股": "XLV"
}

def get_data():
    try:
        raw = yf.download(list(ASSETS.values()), period="2y", interval="1d", progress=False)
        data = raw['Close'] if isinstance(raw.columns, pd.MultiIndex) else raw
        today = data.index[-1]
        
        results = []
        ytd_start = pd.Timestamp(datetime(today.year, 1, 1))
        
        for name, sym in ASSETS.items():
            s = data[sym].dropna()
            curr = s.iloc[-1]
            # 变动计算逻辑：债收益率算点数，其他算百分比
            is_yield = "^" in sym and sym not in ["^GSPC", "^NDX", "^DJI", "^RUT"]
            
            def calc(old):
                val = (curr - old) if is_yield else (curr/old - 1)*100
                return val

            results.append({
                "name": name,
                "price": f"{curr:.1f}" if curr > 100 else f"{curr:.2f}",
                "d1": calc(s.iloc[-2]),
                "ytd": calc(s.loc[s.index >= ytd_start].iloc[0])
            })
        return results, today.strftime('%Y-%m-%d')
    except Exception as e:
        print(f"数据抓取失败: {e}")
        return None, None

def build_card(data_list, date_str):
    # 分成三列：资产名、收盘价、涨跌幅(1D/YTD合并)
    col_names = []
    col_prices = []
    col_changes = []

    for item in data_list:
        emoji = "🟩" if item['d1'] >= 0 else "🟥"
        col_names.append(f"{item['name']}")
        col_prices.append(f"**{item['price']}**")
        col_changes.append(f"{emoji} {item['d1']:+.1f}% | {item['ytd']:+.1f}%")

    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"📊 美股日报 {date_str}"},
                "template": "blue" # 蓝色页眉
            },
            "elements": [
                {
                    "tag": "column_set",
                    "flex_mode": "stretch",
                    "columns": [
                        {
                            "tag": "column", "width": "weighted", "weight": 1,
                            "elements": [{"tag": "markdown", "content": "\n".join(col_names)}]
                        },
                        {
                            "tag": "column", "width": "weighted", "weight": 1,
                            "elements": [{"tag": "markdown", "content": "\n".join(col_prices)}]
                        },
                        {
                            "tag": "column", "width": "weighted", "weight": 2,
                            "elements": [{"tag": "markdown", "content": "\n".join(col_changes)}]
                        }
                    ]
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [{"tag": "plain_text", "content": "列说明：资产 | 现价 | 当日涨跌% | YTD%"}]
                }
            ]
        }
    }
    return payload

if __name__ == "__main__":
    results, date_header = get_data()
    if results:
        card = build_card(results, date_header)
        r = requests.post(WEBHOOK_URL, json=card)
        print(f"发送结果: {r.status_code}")
    else:
        sys.exit(1)
