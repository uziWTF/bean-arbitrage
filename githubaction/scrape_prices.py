"""
从东方财富网抓取最新期货价格
基于 豆类/05_update_data.py 重写，适配 GitHub Actions
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import re
import time
import json
import os
from pathlib import Path
from datetime import datetime


# 品种配置
COMMODITIES = [
    {"name": "菜油", "url": "https://quote.eastmoney.com/qihuo/OIM.html"},
    {"name": "菜粕", "url": "https://quote.eastmoney.com/qihuo/RMM.html"},
    {"name": "豆油", "url": "https://quote.eastmoney.com/qihuo/Ym.html"},
    {"name": "豆粕", "url": "https://quote.eastmoney.com/qihuo/mm.html"},
    {"name": "豆一", "url": "https://quote.eastmoney.com/qihuo/am.html"},
    {"name": "豆二", "url": "https://quote.eastmoney.com/qihuo/bm.html"},
    {"name": "棕榈油", "url": "https://quote.eastmoney.com/qihuo/pm.html"},
]


def create_driver():
    """创建 Chrome WebDriver"""
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

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    return driver


def scrape_commodity(driver, commodity):
    """抓取单个品种的最新价格"""
    name = commodity["name"]
    url = commodity["url"]

    try:
        driver.get(url)

        # 等待页面加载
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "brief_info_c")))
        time.sleep(2)

        result = {
            "name": name,
            "url": url,
            "date": "",
            "close_price": None,
            "open_price": None,
            "high": None,
            "low": None,
            "prev_settle": None,
            "change": None,
            "volume": None,
            "open_interest": None,
        }

        # 提取交易日期
        try:
            title_div = driver.find_element(By.CLASS_NAME, "quote_title_l")
            time_span = title_div.find_element(By.CLASS_NAME, "quote_title_time")
            time_text = time_span.text
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", time_text)
            if date_match:
                result["date"] = date_match.group(1)
        except Exception as e:
            print(f"  [{name}] 提取交易日期失败: {e}")

        # 提取最新价（收盘价）
        try:
            close_div = driver.find_element(By.CLASS_NAME, "zxj")
            price_span = close_div.find_element(By.TAG_NAME, "span")
            price_text = price_span.text.strip().replace(",", "")
            result["close_price"] = float(price_text)
        except Exception as e:
            print(f"  [{name}] 提取最新价失败: {e}")

        # 提取涨跌
        try:
            zd_div = driver.find_element(By.CLASS_NAME, "zd")
            spans = zd_div.find_elements(By.TAG_NAME, "span")
            if spans:
                change_text = spans[0].text.strip().replace(",", "")
                result["change"] = float(change_text)
        except Exception as e:
            print(f"  [{name}] 提取涨跌失败: {e}")

        # 提取详细信息
        try:
            brief_info = driver.find_element(By.CLASS_NAME, "brief_info_c")
            table = brief_info.find_element(By.TAG_NAME, "table")
            tds = table.find_elements(By.TAG_NAME, "td")

            for td in tds:
                text = td.text.strip()
                try:
                    value_span = td.find_element(By.TAG_NAME, "span")
                    value_text = value_span.text.strip()
                except:
                    continue

                if "昨结算:" in text:
                    result["prev_settle"] = _parse_number(value_text)
                elif "今开:" in text:
                    result["open_price"] = _parse_number(value_text)
                elif "最高:" in text:
                    result["high"] = _parse_number(value_text)
                elif "最低:" in text:
                    result["low"] = _parse_number(value_text)
                elif "成交量:" in text:
                    result["volume"] = _parse_volume(value_text)
                elif "持仓量:" in text:
                    result["open_interest"] = _parse_volume(value_text)

        except Exception as e:
            print(f"  [{name}] 提取详细信息失败: {e}")

        return result

    except Exception as e:
        print(f"  [{name}] 抓取失败: {e}")
        return None


def _parse_number(text):
    """解析数字文本"""
    text = text.strip().replace(",", "")
    try:
        return float(text)
    except:
        return None


def _parse_volume(text):
    """解析成交量/持仓量（处理万单位）"""
    text = text.strip()
    try:
        if "万" in text:
            num = float(text.replace("万", ""))
            return int(num * 10000)
        else:
            return int(float(text.replace(",", "")))
    except:
        return None


def main():
    print("=" * 60)
    print("开始抓取东方财富网期货最新价格")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    driver = None
    try:
        driver = create_driver()
        commodities_data = []

        for commodity in COMMODITIES:
            print(f"\n正在抓取 {commodity['name']}...")
            result = scrape_commodity(driver, commodity)
            if result:
                commodities_data.append(result)
                print(f"  成功: {result['date']} 最新价={result['close_price']}")
            else:
                print(f"  失败")
            time.sleep(1)  # 避免请求过快

        # 保存到JSON
        output = {
            "scrape_date": datetime.now().strftime("%Y-%m-%d"),
            "commodities": commodities_data,
        }

        output_dir = Path(__file__).parent / "data"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / "commodities.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n{'=' * 60}")
        print(f"抓取完成! 共 {len(commodities_data)} 个品种")
        print(f"数据已保存到: {output_path}")
        print("=" * 60)

    except Exception as e:
        print(f"\n错误: {e}")
        raise
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()
