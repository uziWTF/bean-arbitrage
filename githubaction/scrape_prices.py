"""
从多个数据源获取最新期货价格
三层回退机制：akshare → Selenium网页爬取 → 东方财富API
"""

import time
import json
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

# 品种配置
COMMODITIES = [
    {"name": "菜油", "code_akshare": "OI0", "code_eastmoney": "OIM", "url": "https://quote.eastmoney.com/qihuo/OIM.html"},
    {"name": "菜粕", "code_akshare": "RM0", "code_eastmoney": "RMM", "url": "https://quote.eastmoney.com/qihuo/RMM.html"},
    {"name": "豆油", "code_akshare": "Y0", "code_eastmoney": "Ym", "url": "https://quote.eastmoney.com/qihuo/Ym.html"},
    {"name": "豆粕", "code_akshare": "M0", "code_eastmoney": "mm", "url": "https://quote.eastmoney.com/qihuo/mm.html"},
    {"name": "豆一", "code_akshare": "A0", "code_eastmoney": "am", "url": "https://quote.eastmoney.com/qihuo/am.html"},
    {"name": "豆二", "code_akshare": "B0", "code_eastmoney": "bm", "url": "https://quote.eastmoney.com/qihuo/bm.html"},
    {"name": "棕榈油", "code_akshare": "P0", "code_eastmoney": "pm", "url": "https://quote.eastmoney.com/qihuo/pm.html"},
]

COMMODITY_COUNT = len(COMMODITIES)

# ============================================================
# 第一层: akshare
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
# 第二层: Selenium 网页爬取
# ============================================================
def _parse_number(text):
    text = text.strip().replace(",", "")
    try:
        return float(text)
    except Exception:
        return None


def _parse_volume(text):
    text = text.strip()
    try:
        if "万" in text:
            return int(float(text.replace("万", "")) * 10000)
        return int(float(text.replace(",", "")))
    except Exception:
        return None


def _scrape_single_commodity_selenium(driver, c):
    """爬取单个品种的数据，带重试"""
    name = c["name"]
    url = c["url"]
    for attempt in range(2):
        try:
            driver.get(url)
            wait = WebDriverWait(driver, 30)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "brief_info_c")))
            time.sleep(3)

            result = {
                "name": name, "url": url, "date": "",
                "close_price": None, "open_price": None,
                "high": None, "low": None, "prev_settle": None,
                "change": None, "volume": None, "open_interest": None,
            }

            # 日期
            try:
                time_text = driver.find_element(By.CLASS_NAME, "quote_title_l").find_element(By.CLASS_NAME, "quote_title_time").text
                m = re.search(r"(\d{4}-\d{2}-\d{2})", time_text)
                if m:
                    result["date"] = m.group(1)
            except Exception:
                pass

            # 最新价
            try:
                price_text = driver.find_element(By.CLASS_NAME, "zxj").find_element(By.TAG_NAME, "span").text.strip().replace(",", "")
                result["close_price"] = float(price_text)
            except Exception:
                pass

            # 涨跌
            try:
                spans = driver.find_element(By.CLASS_NAME, "zd").find_elements(By.TAG_NAME, "span")
                if spans:
                    result["change"] = float(spans[0].text.strip().replace(",", ""))
            except Exception:
                pass

            # 详细信息
            try:
                tds = driver.find_element(By.CLASS_NAME, "brief_info_c").find_element(By.TAG_NAME, "table").find_elements(By.TAG_NAME, "td")
                for td in tds:
                    text = td.text.strip()
                    try:
                        val = td.find_element(By.TAG_NAME, "span").text.strip()
                    except Exception:
                        continue
                    if "昨结算:" in text:
                        result["prev_settle"] = _parse_number(val)
                    elif "今开:" in text:
                        result["open_price"] = _parse_number(val)
                    elif "最高:" in text:
                        result["high"] = _parse_number(val)
                    elif "最低:" in text:
                        result["low"] = _parse_number(val)
                    elif "成交量:" in text:
                        result["volume"] = _parse_volume(val)
                    elif "持仓量:" in text:
                        result["open_interest"] = _parse_volume(val)
            except Exception:
                pass

            if result["close_price"] is not None:
                print(f"  [Selenium] {name}: {result['date']} 收盘={result['close_price']}")
                return result
            else:
                print(f"  [Selenium] {name}: 第{attempt+1}次未获取到收盘价")
                if attempt == 0:
                    time.sleep(2)

        except Exception as e:
            print(f"  [Selenium] {name}: 第{attempt+1}次失败 - {type(e).__name__}: {e}")
            if attempt == 0:
                time.sleep(2)

    print(f"  [Selenium] {name}: 放弃")
    return None


