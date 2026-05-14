"""
品种对比值/差值回归时间测试模块
功能：测试不同品种对的价格比值或差值从指定值1回归到值2所需的时间
支持的品种对：
1. 豆一与豆二
2. 豆粕与豆油
3. 豆粕与菜粕
4. 豆油与菜油
5. 菜粕与菜油
6. 豆油与棕榈油
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== 配置区域 ====================
# 使用说明：
# 1. 修改 PAIR_SELECTION 选择要分析的品种对（1-6）
# 2. 修改 METRIC_TYPE 选择分析指标类型（'ratio' 或 'diff'）
# 3. 修改 ENTRY_VALUE 设置入场值（开始持仓的值）
# 4. 修改 EXIT_VALUE 设置出场值（目标回归值）
# 5. 运行脚本：conda run -n graph-rag-agent-master python 04_test_ratio_reversion_time.py

# 品种对选择（可选值：1-6）
# 1: 豆一与豆二, 2: 豆粕与豆油, 3: 豆粕与菜粕, 4: 豆油与菜油, 5: 菜粕与菜油, 6: 豆油与棕榈油
PAIR_SELECTION = 6

# 指标类型选择（可选值：'ratio' 或 'diff'）
# 'ratio': 比值, 'diff': 差值
METRIC_TYPE = 'diff'

# 入场值（开始持仓的值）
ENTRY_VALUE = -1014

# 出场值（目标回归值）
EXIT_VALUE = -800

# 品种对映射
PAIR_MAPPING = {
    1: '豆一与豆二',
    2: '豆油与豆粕',
    3: '豆粕与菜粕',
    4: '菜油与豆油',
    5: '菜油与菜粕',
    6: '豆油与棕榈油'
}

# 品种对对应的主力合约文件映射
PAIR_TO_CONTRACTS = {
    '豆一与豆二': ['豆一主力合约历史价格数据.xlsx', '豆二主力合约历史价格数据.xlsx'],
    '豆油与豆粕': ['豆油主力合约历史价格数据.xlsx', '豆粕主力合约历史价格数据.xlsx'],
    '豆粕与菜粕': ['豆粕主力合约历史价格数据.xlsx', '菜粕主力合约历史价格数据.xlsx'],
    '菜油与豆油': ['菜油主力合约历史价格数据.xlsx', '豆油主力合约历史价格数据.xlsx'],
    '菜油与菜粕': ['菜油主力合约历史价格数据.xlsx', '菜粕主力合约历史价格数据.xlsx'],
    '豆油与棕榈油': ['豆油主力合约历史价格数据.xlsx', '棕榈油主力合约历史价格数据.xlsx']
}

# 指标类型映射
METRIC_MAPPING = {
    'ratio': '比值',
    'diff': '差值'
}
# ================================================


def read_ratio_data(pair_name: str, metric_type: str):
    """
    读取指定品种对的价格比值或差值数据

    Args:
        pair_name: 品种对名称（如：'豆粕与豆油'）
        metric_type: 指标类型（'比值' 或 '差值'）

    Returns:
        包含日期和指定指标的DataFrame
    """
    input_file = Path(f"metrics_data/{pair_name}_价格{metric_type}数据.xlsx")
    if not input_file.exists():
        raise FileNotFoundError(f"文件不存在: {input_file}")

    df = pd.read_excel(input_file, engine='openpyxl')
    logger.info(f"成功读取数据: {len(df)} 条记录")
    logger.info(f"数据列: {df.columns.tolist()}")

    # 确保指标列存在
    if metric_type not in df.columns:
        raise ValueError(f"找不到{metric_type}列")

    # 确保日期列存在
    if '日期' not in df.columns:
        raise ValueError("找不到日期列")

    # 转换日期列为datetime类型
    df['日期'] = pd.to_datetime(df['日期'], errors='coerce')

    # 过滤掉无效数据
    df = df[df[metric_type].notna()].copy()
    if metric_type == '比值':
        df = df[df[metric_type] > 0].copy()  # 比值应该大于0
    df = df[df['日期'].notna()].copy()  # 日期不能为空

    # 按日期排序
    df = df.sort_values('日期').reset_index(drop=True)

    logger.info(f"有效数据: {len(df)} 条记录")
    logger.info(f"日期范围: {df['日期'].min()} 至 {df['日期'].max()}")

    return df


def read_contract_data(pair_name: str):
    """
    读取品种对的主力合约历史价格数据

    Args:
        pair_name: 品种对名称（如：'豆粕与豆油'）

    Returns:
        包含两个品种主力合约数据的字典，键为品种名称，值为DataFrame
    """
    if pair_name not in PAIR_TO_CONTRACTS:
        raise ValueError(f"未找到品种对 {pair_name} 的合约文件映射")

    contract_files = PAIR_TO_CONTRACTS[pair_name]
    contract_data = {}

    for contract_file in contract_files:
        file_path = Path(f"processed_data/{contract_file}")
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        df = pd.read_excel(file_path, engine='openpyxl')

        # 确保必要的列存在
        if '交易日期' not in df.columns or '合约名称' not in df.columns:
            raise ValueError(f"文件 {contract_file} 缺少必要的列")

        # 转换日期列为datetime类型
        df['交易日期'] = pd.to_datetime(df['交易日期'], errors='coerce')

        # 过滤掉无效数据
        df = df[df['交易日期'].notna()].copy()
        df = df[df['合约名称'].notna()].copy()

        # 按日期排序
        df = df.sort_values('交易日期').reset_index(drop=True)

        # 提取品种名称（从文件名中）
        variety_name = contract_file.replace('主力合约历史价格数据.xlsx', '')
        contract_data[variety_name] = df

        logger.info(f"成功读取 {variety_name} 主力合约数据: {len(df)} 条记录")

    return contract_data


def check_contract_changes(entry_date, exit_date, contract_data: dict) -> dict:
    """
    检查在回归期间主力合约是否发生变化

    Args:
        entry_date: 入场日期
        exit_date: 出场日期
        contract_data: 包含两个品种主力合约数据的字典

    Returns:
        包含合约变化信息的字典
    """
    changes_info = {}

    for variety_name, df in contract_data.items():
        # 筛选出在回归期间的数据
        period_data = df[(df['交易日期'] >= entry_date) & (df['交易日期'] <= exit_date)].copy()

        if len(period_data) == 0:
            changes_info[variety_name] = {
                'has_change': False,
                'contracts': [],
                'change_dates': [],
                'message': '期间无数据'
            }
            continue

        # 获取期间内所有不同的合约
        contracts = period_data['合约名称'].unique().tolist()

        # 检查是否有合约变化
        has_change = len(contracts) > 1

        # 如果有变化，找出变化的日期
        change_dates = []
        if has_change:
            prev_contract = None
            for idx, row in period_data.iterrows():
                current_contract = row['合约名称']
                if prev_contract is not None and current_contract != prev_contract:
                    change_dates.append({
                        'date': row['交易日期'],
                        'from': prev_contract,
                        'to': current_contract
                    })
                prev_contract = current_contract

        changes_info[variety_name] = {
            'has_change': has_change,
            'contracts': contracts,
            'change_dates': change_dates,
            'message': f"合约变化: {' -> '.join(contracts)}" if has_change else '合约未变化'
        }

    return changes_info


def find_reversion_periods(df: pd.DataFrame, metric_col: str, entry_value: float, exit_value: float,
                          contract_data: dict = None) -> list:
    """
    查找所有从entry_value到exit_value的回归周期

    Args:
        df: 包含日期和指标的DataFrame，已按日期排序
        metric_col: 指标列名（'比值' 或 '差值'）
        entry_value: 入场值（开始持仓的值）
        exit_value: 出场值（目标值）
        contract_data: 主力合约数据字典（可选）

    Returns:
        包含回归周期信息的列表，每个元素是一个字典，包含：
        - entry_date: 入场日期
        - entry_value: 入场值
        - exit_date: 出场日期（如果找到）
        - exit_value: 出场值
        - days: 持仓天数（交易日数）
        - found: 是否找到出场点
        - contract_changes: 合约变化信息（如果提供了contract_data）
    """
    periods = []

    # 判断回归方向
    # 如果 entry_value > exit_value，说明指标需要下降（从高回归到低）
    # 如果 entry_value < exit_value，说明指标需要上升（从低回归到高）
    is_descending = entry_value > exit_value

    # 找到所有指标达到入场条件的时点
    if is_descending:
        # 从高到低回归：入场条件是指标 >= entry_value
        entry_indices = df[df[metric_col] >= entry_value].index.tolist()
        logger.info(f"找到 {len(entry_indices)} 个{metric_col}达到或超过 {entry_value} 的时点（从高到低回归）")
    else:
        # 从低到高回归：入场条件是指标 <= entry_value
        entry_indices = df[df[metric_col] <= entry_value].index.tolist()
        logger.info(f"找到 {len(entry_indices)} 个{metric_col}达到或低于 {entry_value} 的时点（从低到高回归）")

    for entry_idx in entry_indices:
        entry_date = df.loc[entry_idx, '日期']
        entry_metric_value = df.loc[entry_idx, metric_col]

        # 从入场点之后开始查找出场点
        future_data = df.iloc[entry_idx + 1:]

        if is_descending:
            # 指标需要下降，查找后续指标 <= exit_value的时点
            exit_candidates = future_data[future_data[metric_col] <= exit_value]
        else:
            # 指标需要上升，查找后续指标 >= exit_value的时点
            exit_candidates = future_data[future_data[metric_col] >= exit_value]

        if len(exit_candidates) > 0:
            # 找到第一个满足条件的出场点
            exit_idx = exit_candidates.index[0]
            exit_date = df.loc[exit_idx, '日期']
            exit_metric_value = df.loc[exit_idx, metric_col]
            days = (exit_date - entry_date).days

            period_info = {
                'entry_date': entry_date,
                'entry_value': entry_metric_value,
                'exit_date': exit_date,
                'exit_value': exit_metric_value,
                'days': days,
                'found': True
            }

            # 如果提供了合约数据，检查合约变化
            if contract_data is not None:
                contract_changes = check_contract_changes(entry_date, exit_date, contract_data)
                period_info['contract_changes'] = contract_changes

            periods.append(period_info)
        else:
            # 没有找到出场点（数据到末尾时指标还没有回归）
            period_info = {
                'entry_date': entry_date,
                'entry_value': entry_metric_value,
                'exit_date': None,
                'exit_value': None,
                'days': None,
                'found': False
            }

            # 即使没有找到出场点，也可以检查到数据末尾的合约变化
            if contract_data is not None:
                last_date = df['日期'].max()
                contract_changes = check_contract_changes(entry_date, last_date, contract_data)
                period_info['contract_changes'] = contract_changes

            periods.append(period_info)

    return periods


def analyze_reversion_time(periods: list) -> dict:
    """
    分析回归时间的统计信息
    
    Args:
        periods: 回归周期列表
    
    Returns:
        包含统计信息的字典
    """
    # 只统计找到出场点的情况
    found_periods = [p for p in periods if p['found']]
    
    if len(found_periods) == 0:
        return {
            'total_entries': len(periods),
            'found_exits': 0,
            'not_found_exits': len(periods),
            'mean_days': None,
            'median_days': None,
            'min_days': None,
            'max_days': None,
            'std_days': None,
            'percentiles': {}
        }
    
    days_list = [p['days'] for p in found_periods]
    
    percentiles = {
        '25%': np.percentile(days_list, 25),
        '50%': np.percentile(days_list, 50),
        '75%': np.percentile(days_list, 75),
        '90%': np.percentile(days_list, 90),
        '95%': np.percentile(days_list, 95),
        '99%': np.percentile(days_list, 99)
    }
    
    return {
        'total_entries': len(periods),
        'found_exits': len(found_periods),
        'not_found_exits': len(periods) - len(found_periods),
        'mean_days': np.mean(days_list),
        'median_days': np.median(days_list),
        'min_days': np.min(days_list),
        'max_days': np.max(days_list),
        'std_days': np.std(days_list),
        'percentiles': percentiles
    }


def main():
    """主函数"""
    # 验证配置
    if PAIR_SELECTION not in PAIR_MAPPING:
        raise ValueError(f"无效的品种对选择: {PAIR_SELECTION}，请选择1-5之间的数字")

    if METRIC_TYPE not in METRIC_MAPPING:
        raise ValueError(f"无效的指标类型: {METRIC_TYPE}，请选择 'ratio' 或 'diff'")

    pair_name = PAIR_MAPPING[PAIR_SELECTION]
    metric_name = METRIC_MAPPING[METRIC_TYPE]

    logger.info("=" * 60)
    logger.info(f"开始测试：{pair_name} {metric_name}从 {ENTRY_VALUE} 回归到 {EXIT_VALUE} 的时间分析")
    logger.info("=" * 60)

    # 1. 读取数据
    logger.info(f"\n步骤1: 读取{pair_name}价格比值差值数据")
    df = read_ratio_data(pair_name, metric_name)

    # 1.5. 读取主力合约数据
    logger.info(f"\n步骤1.5: 读取{pair_name}主力合约历史价格数据")
    try:
        contract_data = read_contract_data(pair_name)
    except Exception as e:
        logger.warning(f"读取主力合约数据失败: {e}")
        logger.warning("将继续分析，但不包含合约变化信息")
        contract_data = None

    # 2. 查找所有回归周期
    logger.info(f"\n步骤2: 查找所有从{metric_name} {ENTRY_VALUE} 到 {EXIT_VALUE} 的回归周期")
    periods = find_reversion_periods(df, metric_name, ENTRY_VALUE, EXIT_VALUE, contract_data)
    logger.info(f"共找到 {len(periods)} 个入场时点")

    # 3. 分析统计信息
    logger.info("\n步骤3: 分析回归时间统计信息")
    stats = analyze_reversion_time(periods)

    logger.info(f"\n统计结果:")
    logger.info(f"  总入场次数: {stats['total_entries']}")
    logger.info(f"  找到出场点的次数: {stats['found_exits']}")
    logger.info(f"  未找到出场点的次数: {stats['not_found_exits']}")

    if stats['found_exits'] > 0:
        logger.info(f"\n回归时间统计（仅统计找到出场点的情况）:")
        logger.info(f"  平均持仓天数: {stats['mean_days']:.2f} 天")
        logger.info(f"  中位数持仓天数: {stats['median_days']:.2f} 天")
        logger.info(f"  最短持仓天数: {stats['min_days']} 天")
        logger.info(f"  最长持仓天数: {stats['max_days']} 天")
        logger.info(f"  标准差: {stats['std_days']:.2f} 天")
        logger.info(f"\n分位数统计:")
        for pct, value in stats['percentiles'].items():
            logger.info(f"  {pct}: {value:.2f} 天")

        # 转换为周和月
        mean_weeks = stats['mean_days'] / 5  # 假设一周5个交易日
        mean_months = stats['mean_days'] / 20  # 假设一月20个交易日
        logger.info(f"\n平均持仓时间:")
        logger.info(f"  约 {mean_weeks:.2f} 周")
        logger.info(f"  约 {mean_months:.2f} 个月")

    # 4. 保存详细结果到Excel
    logger.info("\n步骤4: 保存详细结果到Excel")
    output_file = Path(f"{pair_name}_{metric_name}_回归时间结果.xlsx")

    # 创建详细结果DataFrame
    if len(periods) > 0:
        # 基础信息
        results_data = []
        for period in periods:
            row = {
                'entry_date': period['entry_date'].strftime('%Y-%m-%d') if pd.notna(period['entry_date']) else '',
                'entry_value': period['entry_value'],
                'exit_date': period['exit_date'].strftime('%Y-%m-%d') if pd.notna(period.get('exit_date')) else '',
                'exit_value': period.get('exit_value', ''),
                'days': period.get('days', ''),
                'found': period['found']
            }

            # 添加合约变化信息
            if 'contract_changes' in period and period['contract_changes']:
                for variety_name, change_info in period['contract_changes'].items():
                    row[f'{variety_name}_合约变化'] = '是' if change_info['has_change'] else '否'
                    row[f'{variety_name}_合约列表'] = ', '.join(change_info['contracts'])
                    if change_info['has_change'] and change_info['change_dates']:
                        change_details = []
                        for change in change_info['change_dates']:
                            change_details.append(
                                f"{change['date'].strftime('%Y-%m-%d')}: {change['from']}->{change['to']}"
                            )
                        row[f'{variety_name}_变化详情'] = '; '.join(change_details)
                    else:
                        row[f'{variety_name}_变化详情'] = ''

            results_data.append(row)

        results_df = pd.DataFrame(results_data)
    else:
        # 如果没有找到任何周期，创建空的DataFrame
        results_df = pd.DataFrame(columns=['entry_date', 'entry_value', 'exit_date', 'exit_value', 'days', 'found'])

    # 创建统计信息DataFrame
    if stats['found_exits'] > 0:
        stats_data = {
            '指标': ['总入场次数', '找到出场点次数', '未找到出场点次数',
                    '平均持仓天数', '中位数持仓天数', '最短持仓天数', '最长持仓天数', '标准差'],
            '数值': [stats['total_entries'], stats['found_exits'], stats['not_found_exits'],
                    stats['mean_days'], stats['median_days'], stats['min_days'],
                    stats['max_days'], stats['std_days']]
        }
        stats_df = pd.DataFrame(stats_data)

        # 添加分位数
        percentiles_data = {
            '指标': [f'{k}分位数' for k in stats['percentiles'].keys()],
            '数值': list(stats['percentiles'].values())
        }
        percentiles_df = pd.DataFrame(percentiles_data)
        stats_df = pd.concat([stats_df, percentiles_df], ignore_index=True)
    else:
        stats_df = pd.DataFrame({
            '指标': ['总入场次数', '找到出场点次数', '未找到出场点次数'],
            '数值': [stats['total_entries'], stats['found_exits'], stats['not_found_exits']]
        })

    # 保存到Excel的多个sheet
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        results_df.to_excel(writer, sheet_name='详细结果', index=False)
        stats_df.to_excel(writer, sheet_name='统计信息', index=False)

    logger.info(f"结果已保存到: {output_file}")

    # 5. 显示前几个案例
    logger.info("\n步骤5: 显示前10个回归周期案例")
    found_periods = [p for p in periods if p['found']]
    if found_periods:
        logger.info("\n前10个完整回归周期:")
        for i, period in enumerate(found_periods[:10], 1):
            logger.info(f"  案例 {i}:")
            logger.info(f"    入场日期: {period['entry_date'].strftime('%Y-%m-%d')}, {metric_name}: {period['entry_value']:.4f}")
            logger.info(f"    出场日期: {period['exit_date'].strftime('%Y-%m-%d')}, {metric_name}: {period['exit_value']:.4f}")
            logger.info(f"    持仓天数: {period['days']} 天")

            # 显示合约变化信息
            if 'contract_changes' in period and period['contract_changes']:
                logger.info(f"    合约变化情况:")
                for variety_name, change_info in period['contract_changes'].items():
                    if change_info['has_change']:
                        logger.info(f"      {variety_name}: {change_info['message']}")
                        for change in change_info['change_dates']:
                            logger.info(f"        {change['date'].strftime('%Y-%m-%d')}: {change['from']} -> {change['to']}")
                    else:
                        logger.info(f"      {variety_name}: 合约未变化 ({change_info['contracts'][0]})")

    logger.info("\n" + "=" * 60)
    logger.info("测试完成！")
    logger.info("=" * 60)

    return periods, stats


if __name__ == "__main__":
    main()

