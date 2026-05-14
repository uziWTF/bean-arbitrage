"""
数据预处理模块
功能：将原始的期货数据筛选出主力合约月份并筛选历史数据
1. 读取各品种历史数据，分析每个交易日的主力合约（持仓量最大）
2. 每个品种独立分析自己的主力合约月份
3. 形成各品种主力合约历史价格数据
4. 保存结果到processed_data文件夹
"""

import pandas as pd
import os
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def read_all_year_data(data_folder: str, years: List[int]) -> pd.DataFrame:
    """
    读取所有年份的历史数据

    Args:
        data_folder: 数据文件夹路径（A、B、M、Y或P）
        years: 年份列表

    Returns:
        合并后的DataFrame
    """
    all_data = []
    
    for year in years:
        file_path = Path(f"ori_data/{data_folder}/{data_folder.lower()}_{year}.xlsx")
        if file_path.exists():
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
                logger.info(f"成功读取 {file_path}: {len(df)} 条记录")
                all_data.append(df)
            except Exception as e:
                logger.error(f"读取 {file_path} 失败: {e}")
        else:
            logger.warning(f"文件不存在: {file_path}")
    
    if not all_data:
        raise ValueError("没有读取到任何数据")
    
    combined_df = pd.concat(all_data, ignore_index=True)
    logger.info(f"总共读取 {len(combined_df)} 条记录")
    
    return combined_df


def extract_month_from_contract(contract: str) -> str:
    """
    从合约代码中提取月份
    
    Args:
        contract: 合约代码，例如 "b2501", "B2501", "b1501" 等
    
    Returns:
        月份字符串，例如 "2501" 表示2025年1月
    """
    if pd.isna(contract):
        return None
    
    contract_str = str(contract).strip()
    # 移除所有非数字字符，然后取后4位作为月份（YYMM格式）
    digits = ''.join(c for c in contract_str if c.isdigit())
    if len(digits) >= 4:
        return digits[-4:]
    return None


def analyze_main_contract(df: pd.DataFrame) -> Dict[str, str]:
    """
    分析每个交易日的主力合约（持仓量最大的合约）
    
    Args:
        df: 包含日期、合约、持仓量等信息的DataFrame
    
    Returns:
        字典，键为日期字符串，值为主力合约月份
    """
    # 查找日期列
    date_col = None
    contract_col = None
    position_col = None
    
    for col in df.columns:
        col_lower = str(col).lower()
        if '日期' in col_lower or 'date' in col_lower or '时间' in col_lower:
            date_col = col
            break
    
    for col in df.columns:
        col_lower = str(col).lower()
        if '合约' in col_lower or 'contract' in col_lower or '代码' in col_lower:
            contract_col = col
            break
    
    for col in df.columns:
        col_lower = str(col).lower()
        if '持仓' in col_lower or 'position' in col_lower or '持仓量' in col_lower:
            position_col = col
            break
    
    if not date_col:
        raise ValueError("找不到日期列，请检查数据格式")
    if not contract_col:
        raise ValueError("找不到合约列，请检查数据格式")
    if not position_col:
        raise ValueError("找不到持仓量列，请检查数据格式")
    
    logger.info(f"使用列: 日期={date_col}, 合约={contract_col}, 持仓量={position_col}")

    # 转换持仓量列为数值类型
    def convert_position_to_numeric(pos):
        if pd.isna(pos):
            return 0
        pos_str = str(pos).strip().replace(',', '').replace('，', '')
        try:
            return float(pos_str) if pos_str else 0
        except (ValueError, TypeError):
            return 0
    
    df['持仓量_数值'] = df[position_col].apply(convert_position_to_numeric)
    
    # 转换日期列为datetime类型
    if df[date_col].dtype in ['int64', 'int32', 'float64', 'float32']:
        df[date_col] = df[date_col].astype(str).apply(
            lambda x: pd.to_datetime(x, format='%Y%m%d', errors='coerce') if len(str(x)) == 8 else pd.NaT
        )
    else:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    
    df = df[df[date_col].notna()].copy()
    df['合约月份'] = df[contract_col].apply(extract_month_from_contract)
    df = df[df['合约月份'].notna()].copy()
    
    # 按日期和合约月份分组，对持仓量求和
    grouped = df.groupby([date_col, '合约月份'])['持仓量_数值'].sum().reset_index()
    grouped = grouped.sort_values(date_col).reset_index(drop=True)
    
    # 按日期分组，找出每个日期持仓量最大的合约
    main_contracts = {}
    previous_month = None
    
    def month_to_comparable(month_str):
        if not month_str or len(month_str) != 4:
            return 0
        year = int(month_str[:2])
        mon = int(month_str[2:])
        return (2000 + year if year < 50 else 1900 + year) * 100 + mon
    
    for date, group in grouped.groupby(date_col):
        if len(group) == 0:
            continue
        
        max_position = group['持仓量_数值'].max()
        max_position_contracts = group[group['持仓量_数值'] == max_position]
        
        if previous_month is not None:
            prev_comparable = month_to_comparable(previous_month)
            valid_contracts = max_position_contracts[
                max_position_contracts['合约月份'].apply(month_to_comparable) >= prev_comparable
            ]
            
            if len(valid_contracts) > 0:
                comparable_values = valid_contracts['合约月份'].apply(month_to_comparable)
                max_comparable_idx = comparable_values.idxmax()
                main_contract_month = valid_contracts.loc[max_comparable_idx, '合约月份']
            else:
                main_contract_month = previous_month
        else:
            comparable_values = max_position_contracts['合约月份'].apply(month_to_comparable)
            max_comparable_idx = comparable_values.idxmax()
            main_contract_month = max_position_contracts.loc[max_comparable_idx, '合约月份']
        
        main_contracts[date.strftime('%Y-%m-%d')] = main_contract_month
        previous_month = main_contract_month
    
    logger.info(f"分析完成，共 {len(main_contracts)} 个交易日的主力合约")
    
    return main_contracts


