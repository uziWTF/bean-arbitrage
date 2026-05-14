from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import re
import time
import pandas as pd
from datetime import datetime, timedelta
import os

def check_trading_time():
    """
    检查当前时间是否在交易时间内
    如果不在 15:01-20:00，则提醒数据可能不准
    """
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute

    # 检查是否在 15:01-20:00 之间
    if not ((current_hour == 15 and current_minute >= 1) or (15 < current_hour < 20) or (current_hour == 20 and current_minute == 0)):
        print("\n" + "=" * 60)
        print("警告：当前时间不在 15:01-20:00 之间")
        print("可能处于交易时间，数据不准")
        print("=" * 60 + "\n")
        return False
    return True


def get_excel_path(commodity_name):
    """
    根据商品名称获取对应的 Excel 文件路径
    """
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "processed_data")
    filename = f"{commodity_name}主力合约历史价格数据.xlsx"
    return os.path.join(base_path, filename)


def load_existing_data(excel_path):
    """
    加载现有的 Excel 数据
    """
    if os.path.exists(excel_path):
        try:
            df = pd.read_excel(excel_path)
            return df
        except Exception as e:
            print(f"读取 Excel 文件失败: {e}")
            return None
    else:
        print(f"Excel 文件不存在: {excel_path}")
        return None


def check_previous_trading_day(df, current_date):
    """
    检查上一个交易日的数据是否存在
    """
    if df is None or len(df) == 0:
        return

    # 将日期列转换为 datetime 类型
    df['交易日期'] = pd.to_datetime(df['交易日期'])

    # 获取最后一个交易日
    last_trading_day = df['交易日期'].max()

    # 将当前日期转换为 datetime
    current_datetime = pd.to_datetime(current_date)

    # 计算日期差
    days_diff = (current_datetime - last_trading_day).days

    # 如果差距大于 3 天（考虑周末），提醒缺少数据
    if days_diff > 3:
        print(f"警告：上一个交易日是 {last_trading_day.strftime('%Y-%m-%d')}，距离当前日期 {current_date} 已有 {days_diff} 天")
        print("可能缺少中间的交易日数据")


def format_number_with_comma(value, decimal_places=2):
    """
    格式化数字：添加千位分隔符和固定小数位数
    """
    if value is None or value == '' or value == 'NaN':
        return value

    try:
        # 转换为浮点数
        num = float(str(value).replace(',', ''))

        # 格式化为带千位分隔符和固定小数位数的字符串
        if decimal_places > 0:
            formatted = f"{num:,.{decimal_places}f}"
        else:
            formatted = f"{int(num):,}"

        return formatted
    except:
        return value


def format_data_to_match_existing(data):
    """
    格式化新数据以匹配现有 Excel 文件的格式
    """
    formatted_data = data.copy()

    # 价格字段：保留两位小数，添加千位分隔符
    price_fields = ['前结算价', '开盘价', '最高价', '最低价', '收盘价', '结算价']
    for field in price_fields:
        if field in formatted_data and formatted_data[field]:
            formatted_data[field] = format_number_with_comma(formatted_data[field], 2)

    # 涨跌字段：保留原格式（可能是负数）
    if '涨跌' in formatted_data and formatted_data['涨跌']:
        try:
            val = float(str(formatted_data['涨跌']).replace(',', ''))
            formatted_data['涨跌'] = format_number_with_comma(val, 2)
        except:
            pass

    # 涨跌1：保留为浮点数（原数据中是 float64 类型）
    # 不需要格式化

    # 成交量(手)：整数，添加千位分隔符
    if '成交量(手)' in formatted_data and formatted_data['成交量(手)']:
        formatted_data['成交量(手)'] = format_number_with_comma(formatted_data['成交量(手)'], 0)

    # 持仓量：整数，添加千位分隔符
    if '持仓量' in formatted_data and formatted_data['持仓量']:
        formatted_data['持仓量'] = format_number_with_comma(formatted_data['持仓量'], 0)

    # 持仓量变化：整数，添加千位分隔符（可能是负数）
    if '持仓量变化' in formatted_data and formatted_data['持仓量变化']:
        try:
            val = float(str(formatted_data['持仓量变化']).replace(',', ''))
            formatted_data['持仓量变化'] = format_number_with_comma(val, 0)
        except:
            pass

    # 成交额(万元)：保留两位小数，添加千位分隔符
    if '成交额(万元)' in formatted_data and formatted_data['成交额(万元)']:
        formatted_data['成交额(万元)'] = format_number_with_comma(formatted_data['成交额(万元)'], 2)

    return formatted_data


