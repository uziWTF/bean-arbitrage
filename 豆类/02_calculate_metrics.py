"""
计算比值差值模块
功能：计算多个品种对主力合约每日的比值或差值并保存
1. 从processed_data文件夹读取所有品种（豆一、豆二、豆粕、豆油、菜粕、菜油、棕榈油）主力合约历史价格数据
2. 提取收盘价数据
3. 计算各品种对的比值或差值：
   - 豆一与豆二：只计算差值（豆一 - 豆二）
   - 豆油与豆粕：只计算比值（豆油 / 豆粕）
   - 豆粕与菜粕：只计算差值（豆粕 - 菜粕）
   - 菜油与豆油：只计算差值（菜油 - 豆油）
   - 菜油与菜粕：只计算比值（菜油 / 菜粕）
   - 豆油与棕榈油：只计算差值（豆油 - 棕榈油）
4. 为每个品种对绘制价格对比图（价格、差值或比值在同一张图上）
5. 为每个品种对绘制比值或差值概率分布统计图
6. 保存结果到metrics_data文件夹
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging

# 设置中文字体

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def find_price_column(df: pd.DataFrame, keywords: list) -> str:
    """
    查找价格列（收盘价）
    
    Args:
        df: DataFrame
        keywords: 关键词列表，如 ['收盘', 'close', '结算']
    
    Returns:
        列名，如果找不到返回None
    """
    for col in df.columns:
        col_str = str(col).lower()
        for keyword in keywords:
            if keyword.lower() in col_str:
                return col
    return None


def read_price_data():
    """
    读取所有品种的主力合约历史价格数据

    Returns:
        dict: 包含所有品种数据的字典，键为品种名称（豆一、豆二、豆粕、豆油、菜粕、菜油、棕榈油）
    """
    input_dir = Path("processed_data")
    data_dict = {}

    # 定义品种映射
    varieties = {
        '豆一': 'A',
        '豆二': 'B',
        '豆粕': 'M',
        '豆油': 'Y',
        '菜粕': 'RM',
        '菜油': 'OI',
        '棕榈油': 'P'
    }
    
    for name, code in varieties.items():
        file_path = input_dir / f"{name}主力合约历史价格数据.xlsx"
        if not file_path.exists():
            logger.warning(f"文件不存在: {file_path}，跳过该品种")
            continue
        
        try:
            data = pd.read_excel(file_path, engine='openpyxl')
            data_dict[name] = data
            logger.info(f"成功读取{name}数据: {len(data)} 条记录")
        except Exception as e:
            logger.error(f"读取{name}数据失败: {e}")
    
    if not data_dict:
        raise ValueError("没有读取到任何数据")
    
    return data_dict


def extract_closing_prices(data1: pd.DataFrame, name1: str, 
                          data2: pd.DataFrame, name2: str) -> pd.DataFrame:
    """
    提取两个品种的收盘价数据并合并
    
    Args:
        data1: 第一个品种的数据
        name1: 第一个品种的名称
        data2: 第二个品种的数据
        name2: 第二个品种的名称
    
    Returns:
        包含日期、两个品种收盘价的DataFrame
    """
    # 查找日期列
    date_col1 = None
    date_col2 = None
    for col in data1.columns:
        col_str = str(col).lower()
        if '日期' in col_str or 'date' in col_str or '交易日期' in col_str:
            date_col1 = col
            break
    for col in data2.columns:
        col_str = str(col).lower()
        if '日期' in col_str or 'date' in col_str or '交易日期' in col_str:
            date_col2 = col
            break
    
    if not date_col1 or not date_col2:
        raise ValueError("找不到日期列")
    
    # 查找收盘价列（严格只使用收盘价）
    price_col1 = find_price_column(data1, ['收盘', 'close'])
    price_col2 = find_price_column(data2, ['收盘', 'close'])
    
    if not price_col1:
        raise ValueError(f"找不到{name1}收盘价列")
    if not price_col2:
        raise ValueError(f"找不到{name2}收盘价列")
    
    logger.info(f"{name1}日期列: {date_col1}, 收盘价列: {price_col1}")
    logger.info(f"{name2}日期列: {date_col2}, 收盘价列: {price_col2}")
    
    # 转换日期列为datetime类型
    data1[date_col1] = pd.to_datetime(data1[date_col1], errors='coerce')
    data2[date_col2] = pd.to_datetime(data2[date_col2], errors='coerce')
    
    # 提取需要的列
    df1 = data1[[date_col1, price_col1]].copy()
    df1.columns = ['日期', f'{name1}收盘价']
    
    df2 = data2[[date_col2, price_col2]].copy()
    df2.columns = ['日期', f'{name2}收盘价']
    
    # 转换价格为数值类型
    def convert_to_numeric(value):
        if pd.isna(value):
            return np.nan
        if isinstance(value, (int, float)):
            return float(value)
        value_str = str(value).strip().replace(',', '').replace('，', '')
        try:
            return float(value_str) if value_str else np.nan
        except (ValueError, TypeError):
            return np.nan
    
    df1[f'{name1}收盘价'] = df1[f'{name1}收盘价'].apply(convert_to_numeric)
    df2[f'{name2}收盘价'] = df2[f'{name2}收盘价'].apply(convert_to_numeric)
    
    # 按日期合并
    merged_df = pd.merge(df1, df2, on='日期', how='inner')
    
    # 过滤掉价格为0或NaN的行
    price_col1_name = f'{name1}收盘价'
    price_col2_name = f'{name2}收盘价'
    merged_df = merged_df[
        (merged_df[price_col1_name] > 0) & 
        (merged_df[price_col2_name] > 0) &
        merged_df[price_col1_name].notna() &
        merged_df[price_col2_name].notna()
    ].copy()
    
    # 按日期排序
    merged_df = merged_df.sort_values('日期').reset_index(drop=True)
    
    logger.info(f"合并后数据: {len(merged_df)} 条记录")
    logger.info(f"日期范围: {merged_df['日期'].min()} 至 {merged_df['日期'].max()}")
    
    return merged_df


def calculate_metrics(df: pd.DataFrame, name1: str, name2: str, metric_type: str) -> pd.DataFrame:
    """
    计算差值或比值

    Args:
        df: 包含两个品种收盘价的DataFrame
        name1: 第一个品种名称
        name2: 第二个品种名称
        metric_type: 'diff' 表示只计算差值，'ratio' 表示只计算比值

    Returns:
        添加了差值或比值列的DataFrame
    """
    df = df.copy()
    price_col1 = f'{name1}收盘价'
    price_col2 = f'{name2}收盘价'

    if metric_type == 'diff':
        df['差值'] = df[price_col1] - df[price_col2]
        logger.info(f"{name1}与{name2}差值统计:")
        logger.info(f"  最小值: {df['差值'].min():.2f}")
        logger.info(f"  最大值: {df['差值'].max():.2f}")
        logger.info(f"  平均值: {df['差值'].mean():.2f}")
        logger.info(f"  中位数: {df['差值'].median():.2f}")
        logger.info(f"  标准差: {df['差值'].std():.2f}")
    elif metric_type == 'ratio':
        df['比值'] = df[price_col1] / df[price_col2]
        logger.info(f"{name1}与{name2}比值统计:")
        logger.info(f"  最小值: {df['比值'].min():.4f}")
        logger.info(f"  最大值: {df['比值'].max():.4f}")
        logger.info(f"  平均值: {df['比值'].mean():.4f}")
        logger.info(f"  中位数: {df['比值'].median():.4f}")
        logger.info(f"  标准差: {df['比值'].std():.4f}")

    return df


def plot_price_comparison(df: pd.DataFrame, name1: str, name2: str, output_path: Path, metric_type: str):
    """
    绘制价格对比图，包含价格subplot和差值或比值subplot

    Args:
        df: 包含日期、价格、差值或比值的DataFrame
        name1: 第一个品种名称
        name2: 第二个品种名称
        output_path: 输出文件路径
        metric_type: 'diff' 只绘制差值，'ratio' 只绘制比值
    """
    # 价格图占50%，差值/比值图占50%（高度翻倍）
    fig, axes = plt.subplots(2, 1, figsize=(16, 12),
                            gridspec_kw={'height_ratios': [2, 2]})
    fig.suptitle(f'{name1}与{name2}价格对比分析', fontsize=16, fontweight='bold', y=0.995)

    # 确保日期是datetime类型
    df['日期_datetime'] = pd.to_datetime(df['日期'])
    df_sorted = df.sort_values('日期_datetime').copy()

    price_col1 = f'{name1}收盘价'
    price_col2 = f'{name2}收盘价'

    # 第一个subplot: 价格对比
    ax1 = axes[0]
    ax1.plot(df_sorted['日期_datetime'], df_sorted[price_col1],
            linewidth=1.5, color='#2E86AB', label=f'{name1}收盘价', alpha=0.8)
    ax1.plot(df_sorted['日期_datetime'], df_sorted[price_col2],
            linewidth=1.5, color='#A23B72', label=f'{name2}收盘价', alpha=0.8)
    ax1.set_ylabel('价格', fontsize=12)
    ax1.set_title(f'{name1}与{name2}收盘价格走势', fontsize=13, fontweight='bold')
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(df_sorted['日期_datetime'].min(), df_sorted['日期_datetime'].max())

    # 第二个subplot: 差值或比值（高度翻倍）
    ax2 = axes[1]
    if metric_type == 'diff':
        ax2.plot(df_sorted['日期_datetime'], df_sorted['差值'],
                linewidth=1.5, color='#F18F01', label=f'差值 ({name1}-{name2})', alpha=0.8)
        ax2.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        mean_diff = df_sorted['差值'].mean()
        ax2.axhline(y=mean_diff, color='r', linestyle='--', linewidth=1.5,
                   label=f'平均值: {mean_diff:.2f}', alpha=0.7)
        ax2.set_ylabel('差值', fontsize=12)
        ax2.set_title(f'{name1}与{name2}价格差值走势', fontsize=13, fontweight='bold')
    elif metric_type == 'ratio':
        ax2.plot(df_sorted['日期_datetime'], df_sorted['比值'],
                linewidth=1.5, color='#06A77D', label=f'比值 ({name1}/{name2})', alpha=0.8)
        mean_ratio = df_sorted['比值'].mean()
        ax2.axhline(y=mean_ratio, color='r', linestyle='--', linewidth=1.5,
                   label=f'平均值: {mean_ratio:.4f}', alpha=0.7)
        std_ratio = df_sorted['比值'].std()
        ax2.axhline(y=mean_ratio + 1.5 * std_ratio, color='orange', linestyle=':',
                   linewidth=1, alpha=0.6, label=f'±1.5σ区间')
        ax2.axhline(y=mean_ratio - 1.5 * std_ratio, color='orange', linestyle=':',
                   linewidth=1, alpha=0.6)
        ax2.fill_between(df_sorted['日期_datetime'],
                         mean_ratio - 1.5 * std_ratio,
                         mean_ratio + 1.5 * std_ratio,
                         alpha=0.1, color='orange')
        ax2.set_ylabel('比值', fontsize=12)
        ax2.set_title(f'{name1}与{name2}价格比值走势', fontsize=13, fontweight='bold')

    ax2.set_xlabel('日期', fontsize=12)
    ax2.legend(loc='best', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(df_sorted['日期_datetime'].min(), df_sorted['日期_datetime'].max())

    # 格式化x轴日期
    fig.autofmt_xdate()
    plt.tight_layout(rect=[0, 0, 1, 0.98])

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"价格对比图已保存到: {output_path}")


def plot_distribution(df: pd.DataFrame, name1: str, name2: str, output_path: Path, metric_type: str):
    """
    绘制比值或差值的概率分布统计图

    Args:
        df: 包含差值或比值的DataFrame
        name1: 第一个品种名称
        name2: 第二个品种名称
        output_path: 输出文件路径
        metric_type: 'diff' 只绘制差值分布，'ratio' 只绘制比值分布
    """
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    n_bins = 50

    if metric_type == 'diff':
        col = '差值'
        color = '#F18F01'
        fmt = '.2f'
        fig.suptitle(f'{name1}与{name2}差值概率分布统计', fontsize=14, fontweight='bold')

        ax1 = axes[0]
        ax1.hist(df[col], bins=n_bins, color=color, alpha=0.7, edgecolor='black')
        ax1.axvline(df[col].mean(), color='r', linestyle='--', linewidth=2,
                   label=f'平均值: {df[col].mean():{fmt}}')
        ax1.axvline(df[col].median(), color='g', linestyle='--', linewidth=2,
                   label=f'中位数: {df[col].median():{fmt}}')
        ax1.set_xlabel('差值', fontsize=12)
        ax1.set_ylabel('频数', fontsize=12)
        ax1.set_title('差值分布直方图', fontsize=12, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2 = axes[1]
        ax2.boxplot(df[col], vert=True, patch_artist=True,
                   boxprops=dict(facecolor=color, alpha=0.7),
                   medianprops=dict(color='red', linewidth=2))
        ax2.set_ylabel('差值', fontsize=12)
        ax2.set_title('差值箱线图', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')

    elif metric_type == 'ratio':
        col = '比值'
        color = '#06A77D'
        fmt = '.4f'
        fig.suptitle(f'{name1}与{name2}比值概率分布统计', fontsize=14, fontweight='bold')

        ax1 = axes[0]
        ax1.hist(df[col], bins=n_bins, color=color, alpha=0.7, edgecolor='black')
        ax1.axvline(df[col].mean(), color='r', linestyle='--', linewidth=2,
                   label=f'平均值: {df[col].mean():{fmt}}')
        ax1.axvline(df[col].median(), color='g', linestyle='--', linewidth=2,
                   label=f'中位数: {df[col].median():{fmt}}')
        ax1.set_xlabel('比值', fontsize=12)
        ax1.set_ylabel('频数', fontsize=12)
        ax1.set_title('比值分布直方图', fontsize=12, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2 = axes[1]
        ax2.boxplot(df[col], vert=True, patch_artist=True,
                   boxprops=dict(facecolor=color, alpha=0.7),
                   medianprops=dict(color='red', linewidth=2))
        ax2.set_ylabel('比值', fontsize=12)
        ax2.set_title('比值箱线图', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"概率分布图已保存到: {output_path}")


def process_pair(data_dict: dict, name1: str, name2: str, output_dir: Path, metric_type: str):
    """
    处理一对品种的关系分析

    Args:
        data_dict: 包含所有品种数据的字典
        name1: 第一个品种名称
        name2: 第二个品种名称
        output_dir: 输出文件夹路径
        metric_type: 'diff' 只计算差值，'ratio' 只计算比值
    """
    if name1 not in data_dict or name2 not in data_dict:
        logger.warning(f"缺少数据，跳过{name1}与{name2}的分析")
        return

    logger.info(f"\n{'='*60}")
    logger.info(f"开始分析{name1}与{name2}的价格关系")
    logger.info(f"{'='*60}")

    # 提取收盘价并合并
    logger.info(f"提取{name1}和{name2}的收盘价数据并合并")
    merged_df = extract_closing_prices(data_dict[name1], name1, data_dict[name2], name2)

    # 计算差值或比值
    metric_name = '差值' if metric_type == 'diff' else '比值'
    logger.info(f"计算{name1}与{name2}价格的{metric_name}")
    result_df = calculate_metrics(merged_df, name1, name2, metric_type)

    # 保存数据到Excel
    logger.info(f"保存{name1}与{name2}的{metric_name}数据到Excel")
    price_col1 = f'{name1}收盘价'
    price_col2 = f'{name2}收盘价'
    excel_path = output_dir / f"{name1}与{name2}_价格{metric_name}数据.xlsx"

    if metric_type == 'diff':
        result_df[['日期', price_col1, price_col2, '差值']].to_excel(
            excel_path, index=False, engine='openpyxl'
        )
    elif metric_type == 'ratio':
        result_df[['日期', price_col1, price_col2, '比值']].to_excel(
            excel_path, index=False, engine='openpyxl'
        )
    logger.info(f"数据已保存到: {excel_path}")

    # 绘制价格对比图
    logger.info(f"绘制{name1}与{name2}的价格对比图（价格、{metric_name}）")
    comparison_path = output_dir / f"{name1}与{name2}_价格对比图.png"
    plot_price_comparison(result_df, name1, name2, comparison_path, metric_type)

    # 绘制概率分布图
    logger.info(f"绘制{name1}与{name2}的{metric_name}概率分布统计图")
    dist_path = output_dir / f"{name1}与{name2}_概率分布统计图.png"
    plot_distribution(result_df, name1, name2, dist_path, metric_type)

    logger.info(f"{name1}与{name2}的分析完成！")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始计算各品种对价格的比值和差值")
    logger.info("=" * 60)
    
    # 创建输出文件夹
    output_dir = Path("metrics_data")
    output_dir.mkdir(exist_ok=True)
    logger.info(f"输出文件夹: {output_dir}")
    
    # 1. 读取所有品种数据
    logger.info("\n步骤1: 读取所有品种主力合约历史价格数据")
    data_dict = read_price_data()
    logger.info(f"成功读取 {len(data_dict)} 个品种的数据")
    
    # 2. 定义需要分析的品种对（name1, name2, metric_type）
    # metric_type: 'diff' 计算 name1-name2，'ratio' 计算 name1/name2
    pairs = [
        ('豆一', '豆二', 'diff'),    # 豆一 - 豆二
        ('豆油', '豆粕', 'ratio'),   # 豆油 / 豆粕
        ('豆粕', '菜粕', 'diff'),    # 豆粕 - 菜粕
        ('菜油', '豆油', 'diff'),    # 菜油 - 豆油
        ('菜油', '菜粕', 'ratio'),   # 菜油 / 菜粕
        ('豆油', '棕榈油', 'diff'),  # 豆油 - 棕榈油
    ]

    # 3. 处理每个品种对
    logger.info(f"\n步骤2: 开始处理 {len(pairs)} 个品种对的关系分析")
    for name1, name2, metric_type in pairs:
        try:
            process_pair(data_dict, name1, name2, output_dir, metric_type)
        except Exception as e:
            logger.error(f"处理{name1}与{name2}时出错: {e}", exc_info=True)
    
    logger.info("\n" + "=" * 60)
    logger.info("所有任务完成！")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