def get_main_contract_data(df: pd.DataFrame, main_contracts: Dict[str, str]) -> pd.DataFrame:
    """
    根据主力合约月份筛选历史数据
    
    Args:
        df: 原始数据DataFrame
        main_contracts: 主力合约月份字典（日期 -> 月份）
    
    Returns:
        筛选后的主力合约数据DataFrame
    """
    date_col = None
    contract_col = None
    
    for col in df.columns:
        col_lower = str(col).lower()
        if '日期' in col_lower or 'date' in col_lower or '时间' in col_lower:
            date_col = col
            break
    
    for col in df.columns:
        col_lower = str(col).lower()
        if '合约' in col_lower or 'contract' in col_lower or '代码' in col_lower:
            contract_col = col
            break
    
    if not date_col or not contract_col:
        raise ValueError("找不到必要的列")
    
    # 转换日期列
    if df[date_col].dtype in ['int64', 'int32', 'float64', 'float32']:
        df[date_col] = df[date_col].astype(str).apply(
            lambda x: pd.to_datetime(x, format='%Y%m%d', errors='coerce') if len(str(x)) == 8 else pd.NaT
        )
    else:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    
    df = df[df[date_col].notna()].copy()
    df['合约月份'] = df[contract_col].apply(extract_month_from_contract)
    
    # 筛选主力合约数据
    main_data = []
    for date_str, month in main_contracts.items():
        if month is None:
            continue
        date = pd.to_datetime(date_str)
        day_data = df[(df[date_col].dt.date == date.date()) & (df['合约月份'] == month)]
        if len(day_data) > 0:
            main_data.append(day_data.iloc[0])
    
    result_df = pd.DataFrame(main_data)
    if '合约月份' in result_df.columns:
        result_df = result_df.drop(columns=['合约月份'])
    
    # 格式化日期列
    if date_col in result_df.columns:
        if pd.api.types.is_datetime64_any_dtype(result_df[date_col]):
            result_df[date_col] = pd.to_datetime(result_df[date_col]).dt.strftime('%Y-%m-%d')
        else:
            result_df[date_col] = pd.to_datetime(result_df[date_col], errors='coerce').dt.strftime('%Y-%m-%d')
    
    return result_df


def read_all_year_data_with_year(data_folder: str, years: List[int], file_pattern: str) -> pd.DataFrame:
    """
    读取所有年份的历史数据（用于OI和RM，文件名格式不同）

    Args:
        data_folder: 数据文件夹路径（OI或RM）
        years: 年份列表
        file_pattern: 文件名模式，例如 "OIFUTURES{year}.xlsx"

    Returns:
        合并后的DataFrame，包含年份列
    """
    all_data = []

    for year in years:
        file_path = Path(f"ori_data/{data_folder}/{file_pattern.format(year=year)}")
        if file_path.exists():
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
                # 添加年份列，用于区分重复的合约代码
                df['年份'] = year
                logger.info(f"成功读取 {file_path}: {len(df)} 条记录")
                all_data.append(df)
            except Exception as e:
                logger.error(f"读取 {file_path} 失败: {e}")
        else:
            logger.warning(f"文件不存在: {file_path}")

    if not all_data:
        raise ValueError("没有读取到任何数据")

    combined_df = pd.concat(all_data, ignore_index=True)
    logger.info(f"总共读取 {len(combined_df)} 条记录")

    return combined_df


