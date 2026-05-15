"""
检查极端信号并通过飞书机器人发送警报
"""

import json
import os
import hashlib
import hmac
import base64
import time
import requests
from pathlib import Path


def load_json(path):
    """加载JSON文件"""
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def gen_sign(timestamp, secret):
    """生成飞书签名（可选安全设置）"""
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"), string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def build_feishu_card(alerts, date, dashboard_url):
    """构建飞书消息卡片"""
    extreme_high = sum(1 for a in alerts if a["direction"] == "extreme_high")
    extreme_low = sum(1 for a in alerts if a["direction"] == "extreme_low")

    elements = []

    # 概览
    summary_parts = []
    if extreme_high > 0:
        summary_parts.append(f"{extreme_high}个极高信号")
    if extreme_low > 0:
        summary_parts.append(f"{extreme_low}个极低信号")
    summary = "、".join(summary_parts)

    elements.append({
        "tag": "markdown",
        "content": f"**日期**: {date}  |  **触发信号**: {len(alerts)} 个 ({summary})"
    })
    elements.append({"tag": "hr"})

    # 每个信号
    for alert in alerts:
        is_high = alert["direction"] == "extreme_high"
        direction_text = "↑ 极高" if is_high else "↓ 极低"

        elements.append({
            "tag": "markdown",
            "content": (
                f"**{alert['name_zh']}**\n"
                f"当前{alert['metric_label']}: **{alert['current_value']}**  |  "
                f"分位数: **{alert['percentile']}%**  |  "
                f"信号: **{direction_text}**"
            )
        })
        elements.append({
            "tag": "markdown",
            "content": (
                f"均值: {alert['mean']}  |  标准差: {alert['std']}  |  "
                f"历史区间: [{alert['min']}, {alert['max']}]"
            )
        })
        elements.append({"tag": "hr"})

    # 底部按钮
    elements.append({
        "tag": "action",
        "actions": [{
            "tag": "button",
            "text": {"tag": "plain_text", "content": "查看完整仪表盘"},
            "url": dashboard_url,
            "type": "primary",
        }]
    })

    return {
        "header": {
            "title": {"tag": "plain_text", "content": "豆类期货套利 - 极端信号警报"},
            "template": "red" if extreme_high > 0 else "blue",
        },
        "elements": elements,
    }


def send_to_feishu(webhook_url, card, secret=None):
    """通过飞书 webhook 发送消息卡片"""
    payload = {"msg_type": "interactive", "card": card}

    if secret:
        timestamp = str(int(time.time()))
        payload["timestamp"] = timestamp
        payload["sign"] = gen_sign(timestamp, secret)

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        result = resp.json()
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            return True
        print(f"  飞书返回错误: {result}")
        return False
    except Exception as e:
        print(f"  发送失败: {e}")
        return False


def main():
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"

    alerts_path = data_dir / "alerts.json"
    alerts_data = load_json(alerts_path)

    if not alerts_data or not alerts_data.get("alerts"):
        print("没有需要发送的警报")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write("has_alerts=false\n")
        return

    alerts = alerts_data["alerts"]
    date = alerts_data.get("date", "")

    print(f"发现 {len(alerts)} 个极端信号:")
    for alert in alerts:
        direction = "极高" if alert["direction"] == "extreme_high" else "极低"
        print(f"  {alert['name_zh']}: {alert['metric_label']}={alert['current_value']}, "
              f"百分位={alert['percentile']}% ({direction})")

    subscribers_path = data_dir / "subscribers.json"
    subscribers_data = load_json(subscribers_path)

    if not subscribers_data or not subscribers_data.get("subscribers"):
        print("\n没有订阅者，跳过飞书发送")
        return

    active_subscribers = [
        s for s in subscribers_data["subscribers"]
        if s.get("active", True)
    ]

    if not active_subscribers:
        print("\n没有活跃订阅者，跳过飞书发送")
        return

    print(f"\n共有 {len(active_subscribers)} 个活跃订阅者")

    secret = os.environ.get("FEISHU_WEBHOOK_SECRET", "")
    dashboard_url = os.environ.get("DASHBOARD_URL", "https://YOUR_USERNAME.github.io/YOUR_REPO/")

    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write("has_alerts=true\n")

    card = build_feishu_card(alerts, date, dashboard_url)

    print(f"\n开始发送飞书消息...")
    success_count = 0
    for subscriber in active_subscribers:
        webhook_url = subscriber.get("webhook_url", "")
        if not webhook_url:
            print(f"  跳过: {subscriber.get('name', '未知')} 没有 webhook URL")
            continue

        name = subscriber.get("name", webhook_url[-8:])
        if send_to_feishu(webhook_url, card, secret=secret if secret else None):
            print(f"  已发送到: {name}")
            success_count += 1
        else:
            print(f"  发送失败: {name}")

    print(f"\n飞书发送完成: {success_count}/{len(active_subscribers)} 成功")


if __name__ == "__main__":
    main()
