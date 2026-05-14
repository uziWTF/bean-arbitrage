"""
季节性规律分析模块
功能：分析多个品种对比值或差值的季节性规律
1. 从metrics_data文件夹读取各品种对的价格比值或差值数据
2. 统计每个品种对比值或差值的概率分布
3. 分析每个品种对比值或差值的季节规律（按月份统计）
4. 为每个品种对生成统计图表
5. 保存结果到seasonal_analysis文件夹
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


def read_metrics_data(name1: str, name2: str, metric_type: str):
    """
    读取指定品种对的价格比值或差值数据

    Args:
        name1: 第一个品种名称
        name2: 第二个品种名称
        metric_type: 'diff' 读取差值数据，'ratio' 读取比值数据

    Returns:
        包含日期和比值或差值的DataFrame
    """
    metric_name = '差值' if metric_type == 'diff' else '比值'
    input_file = Path(f"metrics_data/{name1}与{name2}_价格{metric_name}数据.xlsx")
    if not input_file.exists():
        raise FileNotFoundError(f"文件不存在: {input_file}")

    df = pd.read_excel(input_file, engine='openpyxl')
    logger.info(f"成功读取{name1}与{name2}数据: {len(df)} 条记录")
    logger.info(f"数据列: {df.columns.tolist()}")

    # 确保日期列是datetime类型
    if '日期' in df.columns:
        df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
    else:
        raise ValueError("找不到日期列")

    # 确保对应列存在
    if metric_name not in df.columns:
        raise ValueError(f"找不到{metric_name}列")

    # 过滤掉无效数据
    df = df[df['日期'].notna() & df[metric_name].notna()].copy()
    if metric_type == 'ratio':
        df = df[df['比值'] > 0].copy()

    logger.info(f"有效数据: {len(df)} 条记录")
    logger.info(f"日期范围: {df['日期'].min()} 到 {df['日期'].max()}")

    return df


def calculate_statistics(df: pd.DataFrame, metric: str):
    """
    计算统计指标
    
    Args:
        df: 数据DataFrame
        metric: 指标名称（'比值'或'差值'）
    
    Returns:
        统计信息字典
    """
    if len(df) == 0:
        logger.warning(f"没有数据")
        return None
    
    stats_dict = {
        '样本数': len(df),
        '平均值': df[metric].mean(),
        '中位数': df[metric].median(),
        '标准差': df[metric].std(),
        '最小值': df[metric].min(),
        '最大值': df[metric].max(),
        '25%分位数': df[metric].quantile(0.25),
        '75%分位数': df[metric].quantile(0.75),
        '偏度': df[metric].skew(),
        '峰度': df[metric].kurtosis(),
    }
    
    logger.info(f"\n{metric}统计信息:")
    for key, value in stats_dict.items():
        if isinstance(value, float):
            if metric == '比值':
                logger.info(f"  {key}: {value:.4f}")
            else:
                logger.info(f"  {key}: {value:.2f}")
        else:
            logger.info(f"  {key}: {value}")
    
    return stats_dict


def plot_distribution(df: pd.DataFrame, metric: str, name1: str, name2: str, output_path: Path):
    """
    绘制概率分布图
    
    Args:
        df: 数据DataFrame
        metric: 指标名称（'比值'或'差值'）
        name1: 第一个品种名称
        name2: 第二个品种名称
        output_path: 输出文件路径
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f'{name1}与{name2} {metric}概率分布统计', fontsize=14, fontweight='bold')
    
    # 直方图
    n_bins = 50
    ax1.hist(df[metric], bins=n_bins, color='#2E86AB', alpha=0.7, 
            edgecolor='black', density=True)
    mean_val = df[metric].mean()
    median_val = df[metric].median()
    format_str = '.4f' if metric == '比值' else '.2f'
    ax1.axvline(mean_val, color='r', linestyle='--', 
               linewidth=2, label=f'平均值: {mean_val:{format_str}}')
    ax1.axvline(median_val, color='g', linestyle='--', 
               linewidth=2, label=f'中位数: {median_val:{format_str}}')
    ax1.set_xlabel(metric, fontsize=12)
    ax1.set_ylabel('密度', fontsize=12)
    ax1.set_title(f'{metric}分布直方图', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 箱线图
    bp = ax2.boxplot(df[metric], vert=True, patch_artist=True,
                     boxprops=dict(facecolor='#2E86AB', alpha=0.7),
                     medianprops=dict(color='red', linewidth=2))
    ax2.set_ylabel(metric, fontsize=12)
    ax2.set_title(f'{metric}箱线图', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # 添加统计信息
    stats_text = f'统计信息:\n'
    stats_text += f'样本数: {len(df)}\n'
    stats_text += f'平均值: {mean_val:{format_str}}\n'
    stats_text += f'中位数: {median_val:{format_str}}\n'
    stats_text += f'标准差: {df[metric].std():{format_str}}\n'
    stats_text += f'最小值: {df[metric].min():{format_str}}\n'
    stats_text += f'最大值: {df[metric].max():{format_str}}\n'
    stats_text += f'25%分位数: {df[metric].quantile(0.25):{format_str}}\n'
    stats_text += f'75%分位数: {df[metric].quantile(0.75):{format_str}}'
    
    ax2.text(1.15, 0.5, stats_text, transform=ax2.transAxes, 
             fontsize=10, verticalalignment='center',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"概率分布图已保存到: {output_path}")


def analyze_seasonal_pattern(df: pd.DataFrame, metric: str):
    """
    分析季节规律（按月份统计）
    
    Args:
        df: 数据DataFrame
        metric: 指标名称（'比值'或'差值'）
    
    Returns:
        按月份统计的DataFrame
    """
    if len(df) == 0:
        logger.warning(f"没有数据，无法分析季节规律")
        return None
    
    df['月份'] = df['日期'].dt.month
    
    monthly_stats = df.groupby('月份')[metric].agg([
        ('样本数', 'count'),
        ('平均值', 'mean'),
        ('中位数', 'median'),
        ('标准差', 'std'),
        ('最小值', 'min'),
        ('最大值', 'max'),
        ('25%分位数', lambda x: x.quantile(0.25)),
        ('75%分位数', lambda x: x.quantile(0.75))
    ]).reset_index()
    
    monthly_stats['月份名称'] = monthly_stats['月份'].apply(
        lambda x: f"{x}月"
    )
    
    logger.info(f"\n{metric}月份统计:")
    logger.info(monthly_stats.to_string(index=False))
    
    return monthly_stats


def plot_seasonal_pattern(monthly_stats: pd.DataFrame, metric: str, name1: str, name2: str, output_path: Path):
    """
    绘制季节规律图
    
    Args:
        monthly_stats: 月份统计数据
        metric: 指标名称（'比值'或'差值'）
        name1: 第一个品种名称
        name2: 第二个品种名称
        output_path: 输出文件路径
    """
    if monthly_stats is None or len(monthly_stats) == 0:
        logger.warning(f"没有月份统计数据，无法绘制季节规律图")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f'{name1}与{name2} {metric}季节规律分析', fontsize=14, fontweight='bold')
    
    # 第一行：各月份平均值趋势
    ax1 = axes[0, 0]
    ax1.plot(monthly_stats['月份'], monthly_stats['平均值'], 
            marker='o', linewidth=2, markersize=8, color='#2E86AB', label='平均值')
    ax1.fill_between(monthly_stats['月份'], 
                     monthly_stats['平均值'] - monthly_stats['标准差'],
                     monthly_stats['平均值'] + monthly_stats['标准差'],
                     alpha=0.3, color='#2E86AB', label='±1标准差')
    ax1.set_xlabel('月份', fontsize=12)
    ax1.set_ylabel(metric, fontsize=12)
    ax1.set_title(f'各月份{metric}平均值趋势', fontsize=12, fontweight='bold')
    ax1.set_xticks(range(1, 13))
    ax1.set_xticklabels([f'{i}月' for i in range(1, 13)])
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 第二行：各月份中位数趋势
    ax2 = axes[0, 1]
    ax2.plot(monthly_stats['月份'], monthly_stats['中位数'], 
            marker='s', linewidth=2, markersize=8, color='#A23B72', label='中位数')
    ax2.set_xlabel('月份', fontsize=12)
    ax2.set_ylabel(metric, fontsize=12)
    ax2.set_title(f'各月份{metric}中位数趋势', fontsize=12, fontweight='bold')
    ax2.set_xticks(range(1, 13))
    ax2.set_xticklabels([f'{i}月' for i in range(1, 13)])
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 第三行：平均值和中位数对比
    ax3 = axes[1, 0]
    ax3.plot(monthly_stats['月份'], monthly_stats['平均值'], 
            marker='o', linewidth=2, markersize=8, color='#2E86AB', 
            label='平均值')
    ax3.plot(monthly_stats['月份'], monthly_stats['中位数'], 
            marker='s', linewidth=2, markersize=8, color='#A23B72', 
            label='中位数')
    ax3.set_xlabel('月份', fontsize=12)
    ax3.set_ylabel(metric, fontsize=12)
    ax3.set_title(f'各月份{metric}平均值与中位数对比', fontsize=12, fontweight='bold')
    ax3.set_xticks(range(1, 13))
    ax3.set_xticklabels([f'{i}月' for i in range(1, 13)])
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 第四行：柱状图
    ax4 = axes[1, 1]
    x = np.arange(len(monthly_stats))
    width = 0.6
    ax4.bar(x, monthly_stats['平均值'], width, label='平均值', color='#2E86AB', alpha=0.7)
    ax4.set_xlabel('月份', fontsize=12)
    ax4.set_ylabel(f'{metric}平均值', fontsize=12)
    ax4.set_title(f'各月份{metric}平均值柱状图', fontsize=12, fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(monthly_stats['月份名称'])
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"季节规律图已保存到: {output_path}")


def save_statistics_to_excel(stats: dict, monthly_stats: pd.DataFrame,
                             metric: str, name1: str, name2: str, output_path: Path):
    """
    保存统计结果到Excel文件

    Args:
        stats: 统计信息字典
        monthly_stats: 月份统计DataFrame
        metric: 指标名称（'比值'或'差值'）
        name1: 第一个品种名称
        name2: 第二个品种名称
        output_path: 输出文件路径
    """
    fmt = '.4f' if metric == '比值' else '.2f'
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        if stats:
            stats_df = pd.DataFrame({
                '统计指标': ['样本数', '平均值', '中位数', '标准差', '最小值', '最大值',
                          '25%分位数', '75%分位数', '偏度', '峰度'],
                '数值': [
                    stats.get('样本数', ''),
                    f"{stats.get('平均值', 0):{fmt}}",
                    f"{stats.get('中位数', 0):{fmt}}",
                    f"{stats.get('标准差', 0):{fmt}}",
                    f"{stats.get('最小值', 0):{fmt}}",
                    f"{stats.get('最大值', 0):{fmt}}",
                    f"{stats.get('25%分位数', 0):{fmt}}",
                    f"{stats.get('75%分位数', 0):{fmt}}",
                    f"{stats.get('偏度', 0):.4f}",
                    f"{stats.get('峰度', 0):.4f}",
                ]
            })
            stats_df.to_excel(writer, sheet_name=f'{metric}总体统计', index=False)

        if monthly_stats is not None and len(monthly_stats) > 0:
            monthly_stats.to_excel(writer, sheet_name=f'{metric}月份统计', index=False)

    logger.info(f"统计结果已保存到: {output_path}")


def process_pair(name1: str, name2: str, output_dir: Path, metric_type: str):
    """
    处理单个品种对的季节性分析

    Args:
        name1: 第一个品种名称
        name2: 第二个品种名称
        output_dir: 输出文件夹路径
        metric_type: 'diff' 分析差值，'ratio' 分析比值
    """
    logger.info(f"\n{'='*60}")
    metric_name = '差值' if metric_type == 'diff' else '比值'
    logger.info(f"开始分析{name1}与{name2}的{metric_name}季节规律")
    logger.info(f"{'='*60}")

    try:
        # 1. 读取数据
        logger.info(f"读取{name1}与{name2}的价格{metric_name}数据")
        df = read_metrics_data(name1, name2, metric_type)

        # 2. 计算统计指标
        logger.info(f"计算{name1}与{name2}的统计指标")
        stats = calculate_statistics(df, metric_name)

        # 3. 绘制概率分布图
        logger.info(f"绘制{name1}与{name2}的概率分布图")
        dist_path = output_dir / f"{name1}与{name2}_{metric_name}概率分布图.png"
        plot_distribution(df, metric_name, name1, name2, dist_path)

        # 4. 分析季节规律
        logger.info(f"分析{name1}与{name2}的季节规律（按月份统计）")
        monthly_stats = analyze_seasonal_pattern(df, metric_name)

        # 5. 绘制季节规律图
        logger.info(f"绘制{name1}与{name2}的季节规律图")
        seasonal_path = output_dir / f"{name1}与{name2}_{metric_name}季节规律图.png"
        plot_seasonal_pattern(monthly_stats, metric_name, name1, name2, seasonal_path)

        # 6. 保存统计结果到Excel
        logger.info(f"保存{name1}与{name2}的统计结果到Excel")
        excel_path = output_dir / f"{name1}与{name2}_统计结果.xlsx"
        save_statistics_to_excel(stats, monthly_stats, metric_name, name1, name2, excel_path)

        logger.info(f"{name1}与{name2}的分析完成！")

    except FileNotFoundError as e:
        logger.warning(f"跳过{name1}与{name2}的分析: {e}")
    except Exception as e:
        logger.error(f"处理{name1}与{name2}时出错: {e}", exc_info=True)


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始分析各品种对比值或差值的季节规律")
    logger.info("=" * 60)

    # 创建输出文件夹
    output_dir = Path("seasonal_analysis")
    output_dir.mkdir(exist_ok=True)
    logger.info(f"输出文件夹: {output_dir}")

    # 定义需要分析的品种对（name1, name2, metric_type）
    pairs = [
        ('豆一', '豆二', 'diff'),
        ('豆油', '豆粕', 'ratio'),
        ('豆粕', '菜粕', 'diff'),
        ('菜油', '豆油', 'diff'),
        ('菜油', '菜粕', 'ratio'),
        ('豆油', '棕榈油', 'diff')
    ]

    # 处理每个品种对
    logger.info(f"\n开始处理 {len(pairs)} 个品种对的季节性分析")
    for name1, name2, metric_type in pairs:
        process_pair(name1, name2, output_dir, metric_type)

    logger.info("\n" + "=" * 60)
    logger.info("所有任务完成！")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