def extract_month_from_contract_with_year(contract: str, year: int) -> str:
    """
    从合约代码中提取月份（结合年份信息）

    Args:
        contract: 合约代码，例如 "OI501", "RM509" 等
        year: 年份，例如 2015, 2025

    Returns:
        月份字符串，例如 "2501" 表示2025年1月
    """
    if pd.isna(contract) or pd.isna(year):
        return None

    contract_str = str(contract).strip()
    # 移除所有非数字字符
    digits = ''.join(c for c in contract_str if c.isdigit())

    if len(digits) >= 3:
        # 取后3位：第1位是年份个位，后2位是月份
        # 例如：OI501 -> 501，其中5是年份个位（2015或2025），01是月份
        year_digit = digits[-3]  # 年份个位
        month = digits[-2:]  # 月份

        # 根据文件年份确定完整的年份
        year_str = str(year)[-2:]  # 取年份后两位，例如 2015 -> "15", 2025 -> "25"

        return year_str + month

    return None


def analyze_main_contract_with_year(df: pd.DataFrame) -> Dict[str, str]:
    """
    分析每个交易日的主力合约（持仓量最大的合约，用于OI和RM）
    考虑年份信息以处理重复的合约代码

    Args:
        df: 包含日期、合约、持仓量、年份等信息的DataFrame

    Returns:
        字典，键为日期字符串，值为主力合约月份
    """
    # 查找日期列
    date_col = None
    contract_col = None
    position_col = None

    for col in df.columns:
        col_lower = str(col).lower()
        if '日期' in col_lower or 'date' in col_lower or '时间' in col_lower:
            date_col = col
            break

    for col in df.columns:
        col_lower = str(col).lower()
        if '合约' in col_lower or 'contract' in col_lower or '代码' in col_lower or '品种' in col_lower:
            contract_col = col
            break

    for col in df.columns:
        col_lower = str(col).lower()
        if '持仓' in col_lower or 'position' in col_lower or '持仓量' in col_lower:
            position_col = col
            break

    if not date_col:
        raise ValueError("找不到日期列，请检查数据格式")
    if not contract_col:
        raise ValueError("找不到合约列，请检查数据格式")
    if not position_col:
        raise ValueError("找不到持仓量列，请检查数据格式")

    logger.info(f"使用列: 日期={date_col}, 合约={contract_col}, 持仓量={position_col}")

    # 转换持仓量列为数值类型
    def convert_position_to_numeric(pos):
        if pd.isna(pos):
            return 0
        pos_str = str(pos).strip().replace(',', '').replace('，', '')
        try:
            return float(pos_str) if pos_str else 0
        except (ValueError, TypeError):
            return 0

    df['持仓量_数值'] = df[position_col].apply(convert_position_to_numeric)

    # 转换日期列为datetime类型
    if df[date_col].dtype in ['int64', 'int32', 'float64', 'float32']:
        df[date_col] = df[date_col].astype(str).apply(
            lambda x: pd.to_datetime(x, format='%Y%m%d', errors='coerce') if len(str(x)) == 8 else pd.NaT
        )
    else:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

    df = df[df[date_col].notna()].copy()

    # 使用年份信息提取合约月份
    df['合约月份'] = df.apply(
        lambda row: extract_month_from_contract_with_year(row[contract_col], row['年份']),
        axis=1
    )
    df = df[df['合约月份'].notna()].copy()

    # 按日期和合约月份分组，对持仓量求和
    grouped = df.groupby([date_col, '合约月份'])['持仓量_数值'].sum().reset_index()
    grouped = grouped.sort_values(date_col).reset_index(drop=True)

    # 按日期分组，找出每个日期持仓量最大的合约
    main_contracts = {}
    previous_month = None

    def month_to_comparable(month_str):
        if not month_str or len(month_str) != 4:
            return 0
        year = int(month_str[:2])
        mon = int(month_str[2:])
        return (2000 + year if year < 50 else 1900 + year) * 100 + mon

    for date, group in grouped.groupby(date_col):
        if len(group) == 0:
            continue

        max_position = group['持仓量_数值'].max()
        max_position_contracts = group[group['持仓量_数值'] == max_position]

        if previous_month is not None:
            prev_comparable = month_to_comparable(previous_month)
            # 主力合约不应该从较晚的月份切换到较早的月份
            valid_contracts = max_position_contracts[
                max_position_contracts['合约月份'].apply(month_to_comparable) >= prev_comparable
            ]

            if len(valid_contracts) > 0:
                # 选择最远的月份作为主力合约
                comparable_values = valid_contracts['合约月份'].apply(month_to_comparable)
                max_comparable_idx = comparable_values.idxmax()
                main_contract_month = valid_contracts.loc[max_comparable_idx, '合约月份']
            else:
                # 如果没有符合条件的合约，保持上一个主力合约
                main_contract_month = previous_month
        else:
            # 第一天，选择持仓量最大且月份最远的合约
            comparable_values = max_position_contracts['合约月份'].apply(month_to_comparable)
            max_comparable_idx = comparable_values.idxmax()
            main_contract_month = max_position_contracts.loc[max_comparable_idx, '合约月份']

        main_contracts[date.strftime('%Y-%m-%d')] = main_contract_month
        previous_month = main_contract_month

    logger.info(f"分析完成，共 {len(main_contracts)} 个交易日的主力合约")

    return main_contracts