def scrape_selenium() -> Optional[list]:
    """通过 Selenium 爬取东方财富网页"""
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
    except ImportError:
        print("[Selenium] 未安装，跳过")
        return None

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver = None
    results = []
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)

        for c in COMMODITIES:
            result = _scrape_single_commodity_selenium(driver, c)
            if result:
                results.append(result)
            time.sleep(1)

        if len(results) >= 4:
            return results
        print(f"[Selenium] 仅获取 {len(results)}/{COMMODITY_COUNT} 个品种，不足4个")
        return None

    except Exception as e:
        print(f"[Selenium] 初始化失败: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


# ============================================================
# 第三层: 东方财富 API
# ============================================================
def scrape_eastmoney_api() -> Optional[list]:
    """通过东方财富 push2 API 获取行情"""
    import requests

    results = []
    for c in COMMODITIES:
        name = c["name"]
        code = c["code_eastmoney"]
        for attempt in range(2):
            try:
                url = "https://push2.eastmoney.com/api/qt/stock/get"
                params = {
                    "secid": f"115.{code}",
                    "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f170",
                    "ut": "fa5fd1943c7b386f172d6893dbbd4dd1",
                }
                resp = requests.get(url, params=params, timeout=10)
                data = resp.json().get("data", {})

                if not data or not data.get("f43"):
                    print(f"  [API] {name}: 无数据")
                    break

                # 东财API价格单位为分(除以100)
                close_price = data["f43"] / 100
                high = data.get("f44", 0) / 100 if data.get("f44") else None
                low = data.get("f45", 0) / 100 if data.get("f45") else None
                open_price = data.get("f46", 0) / 100 if data.get("f46") else None
                prev_settle = data.get("f60", 0) / 100 if data.get("f60") else None
                volume = data.get("f47")
                open_interest = data.get("f48")

                change = round(close_price - prev_settle, 2) if prev_settle else None

                results.append({
                    "name": name,
                    "url": c["url"],
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "close_price": close_price,
                    "open_price": open_price,
                    "high": high,
                    "low": low,
                    "prev_settle": prev_settle,
                    "change": change,
                    "volume": volume,
                    "open_interest": open_interest,
                })
                print(f"  [API] {name}: 收盘={close_price}")
                break
            except Exception as e:
                print(f"  [API] {name}: 第{attempt+1}次失败 - {e}")
                if attempt == 0:
                    time.sleep(1)

    if len(results) == COMMODITY_COUNT:
        return results
    if len(results) >= 4:
        print(f"[API] 获取 {len(results)}/{COMMODITY_COUNT} 个品种")
        return results
    print(f"[API] 仅获取 {len(results)} 个品种，不足4个")
    return None


# ============================================================
# 主函数: 三层回退
# ============================================================
def main():
    print("=" * 60)
    print("开始获取期货最新价格")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 第一层: akshare
    print("\n--- 第一层: akshare ---")
    data = scrape_akshare()

    # 第二层: Selenium
    if data is None:
        print("\n--- 第二层: Selenium 网页爬取 ---")
        data = scrape_selenium()

    # 第三层: 东方财富 API
    if data is None:
        print("\n--- 第三层: 东方财富 API ---")
        data = scrape_eastmoney_api()

    if data is None:
        print("\n三层数据源均失败，无法获取数据")
        return

    # 按 COMMODITIES 顺序排序
    order = {c["name"]: i for i, c in enumerate(COMMODITIES)}
    data.sort(key=lambda x: order.get(x["name"], 99))

    # 保存
    output = {
        "scrape_date": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
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