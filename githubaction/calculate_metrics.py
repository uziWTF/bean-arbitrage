"""
计算6个品种对的当前比值/差值，并对比历史数据计算百分位
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime


# 品种对配置
PAIRS_CONFIG = [
    {
        "id": "douyi_douer",
        "name_zh": "豆一与豆二",
        "name1": "豆一",
        "name2": "豆二",
        "metric_type": "diff",
        "metric_label": "差值",
    },
    {
        "id": "douyou_doupo",
        "name_zh": "豆油与豆粕",
        "name1": "豆油",
        "name2": "豆粕",
        "metric_type": "ratio",
        "metric_label": "比值",
    },
    {
        "id": "doupo_caipo",
        "name_zh": "豆粕与菜粕",
        "name1": "豆粕",
        "name2": "菜粕",
        "metric_type": "diff",
        "metric_label": "差值",
    },
    {
        "id": "caiyou_douyou",
        "name_zh": "菜油与豆油",
        "name1": "菜油",
        "name2": "豆油",
        "metric_type": "diff",
        "metric_label": "差值",
    },
    {
        "id": "caiyou_caipo",
        "name_zh": "菜油与菜粕",
        "name1": "菜油",
        "name2": "菜粕",
        "metric_type": "ratio",
        "metric_label": "比值",
    },
    {
        "id": "youyou_zonglvyou",
        "name_zh": "豆油与棕榈油",
        "name1": "豆油",
        "name2": "棕榈油",
        "metric_type": "diff",
        "metric_label": "差值",
    },
]


def load_json(path):
    """加载JSON文件"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    """保存JSON文件"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


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


def calculate_percentile(values, current_value):
    """计算当前值在历史数据中的百分位"""
    arr = np.array(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return 50.0
    count_below = np.sum(arr <= current_value)
    return round(float(count_below / len(arr) * 100), 2)


def get_status(percentile):
    """根据百分位获取状态"""
    if percentile <= 1.0:
        return "extreme_low", "极低", "#ff4757"
    elif percentile <= 5.0:
        return "very_low", "很低", "#ff6b81"
    elif percentile <= 25.0:
        return "low", "偏低", "#ff9500"
    elif percentile <= 75.0:
        return "normal", "正常", "#00d4aa"
    elif percentile <= 95.0:
        return "high", "偏高", "#ff9500"
    elif percentile <= 99.0:
        return "very_high", "很高", "#ff6b81"
    else:
        return "extreme_high", "极高", "#ff4757"


def main():
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"

    pairs_path = data_dir / "pairs_data.json"
    commodities_path = data_dir / "commodities.json"

    if not pairs_path.exists():
        print("错误: pairs_data.json 不存在，请先运行 convert_excel_to_json.py")
        return

    if not commodities_path.exists():
        print("错误: commodities.json 不存在，请先运行 scrape_prices.py")
        return

    print("=" * 60)
    print("开始计算品种对指标和百分位")
    print("=" * 60)

    # 加载数据
    pairs_data = load_json(pairs_path)
    commodities_data = load_json(commodities_path)

    # 构建品种价格查找表
    price_map = {}
    for c in commodities_data["commodities"]:
        if c["close_price"] is not None:
            price_map[c["name"]] = c["close_price"]

    print(f"\n最新价格:")
    for name, price in price_map.items():
        print(f"  {name}: {price}")

    # 处理每个品种对
    alerts = []
    scrape_date = commodities_data.get("scrape_date", datetime.now().strftime("%Y-%m-%d"))

    for pair in pairs_data["pairs"]:
        config = next((p for p in PAIRS_CONFIG if p["id"] == pair["id"]), None)
        if not config:
            continue

        name1 = config["name1"]
        name2 = config["name2"]

        if name1 not in price_map or name2 not in price_map:
            print(f"\n[{pair['name_zh']}] 缺少价格数据，跳过")
            continue

        price1 = price_map[name1]
        price2 = price_map[name2]

        # 计算当前指标
        if config["metric_type"] == "diff":
            current_metric = price1 - price2
        else:
            current_metric = price1 / price2 if price2 != 0 else 0

        # 检查是否已有今天的数据
        last_date = pair["data"][-1]["date"] if pair["data"] else ""
        if last_date == scrape_date:
            # 更新今天的数据
            pair["data"][-1] = {
                "date": scrape_date,
                "price1": round(price1, 2),
                "price2": round(price2, 2),
                "metric": round(current_metric, 6),
            }
            print(f"\n[{pair['name_zh']}] 更新 {scrape_date} 数据")
        else:
            # 添加新数据
            pair["data"].append({
                "date": scrape_date,
                "price1": round(price1, 2),
                "price2": round(price2, 2),
                "metric": round(current_metric, 6),
            })
            print(f"\n[{pair['name_zh']}] 添加 {scrape_date} 数据")

        # 重新计算统计信息
        metrics = [d["metric"] for d in pair["data"]]
        pair["statistics"] = calculate_statistics(metrics)

        # 计算百分位
        percentile = calculate_percentile(metrics, current_metric)
        status_type, status_text, status_color = get_status(percentile)

        # 计算z-score
        mean = pair["statistics"]["mean"]
        std = pair["statistics"]["std"]
        z_score = round((current_metric - mean) / std, 4) if std > 0 else 0

        # 添加当前值和百分位信息
        pair["current"] = {
            "value": round(current_metric, 6),
            "percentile": percentile,
            "status_type": status_type,
            "status_text": status_text,
            "status_color": status_color,
            "z_score": z_score,
            "date": scrape_date,
        }

        metric_label = config["metric_label"]
        print(f"  当前{metric_label}: {current_metric:.4f}")
        print(f"  百分位: {percentile}%")
        print(f"  状态: {status_text}")
        print(f"  Z-Score: {z_score}")

        # 检查是否需要警报
        if percentile <= 1.0 or percentile >= 99.0:
            alerts.append({
                "pair_id": pair["id"],
                "name_zh": pair["name_zh"],
                "metric_label": metric_label,
                "current_value": round(current_metric, 4),
                "percentile": percentile,
                "direction": "extreme_low" if percentile <= 1.0 else "extreme_high",
                "mean": mean,
                "std": std,
                "min": pair["statistics"]["min"],
                "max": pair["statistics"]["max"],
            })

    # 更新时间戳
    pairs_data["last_updated"] = scrape_date

    # 保存更新后的数据
    save_json(pairs_path, pairs_data)

    print(f"\n{'=' * 60}")
    print(f"计算完成! 数据已更新到: {pairs_path}")
    print(f"共 {len(pairs_data['pairs'])} 个品种对")

    if alerts:
        print(f"\n*** 发现 {len(alerts)} 个极端信号 ***")
        for alert in alerts:
            direction = "极低" if alert["direction"] == "extreme_low" else "极高"
            print(f"  {alert['name_zh']}: {alert['metric_label']}={alert['current_value']}, "
                  f"百分位={alert['percentile']}% ({direction})")

        # 保存警报信息供 send_alerts.py 使用
        alerts_path = data_dir / "alerts.json"
        save_json(alerts_path, {"alerts": alerts, "date": scrape_date})
        print(f"警报数据已保存到: {alerts_path}")
    else:
        print("\n没有触发极端信号警报")
        # 清除旧的警报文件
        alerts_path = data_dir / "alerts.json"
        if alerts_path.exists():
            alerts_path.unlink()

    print("=" * 60)


if __name__ == "__main__":
    main()