def get_main_contract_data_with_year(df: pd.DataFrame, main_contracts: Dict[str, str]) -> pd.DataFrame:
    """
    根据主力合约月份筛选历史数据（用于OI和RM）

    Args:
        df: 原始数据DataFrame（包含年份列）
        main_contracts: 主力合约月份字典（日期 -> 月份）

    Returns:
        筛选后的主力合约数据DataFrame
    """
    date_col = None
    contract_col = None

    for col in df.columns:
        col_lower = str(col).lower()
        if '日期' in col_lower or 'date' in col_lower or '时间' in col_lower:
            date_col = col
            break

    for col in df.columns:
        col_lower = str(col).lower()
        if '合约' in col_lower or 'contract' in col_lower or '代码' in col_lower or '品种' in col_lower:
            contract_col = col
            break

    if not date_col or not contract_col:
        raise ValueError("找不到必要的列")

    # 转换日期列
    if df[date_col].dtype in ['int64', 'int32', 'float64', 'float32']:
        df[date_col] = df[date_col].astype(str).apply(
            lambda x: pd.to_datetime(x, format='%Y%m%d', errors='coerce') if len(str(x)) == 8 else pd.NaT
        )
    else:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

    df = df[df[date_col].notna()].copy()

    # 使用年份信息提取合约月份
    df['合约月份'] = df.apply(
        lambda row: extract_month_from_contract_with_year(row[contract_col], row['年份']),
        axis=1
    )

    # 筛选主力合约数据
    main_data = []
    for date_str, month in main_contracts.items():
        if month is None:
            continue
        date = pd.to_datetime(date_str)
        day_data = df[(df[date_col].dt.date == date.date()) & (df['合约月份'] == month)]
        if len(day_data) > 0:
            main_data.append(day_data.iloc[0])

    result_df = pd.DataFrame(main_data)

    # 删除辅助列
    if '合约月份' in result_df.columns:
        result_df = result_df.drop(columns=['合约月份'])
    if '年份' in result_df.columns:
        result_df = result_df.drop(columns=['年份'])
    if '持仓量_数值' in result_df.columns:
        result_df = result_df.drop(columns=['持仓量_数值'])

    # 格式化日期列
    if date_col in result_df.columns:
        if pd.api.types.is_datetime64_any_dtype(result_df[date_col]):
            result_df[date_col] = pd.to_datetime(result_df[date_col]).dt.strftime('%Y-%m-%d')
        else:
            result_df[date_col] = pd.to_datetime(result_df[date_col], errors='coerce').dt.strftime('%Y-%m-%d')

    return result_df


