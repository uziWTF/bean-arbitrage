"""
从多个数据源获取最新期货价格
优先使用新浪网页行情接口，akshare 仅作为兜底日频数据源
"""

import time
import json
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

# 品种配置
COMMODITIES = [
    {"name": "菜油", "code_akshare": "OI0", "url": "https://finance.sina.com.cn/futures/quotes/OI0.shtml"},
    {"name": "菜粕", "code_akshare": "RM0", "url": "https://finance.sina.com.cn/futures/quotes/RM0.shtml"},
    {"name": "豆油", "code_akshare": "Y0", "url": "https://finance.sina.com.cn/futures/quotes/Y0.shtml"},
    {"name": "豆粕", "code_akshare": "M0", "url": "https://finance.sina.com.cn/futures/quotes/M0.shtml"},
    {"name": "豆一", "code_akshare": "A0", "url": "https://finance.sina.com.cn/futures/quotes/A0.shtml"},
    {"name": "豆二", "code_akshare": "B0", "url": "https://finance.sina.com.cn/futures/quotes/B0.shtml"},
    {"name": "棕榈油", "code_akshare": "P0", "url": "https://finance.sina.com.cn/futures/quotes/P0.shtml"},
]

COMMODITY_COUNT = len(COMMODITIES)
BJ_TZ = timezone(timedelta(hours=8))


def _now_bj() -> datetime:
    return datetime.now(BJ_TZ)


def is_realtime_preferred_window(now: Optional[datetime] = None) -> bool:
    """在 akshare 容易返回旧日频数据的时段，优先使用实时网页数据源。"""
    now = now or _now_bj()
    minutes = now.hour * 60 + now.minute
    midday_start = 11 * 60 + 30
    midday_end = 13 * 60 + 30
    night_start = 23 * 60
    morning_end = 9 * 60
    return midday_start <= minutes <= midday_end or minutes >= night_start or minutes <= morning_end