def update_excel_data(excel_path, new_data, force_update=None):
    """
    更新 Excel 数据（增量更新或覆盖）

    Args:
        excel_path: Excel 文件路径
        new_data: 新数据
        force_update: 是否强制更新（True=更新, False=跳过, None=询问用户）
    """
    # 格式化新数据以匹配现有格式
    formatted_data = format_data_to_match_existing(new_data)

    # 加载现有数据
    df = load_existing_data(excel_path)

    if df is None:
        # 如果文件不存在，创建新的 DataFrame
        df = pd.DataFrame([formatted_data])
        print(f"创建新的数据文件")
    else:
        # 检查上一个交易日数据
        check_previous_trading_day(df, formatted_data['交易日期'])

        # 检查是否已存在该日期的数据
        df['交易日期'] = pd.to_datetime(df['交易日期']).dt.strftime('%Y-%m-%d')
        existing_dates = df['交易日期'].tolist()

        if formatted_data['交易日期'] in existing_dates:
            # 如果 force_update 为 False，跳过更新
            if force_update is False:
                print(f"跳过更新：保留 {formatted_data['交易日期']} 的原有数据")
                return True
            # 如果 force_update 为 True，直接更新
            elif force_update is True:
                print(f"更新数据：{formatted_data['交易日期']} 的数据将被覆盖")
                # 删除旧数据
                df = df[df['交易日期'] != formatted_data['交易日期']]
                # 添加新数据
                df = pd.concat([df, pd.DataFrame([formatted_data])], ignore_index=True)
            # 如果 force_update 为 None，询问用户（保留原有逻辑，但这种情况不应该发生）
            else:
                print(f"\n警告：{formatted_data['交易日期']} 的数据已存在")
                user_input = input("是否需要更新数据？(y/n): ").strip().lower()

                if user_input == 'y' or user_input == 'yes':
                    print(f"更新数据：{formatted_data['交易日期']} 的数据将被覆盖")
                    # 删除旧数据
                    df = df[df['交易日期'] != formatted_data['交易日期']]
                    # 添加新数据
                    df = pd.concat([df, pd.DataFrame([formatted_data])], ignore_index=True)
                else:
                    print(f"跳过更新：保留 {formatted_data['交易日期']} 的原有数据")
                    # 不添加新数据，直接返回
                    return True
        else:
            print(f"添加新数据：{formatted_data['交易日期']}")
            # 添加新数据
            df = pd.concat([df, pd.DataFrame([formatted_data])], ignore_index=True)

        # 按日期排序
        df['交易日期'] = pd.to_datetime(df['交易日期'])
        df = df.sort_values('交易日期')
        df['交易日期'] = df['交易日期'].dt.strftime('%Y-%m-%d')

    # 保存到 Excel
    try:
        df.to_excel(excel_path, index=False)
        print(f"数据已保存到: {excel_path}")
        return True
    except Exception as e:
        print(f"保存 Excel 文件失败: {e}")
        return False


def check_date_exists_in_commodities(commodities, target_date):
    """
    检查目标日期是否在任何品种的数据中已存在

    Args:
        commodities: 品种列表
        target_date: 目标日期（格式：YYYY-MM-DD）

    Returns:
        存在该日期的品种列表
    """
    existing_commodities = []

    for commodity in commodities:
        excel_path = get_excel_path(commodity['name'])
        df = load_existing_data(excel_path)

        if df is not None and len(df) > 0:
            df['交易日期'] = pd.to_datetime(df['交易日期']).dt.strftime('%Y-%m-%d')
            if target_date in df['交易日期'].tolist():
                existing_commodities.append(commodity['name'])

    return existing_commodities