def main():
    """主函数"""
    years = list(range(2018, 2027))  # 2018到2026年
    
    logger.info("=" * 60)
    logger.info("开始数据预处理：筛选主力合约历史数据")
    logger.info("=" * 60)
    
    # 创建输出文件夹
    output_dir = Path("processed_data")
    output_dir.mkdir(exist_ok=True)
    logger.info(f"输出文件夹: {output_dir}")
    
    # 1. 读取豆二历史数据并分析主力合约
    logger.info("\n步骤1: 读取豆二历史数据并分析主力合约")
    b_data = read_all_year_data("B", years)
    logger.info(f"豆二数据列: {b_data.columns.tolist()}")

    b_main_contracts = analyze_main_contract(b_data)

    # 保存豆二主力合约月份记录
    b_main_contract_df = pd.DataFrame([
        {"日期": date, "主力合约月份": month}
        for date, month in sorted(b_main_contracts.items())
    ])
    output_path1 = output_dir / "豆二主力合约月份记录.xlsx"
    b_main_contract_df.to_excel(output_path1, index=False, engine='openpyxl')
    logger.info(f"豆二主力合约月份记录已保存到: {output_path1}")

    # 提取豆二主力合约历史价格数据
    b_main_data = get_main_contract_data(b_data, b_main_contracts)
    output_path2 = output_dir / "豆二主力合约历史价格数据.xlsx"
    b_main_data.to_excel(output_path2, index=False, engine='openpyxl')
    logger.info(f"豆二主力合约数据已保存，共 {len(b_main_data)} 条记录")

    # 2. 读取豆粕历史数据并分析主力合约
    logger.info("\n步骤2: 读取豆粕历史数据并分析主力合约")
    m_data = read_all_year_data("M", years)
    logger.info(f"豆粕数据列: {m_data.columns.tolist()}")

    m_main_contracts = analyze_main_contract(m_data)

    # 保存豆粕主力合约月份记录
    m_main_contract_df = pd.DataFrame([
        {"日期": date, "主力合约月份": month}
        for date, month in sorted(m_main_contracts.items())
    ])
    output_path_m1 = output_dir / "豆粕主力合约月份记录.xlsx"
    m_main_contract_df.to_excel(output_path_m1, index=False, engine='openpyxl')
    logger.info(f"豆粕主力合约月份记录已保存到: {output_path_m1}")

    # 提取豆粕主力合约历史价格数据
    m_main_data = get_main_contract_data(m_data, m_main_contracts)
    output_path3 = output_dir / "豆粕主力合约历史价格数据.xlsx"
    m_main_data.to_excel(output_path3, index=False, engine='openpyxl')
    logger.info(f"豆粕主力合约数据已保存，共 {len(m_main_data)} 条记录")

    # 3. 读取豆一历史数据并分析主力合约
    logger.info("\n步骤3: 读取豆一历史数据并分析主力合约")
    a_data = read_all_year_data("A", years)
    logger.info(f"豆一数据列: {a_data.columns.tolist()}")

    a_main_contracts = analyze_main_contract(a_data)

    # 保存豆一主力合约月份记录
    a_main_contract_df = pd.DataFrame([
        {"日期": date, "主力合约月份": month}
        for date, month in sorted(a_main_contracts.items())
    ])
    output_path_a1 = output_dir / "豆一主力合约月份记录.xlsx"
    a_main_contract_df.to_excel(output_path_a1, index=False, engine='openpyxl')
    logger.info(f"豆一主力合约月份记录已保存到: {output_path_a1}")

    # 提取豆一主力合约历史价格数据
    a_main_data = get_main_contract_data(a_data, a_main_contracts)
    output_path4 = output_dir / "豆一主力合约历史价格数据.xlsx"
    a_main_data.to_excel(output_path4, index=False, engine='openpyxl')
    logger.info(f"豆一主力合约数据已保存，共 {len(a_main_data)} 条记录")

    # 4. 读取豆油历史数据并分析主力合约
    logger.info("\n步骤4: 读取豆油历史数据并分析主力合约")
    y_data = read_all_year_data("Y", years)
    logger.info(f"豆油数据列: {y_data.columns.tolist()}")

    y_main_contracts = analyze_main_contract(y_data)

    # 保存豆油主力合约月份记录
    y_main_contract_df = pd.DataFrame([
        {"日期": date, "主力合约月份": month}
        for date, month in sorted(y_main_contracts.items())
    ])
    output_path_y1 = output_dir / "豆油主力合约月份记录.xlsx"
    y_main_contract_df.to_excel(output_path_y1, index=False, engine='openpyxl')
    logger.info(f"豆油主力合约月份记录已保存到: {output_path_y1}")

    # 提取豆油主力合约历史价格数据
    y_main_data = get_main_contract_data(y_data, y_main_contracts)
    output_path5 = output_dir / "豆油主力合约历史价格数据.xlsx"
    y_main_data.to_excel(output_path5, index=False, engine='openpyxl')
    logger.info(f"豆油主力合约数据已保存，共 {len(y_main_data)} 条记录")

    # 5. 读取棕榈油（P）历史数据并分析主力合约
    logger.info("\n步骤5: 读取棕榈油（P）历史数据并分析主力合约")
    p_data = read_all_year_data("P", years)
    logger.info(f"棕榈油数据列: {p_data.columns.tolist()}")

    # 分析棕榈油的主力合约
    p_main_contracts = analyze_main_contract(p_data)

    # 保存棕榈油主力合约月份记录
    p_main_contract_df = pd.DataFrame([
        {"日期": date, "主力合约月份": month}
        for date, month in sorted(p_main_contracts.items())
    ])
    output_path_p1 = output_dir / "棕榈油主力合约月份记录.xlsx"
    p_main_contract_df.to_excel(output_path_p1, index=False, engine='openpyxl')
    logger.info(f"棕榈油主力合约月份记录已保存到: {output_path_p1}")

    # 提取棕榈油主力合约历史价格数据
    p_main_data = get_main_contract_data(p_data, p_main_contracts)
    output_path_p2 = output_dir / "棕榈油主力合约历史价格数据.xlsx"
    p_main_data.to_excel(output_path_p2, index=False, engine='openpyxl')
    logger.info(f"棕榈油主力合约数据已保存，共 {len(p_main_data)} 条记录")

    # 6. 读取菜油（OI）历史数据并分析主力合约
    logger.info("\n步骤6: 读取菜油（OI）历史数据并分析主力合约")
    oi_data = read_all_year_data_with_year("OI", years, "OIFUTURES{year}.xlsx")
    logger.info(f"菜油数据列: {oi_data.columns.tolist()}")

    # 分析菜油的主力合约
    oi_main_contracts = analyze_main_contract_with_year(oi_data)

    # 保存菜油主力合约月份记录
    oi_main_contract_df = pd.DataFrame([
        {"日期": date, "主力合约月份": month}
        for date, month in sorted(oi_main_contracts.items())
    ])
    output_path6 = output_dir / "菜油主力合约月份记录.xlsx"
    oi_main_contract_df.to_excel(output_path6, index=False, engine='openpyxl')
    logger.info(f"菜油主力合约月份记录已保存到: {output_path6}")

    # 提取菜油主力合约历史价格数据
    oi_main_data = get_main_contract_data_with_year(oi_data, oi_main_contracts)
    output_path7 = output_dir / "菜油主力合约历史价格数据.xlsx"
    oi_main_data.to_excel(output_path7, index=False, engine='openpyxl')
    logger.info(f"菜油主力合约数据已保存，共 {len(oi_main_data)} 条记录")

    # 7. 读取菜粕（RM）历史数据并分析主力合约
    logger.info("\n步骤7: 读取菜粕（RM）历史数据并分析主力合约")
    rm_data = read_all_year_data_with_year("RM", years, "RMFUTURES{year}.xlsx")
    logger.info(f"菜粕数据列: {rm_data.columns.tolist()}")

    # 分析菜粕的主力合约
    rm_main_contracts = analyze_main_contract_with_year(rm_data)

    # 保存菜粕主力合约月份记录
    rm_main_contract_df = pd.DataFrame([
        {"日期": date, "主力合约月份": month}
        for date, month in sorted(rm_main_contracts.items())
    ])
    output_path8 = output_dir / "菜粕主力合约月份记录.xlsx"
    rm_main_contract_df.to_excel(output_path8, index=False, engine='openpyxl')
    logger.info(f"菜粕主力合约月份记录已保存到: {output_path8}")

    # 提取菜粕主力合约历史价格数据
    rm_main_data = get_main_contract_data_with_year(rm_data, rm_main_contracts)
    output_path9 = output_dir / "菜粕主力合约历史价格数据.xlsx"
    rm_main_data.to_excel(output_path9, index=False, engine='openpyxl')
    logger.info(f"菜粕主力合约数据已保存，共 {len(rm_main_data)} 条记录")

    logger.info("\n" + "=" * 60)
    logger.info("数据预处理完成！")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