# ============================================================
# 第一层: 新浪网页实时行情
# ============================================================
def scrape_sina_realtime() -> Optional[list]:
    """通过新浪行情网页接口获取主连实时数据。"""
    import requests

    symbols = ",".join(f"nf_{c['code_akshare']}" for c in COMMODITIES)
    url = f"https://hq.sinajs.cn/list={symbols}"
    headers = {
        "Referer": "https://finance.sina.com.cn/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    text = ""
    for attempt in range(2):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            text = resp.text
            break
        except Exception as e:
            print(f"[Sina] 第{attempt+1}次请求失败: {e}")
            if attempt == 0:
                time.sleep(2)
    if not text:
        return None

    rows = dict(re.findall(r'var hq_str_nf_([A-Z0-9]+)="([^"]*)";', text))
    results = []

    for c in COMMODITIES:
        name = c["name"]
        symbol = c["code_akshare"]
        raw = rows.get(symbol)
        if not raw:
            print(f"  [Sina] {name}: 无数据")
            continue

        fields = raw.split(",")
        try:
            close_price = float(fields[8])
            open_price = float(fields[2])
            high = float(fields[3])
            low = float(fields[4])
            prev_settle = float(fields[10])
            volume = int(float(fields[13]))
            open_interest = int(float(fields[14]))
            date_str = fields[17] if len(fields) > 17 and fields[17] else _now_bj().strftime("%Y-%m-%d")
            change = round(close_price - prev_settle, 2)
        except Exception as e:
            print(f"  [Sina] {name}: 解析失败 - {e}")
            continue

        results.append({
            "name": name,
            "url": c["url"],
            "date": date_str,
            "close_price": close_price,
            "open_price": open_price,
            "high": high,
            "low": low,
            "prev_settle": prev_settle,
            "change": change,
            "volume": volume,
            "open_interest": open_interest,
        })
        print(f"  [Sina] {name}: {date_str} 最新={close_price}")

    if len(results) == COMMODITY_COUNT:
        return results
    if len(results) >= 4:
        print(f"[Sina] 获取 {len(results)}/{COMMODITY_COUNT} 个品种")
        return results
    print(f"[Sina] 仅获取 {len(results)} 个品种，不足4个")
    return None


# ============================================================
# 第二层: akshare
# ============================================================
def scrape_akshare() -> Optional[list]:
    """通过 akshare 的 futures_main_sina 获取主连数据"""
    try:
        import akshare as ak
    except ImportError:
        print("[akshare] 未安装，跳过")
        return None

    results = []
    failed_names = []
    for c in COMMODITIES:
        name = c["name"]
        symbol = c["code_akshare"]
        for attempt in range(2):
            try:
                df = ak.futures_main_sina(symbol=symbol)
                if df is None or df.empty:
                    print(f"  [akshare] {name}: 无数据")
                    break

                last = df.iloc[-1]
                prev = df.iloc[-2] if len(df) >= 2 else None

                close_price = float(last.iloc[4])
                open_price = float(last.iloc[1])
                high = float(last.iloc[2])
                low = float(last.iloc[3])
                volume = int(last.iloc[5])
                open_interest = int(last.iloc[6])
                settle = float(last.iloc[7]) if len(last) > 7 else close_price
                prev_settle = float(prev.iloc[7]) if prev is not None and len(prev) > 7 else close_price
                change = round(close_price - prev_settle, 2)
                date_str = str(last.iloc[0])

                results.append({
                    "name": name,
                    "url": c["url"],
                    "date": date_str,
                    "close_price": close_price,
                    "open_price": open_price,
                    "high": high,
                    "low": low,
                    "prev_settle": prev_settle,
                    "change": change,
                    "volume": volume,
                    "open_interest": open_interest,
                })
                print(f"  [akshare] {name}: {date_str} 收盘={close_price}")
                break
            except Exception as e:
                print(f"  [akshare] {name}: 第{attempt+1}次失败 - {e}")
                if attempt == 0:
                    time.sleep(2)
                else:
                    failed_names.append(name)

    if len(results) == COMMODITY_COUNT:
        return results

    print(f"[akshare] 获取 {len(results)}/{COMMODITY_COUNT} 个品种")
    if len(results) >= 4:
        print(f"[akshare] 缺少: {failed_names}")
        return results

    print(f"[akshare] 仅获取 {len(results)} 个品种，不足4个，放弃")
    return None


# ============================================================
# 主函数: 数据源按时段回退
# ============================================================
def _run_source(label, scraper):
    print(f"\n--- {label} ---")
    return scraper()


def _resolve_data_date(data: list, now_bj: datetime) -> str:
    dates = [item.get("date") for item in data if item.get("date")]
    if not dates:
        return now_bj.strftime("%Y-%m-%d")
    return max(dates)


def main():
    print("=" * 60)
    print("开始获取期货最新价格")
    now_bj = _now_bj()
    print(f"北京时间: {now_bj.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if is_realtime_preferred_window(now_bj):
        print("当前处于实时优先窗口，优先使用新浪网页行情，避免 akshare 日频旧数据")

    source_order = [
        ("第一层: 新浪网页实时行情", scrape_sina_realtime),
        ("第二层: akshare 日频兜底", scrape_akshare),
    ]

    data = None
    for label, scraper in source_order:
        data = _run_source(label, scraper)
        if data is not None:
            break

    if data is None:
        print("\n所有数据源均失败，无法获取数据")
        return

    # 按 COMMODITIES 顺序排序
    order = {c["name"]: i for i, c in enumerate(COMMODITIES)}
    data.sort(key=lambda x: order.get(x["name"], 99))

    # 保存
    now_bj = _now_bj()
    output = {
        "scrape_date": _resolve_data_date(data, now_bj),
        "scrape_time": now_bj.strftime("%Y-%m-%d %H:%M:%S"),
        "commodities": data,
    }

    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "commodities.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"获取完成! 共 {len(data)} / {len(COMMODITIES)} 个品种")
    print(f"数据已保存到: {output_path}")

    # 检查缺失品种
    fetched_names = {d["name"] for d in data}
    missing = [c["name"] for c in COMMODITIES if c["name"] not in fetched_names]
    if missing:
        print(f"*** 警告: 缺少以下品种数据: {missing} ***")
    print("=" * 60)


if __name__ == "__main__":
    main()