def crawl_futures_data(url, commodity_name):
    """
    使用Selenium从东方财富网爬取期货数据

    Args:
        url: 期货数据页面URL
        commodity_name: 商品名称
    """
    # 配置Chrome选项
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 无头模式
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    driver = None
    try:
        # 初始化浏览器
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)

        # 等待页面加载
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'brief_info_c')))
        time.sleep(2)  # 额外等待确保数据加载完成

        # 初始化数据字典
        data = {
            '商品名称': commodity_name,
            '交易日期': '',
            '合约名称': '',
            '前结算价': '',
            '开盘价': '',
            '最高价': '',
            '最低价': '',
            '收盘价': '',
            '结算价': '',
            '涨跌': '',
            '涨跌1': '',
            '成交量(手)': '',
            '持仓量': '',
            '持仓量变化': '',
            '成交额(万元)': ''
        }

        # 提取交易日期
        try:
            title_div = driver.find_element(By.CLASS_NAME, 'quote_title_l')
            time_span = title_div.find_element(By.CLASS_NAME, 'quote_title_time')
            time_text = time_span.text
            # 提取日期部分，格式如：（2026-02-27 23:00:00）
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', time_text)
            if date_match:
                data['交易日期'] = date_match.group(1)
        except Exception as e:
            print(f"提取交易日期失败: {e}")

        # 提取收盘价
        try:
            close_price_div = driver.find_element(By.CLASS_NAME, 'zxj')
            price_span = close_price_div.find_element(By.TAG_NAME, 'span')
            data['收盘价'] = price_span.text.strip()
        except Exception as e:
            print(f"提取收盘价失败: {e}")

        # 提取涨跌
        try:
            zd_div = driver.find_element(By.CLASS_NAME, 'zd')
            spans = zd_div.find_elements(By.TAG_NAME, 'span')
            if len(spans) >= 1:
                data['涨跌'] = spans[0].text.strip()
        except Exception as e:
            print(f"提取涨跌失败: {e}")

        # 提取brief_info_c中的数据
        try:
            brief_info = driver.find_element(By.CLASS_NAME, 'brief_info_c')
            table = brief_info.find_element(By.TAG_NAME, 'table')
            tds = table.find_elements(By.TAG_NAME, 'td')

            # 用于存储昨收价格，计算涨跌1
            yesterday_close = None

            for td in tds:
                text = td.text.strip()

                # 昨结算 -> 前结算价
                if '昨结算:' in text:
                    try:
                        value = td.find_element(By.TAG_NAME, 'span')
                        data['前结算价'] = value.text.strip()
                    except:
                        pass

                # 今开 -> 开盘价
                elif '今开:' in text:
                    try:
                        value = td.find_element(By.TAG_NAME, 'span')
                        data['开盘价'] = value.text.strip()
                    except:
                        pass

                # 最高 -> 最高价
                elif '最高:' in text:
                    try:
                        value = td.find_element(By.TAG_NAME, 'span')
                        data['最高价'] = value.text.strip()
                    except:
                        pass

                # 最低 -> 最低价
                elif '最低:' in text:
                    try:
                        value = td.find_element(By.TAG_NAME, 'span')
                        data['最低价'] = value.text.strip()
                    except:
                        pass

                # 成交量 -> 成交量(手)
                elif '成交量:' in text:
                    try:
                        value = td.find_element(By.TAG_NAME, 'span')
                        volume_text = value.text.strip()
                        # 处理"万"单位
                        if '万' in volume_text:
                            volume_num = float(volume_text.replace('万', ''))
                            data['成交量(手)'] = str(int(volume_num * 10000))
                        else:
                            data['成交量(手)'] = volume_text
                    except:
                        pass

                # 持仓量
                elif '持仓量:' in text:
                    try:
                        value = td.find_element(By.TAG_NAME, 'span')
                        position_text = value.text.strip()
                        # 处理"万"单位
                        if '万' in position_text:
                            position_num = float(position_text.replace('万', ''))
                            data['持仓量'] = str(int(position_num * 10000))
                        else:
                            data['持仓量'] = position_text
                    except:
                        pass

                # 仓差 -> 持仓量变化
                elif '仓差:' in text:
                    try:
                        value = td.find_element(By.TAG_NAME, 'span')
                        data['持仓量变化'] = value.text.strip()
                    except:
                        pass

                # 成交额 -> 成交额(万元)
                elif '成交额:' in text:
                    try:
                        value = td.find_element(By.TAG_NAME, 'span')
                        amount_text = value.text.strip()
                        # 处理"亿"单位，需要乘以10000转换为万元
                        if '亿' in amount_text:
                            amount_num = float(amount_text.replace('亿', ''))
                            data['成交额(万元)'] = str(amount_num * 10000)
                        elif '万' in amount_text:
                            data['成交额(万元)'] = amount_text.replace('万', '')
                        else:
                            data['成交额(万元)'] = amount_text
                    except:
                        pass

                # 昨收 -> 用于计算涨跌1
                elif '昨收:' in text:
                    try:
                        value = td.find_element(By.TAG_NAME, 'span')
                        yesterday_close = value.text.strip()
                    except:
                        pass

            # 计算涨跌1 = 收盘价 - 昨收
            try:
                if data['收盘价'] and yesterday_close:
                    close_price = float(data['收盘价'])
                    yesterday_close_price = float(yesterday_close)
                    data['涨跌1'] = str(close_price - yesterday_close_price)
            except Exception as e:
                print(f"计算涨跌1失败: {e}")

        except Exception as e:
            print(f"提取brief_info_c数据失败: {e}")

        return data

    except Exception as e:
        print(f"爬取数据时出错: {e}")
        return None

    finally:
        if driver:
            driver.quit()


