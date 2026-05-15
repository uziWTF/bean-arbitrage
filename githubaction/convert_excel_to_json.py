"""
将 metrics_data 中的6个Excel文件转换为JSON格式
用于 GitHub Pages 网站的历史数据
"""

import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta


# 品种对配置（与 02_calculate_metrics.py 一致）
PAIRS_CONFIG = [
    {
        "id": "douyi_douer",
        "name_zh": "豆一与豆二",
        "name1": "豆一",
        "name2": "豆二",
        "metric_type": "diff",
        "metric_label": "差值",
        "excel_file": "豆一与豆二_价格差值数据.xlsx",
        "price1_col": "豆一收盘价",
        "price2_col": "豆二收盘价",
    },
    {
        "id": "douyou_doupo",
        "name_zh": "豆油与豆粕",
        "name1": "豆油",
        "name2": "豆粕",
        "metric_type": "ratio",
        "metric_label": "比值",
        "excel_file": "豆油与豆粕_价格比值数据.xlsx",
        "price1_col": "豆油收盘价",
        "price2_col": "豆粕收盘价",
    },
    {
        "id": "doupo_caipo",
        "name_zh": "豆粕与菜粕",
        "name1": "豆粕",
        "name2": "菜粕",
        "metric_type": "diff",
        "metric_label": "差值",
        "excel_file": "豆粕与菜粕_价格差值数据.xlsx",
        "price1_col": "豆粕收盘价",
        "price2_col": "菜粕收盘价",
    },
    {
        "id": "caiyou_douyou",
        "name_zh": "菜油与豆油",
        "name1": "菜油",
        "name2": "豆油",
        "metric_type": "diff",
        "metric_label": "差值",
        "excel_file": "菜油与豆油_价格差值数据.xlsx",
        "price1_col": "菜油收盘价",
        "price2_col": "豆油收盘价",
    },
    {
        "id": "caiyou_caipo",
        "name_zh": "菜油与菜粕",
        "name1": "菜油",
        "name2": "菜粕",
        "metric_type": "ratio",
        "metric_label": "比值",
        "excel_file": "菜油与菜粕_价格比值数据.xlsx",
        "price1_col": "菜油收盘价",
        "price2_col": "菜粕收盘价",
    },
    {
        "id": "youyou_zonglvyou",
        "name_zh": "豆油与棕榈油",
        "name1": "豆油",
        "name2": "棕榈油",
        "metric_type": "diff",
        "metric_label": "差值",
        "excel_file": "豆油与棕榈油_价格差值数据.xlsx",
        "price1_col": "豆油收盘价",
        "price2_col": "棕榈油收盘价",
    },
]


def convert_to_numeric(value):
    """将各种格式的值转换为数值"""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    value_str = str(value).strip().replace(",", "").replace("，", "")
    try:
        return float(value_str) if value_str else None
    except (ValueError, TypeError):
        return None


def calculate_statistics(values):
    """计算统计信息"""
    arr = np.array(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    n = len(arr)
    if n == 0:
        return {}

    mean = float(np.mean(arr))
    median = float(np.median(arr))
    std = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    mn = float(np.min(arr))
    mx = float(np.max(arr))
    q25 = float(np.percentile(arr, 25))
    q75 = float(np.percentile(arr, 75))

    # 偏度和峰度
    if std > 0 and n > 2:
        skewness = float(np.mean(((arr - mean) / std) ** 3))
        kurtosis = float(np.mean(((arr - mean) / std) ** 4) - 3)
    else:
        skewness = 0.0
        kurtosis = 0.0

    return {
        "count": n,
        "mean": round(mean, 6),
        "median": round(median, 6),
        "std": round(std, 6),
        "min": round(mn, 6),
        "max": round(mx, 6),
        "q25": round(q25, 6),
        "q75": round(q75, 6),
        "skewness": round(skewness, 4),
        "kurtosis": round(kurtosis, 4),
    }


def process_pair(pair_config, metrics_dir):
    """处理单个品种对的Excel文件"""
    excel_path = metrics_dir / pair_config["excel_file"]
    if not excel_path.exists():
        print(f"  [SKIP] 文件不存在: {excel_path}")
        return None

    df = pd.read_excel(excel_path, engine="openpyxl")
    print(f"  读取 {len(df)} 行数据")

    # 提取数据
    data = []
    metric_col = "比值" if pair_config["metric_type"] == "ratio" else "差值"

    for _, row in df.iterrows():
        date_val = row.iloc[0]
        if pd.isna(date_val):
            continue

        # 处理日期
        if isinstance(date_val, datetime):
            date_str = date_val.strftime("%Y-%m-%d")
        else:
            date_str = str(date_val)[:10]

        price1 = convert_to_numeric(row[pair_config["price1_col"]])
        price2 = convert_to_numeric(row[pair_config["price2_col"]])
        metric = convert_to_numeric(row[metric_col])

        if price1 is not None and price2 is not None and metric is not None:
            data.append(
                {
                    "date": date_str,
                    "price1": round(price1, 2),
                    "price2": round(price2, 2),
                    "metric": round(metric, 6),
                }
            )

    # 计算统计信息
    metrics = [d["metric"] for d in data]
    statistics = calculate_statistics(metrics)

    return {
        "id": pair_config["id"],
        "name_zh": pair_config["name_zh"],
        "name1": pair_config["name1"],
        "name2": pair_config["name2"],
        "metric_type": pair_config["metric_type"],
        "metric_label": pair_config["metric_label"],
        "data": data,
        "statistics": statistics,
    }


def main():
    # 路径配置
    script_dir = Path(__file__).parent
    metrics_dir = script_dir.parent / "豆类" / "metrics_data"
    output_dir = script_dir / "data"
    output_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("开始转换 Excel 数据为 JSON")
    print(f"数据源: {metrics_dir}")
    print(f"输出目录: {output_dir}")
    print("=" * 60)

    pairs = []
    for config in PAIRS_CONFIG:
        print(f"\n处理 {config['name_zh']}...")
        result = process_pair(config, metrics_dir)
        if result:
            pairs.append(result)
            print(f"  完成: {len(result['data'])} 条数据, "
                  f"统计: mean={result['statistics']['mean']}, "
                  f"std={result['statistics']['std']}")

    # 组装最终JSON
    output = {
        "last_updated": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"),
        "pairs": pairs,
    }

    output_path = output_dir / "pairs_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"转换完成! 输出: {output_path}")
    print(f"共 {len(pairs)} 个品种对")
    for p in pairs:
        print(f"  {p['name_zh']}: {len(p['data'])} 条数据")
    print("=" * 60)


if __name__ == "__main__":
    main()