def main():
    # 检查运行时间
    check_trading_time()

    # 定义要爬取的品种列表
    commodities = [
        {'name': '菜油', 'url': 'https://quote.eastmoney.com/qihuo/OIM.html'},
        {'name': '菜粕', 'url': 'https://quote.eastmoney.com/qihuo/RMM.html'},
        {'name': '豆油', 'url': 'https://quote.eastmoney.com/qihuo/Ym.html'},
        {'name': '豆粕', 'url': 'https://quote.eastmoney.com/qihuo/mm.html'},
        {'name': '豆一', 'url': 'https://quote.eastmoney.com/qihuo/am.html'},
        {'name': '豆二', 'url': 'https://quote.eastmoney.com/qihuo/bm.html'},
        {'name': '棕榈油', 'url': 'https://quote.eastmoney.com/qihuo/pm.html'}
    ]

    print("开始爬取数据...")
    print("=" * 60)

    # 先爬取第一个品种的数据，获取交易日期
    print(f"\n正在爬取 {commodities[0]['name']} 数据以获取交易日期...")
    first_data = crawl_futures_data(commodities[0]['url'], commodities[0]['name'])

    if not first_data or not first_data.get('交易日期'):
        print("无法获取交易日期，程序终止")
        return

    target_date = first_data['交易日期']
    print(f"\n检测到交易日期: {target_date}")

    # 检查该日期是否在任何品种中已存在
    existing_commodities = check_date_exists_in_commodities(commodities, target_date)

    force_update = None  # None=添加新数据, True=更新数据, False=跳过更新

    if existing_commodities:
        print(f"\n警告：以下品种已存在 {target_date} 的数据：")
        for name in existing_commodities:
            print(f"  - {name}")

        user_input = input("\n是否需要更新所有品种的数据？(y/n): ").strip().lower()

        if user_input == 'y' or user_input == 'yes':
            force_update = True
            print("将更新所有品种的数据")
        else:
            force_update = False
            print("跳过更新，保留原有数据")
            print("\n" + "=" * 60)
            print("程序结束")
            print("=" * 60)
            return
    else:
        print(f"\n{target_date} 的数据不存在，将添加新数据")

    print("\n" + "=" * 60)

    # 处理所有品种
    for i, commodity in enumerate(commodities):
        print(f"\n正在处理 {commodity['name']} 数据...")

        # 如果是第一个品种，使用已经爬取的数据
        if i == 0:
            data = first_data
        else:
            data = crawl_futures_data(commodity['url'], commodity['name'])

        if data:
            print(f"{commodity['name']} 数据爬取成功")

            # 输出爬取的数据
            print("\n爬取的数据：")
            for key, value in data.items():
                print(f"  {key}: {value}")

            # 更新到 Excel 文件
            excel_path = get_excel_path(commodity['name'])
            print(f"\n正在更新 Excel 文件...")
            if update_excel_data(excel_path, data, force_update):
                print(f"{commodity['name']} 数据已成功保存")
            else:
                print(f"{commodity['name']} 数据保存失败")
        else:
            print(f"{commodity['name']} 数据爬取失败")

        print("-" * 60)

    print("\n" + "=" * 60)
    print("所有数据处理完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
