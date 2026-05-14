"""
检查极端信号并发送邮件警报
"""

import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def load_json(path):
    """加载JSON文件"""
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def send_email(to_email, subject, html_content, smtp_config):
    """发送HTML邮件"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{smtp_config['sender_name']} <{smtp_config['sender_email']}>"
    msg["To"] = to_email

    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_config["server"], int(smtp_config["port"])) as server:
            server.starttls()
            server.login(smtp_config["username"], smtp_config["password"])
            server.sendmail(smtp_config["sender_email"], to_email, msg.as_string())
        print(f"  邮件已发送到: {to_email}")
        return True
    except Exception as e:
        print(f"  发送失败 ({to_email}): {e}")
        return False


def main():
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"
    template_dir = script_dir / "templates"

    # 加载警报数据
    alerts_path = data_dir / "alerts.json"
    alerts_data = load_json(alerts_path)

    if not alerts_data or not alerts_data.get("alerts"):
        print("没有需要发送的警报")
        # 设置 GitHub Actions 输出
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

    # 加载订阅者
    subscribers_path = data_dir / "subscribers.json"
    subscribers_data = load_json(subscribers_path)

    if not subscribers_data or not subscribers_data.get("subscribers"):
        print("\n没有订阅者，跳过邮件发送")
        return

    active_subscribers = [
        s for s in subscribers_data["subscribers"]
        if s.get("active", True)
    ]

    if not active_subscribers:
        print("\n没有活跃订阅者，跳过邮件发送")
        return

    print(f"\n共有 {len(active_subscribers)} 个活跃订阅者")

    # SMTP 配置（从环境变量读取）
    smtp_config = {
        "server": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
        "port": os.environ.get("SMTP_PORT", "587"),
        "username": os.environ.get("SMTP_USERNAME", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "sender_email": os.environ.get("ALERT_SENDER_EMAIL", ""),
        "sender_name": os.environ.get("ALERT_SENDER_NAME", "套利分析助手"),
    }

    if not smtp_config["username"] or not smtp_config["password"]:
        print("\n错误: SMTP 配置不完整，请检查环境变量")
        print("需要设置: SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, ALERT_SENDER_EMAIL")
        return

    # 设置 GitHub Actions 输出
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write("has_alerts=true\n")

    # 渲染邮件模板
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("email_alert.html")

    # 确定仪表盘URL
    dashboard_url = os.environ.get("DASHBOARD_URL", "https://YOUR_USERNAME.github.io/YOUR_REPO/")
    unsubscribe_url = "https://github.com/YOUR_USERNAME/YOUR_REPO/issues/new?template=unsubscribe.yml"

    html_content = template.render(
        alerts=alerts,
        date=date,
        dashboard_url=dashboard_url,
        unsubscribe_url=unsubscribe_url,
    )

    # 构建邮件主题
    pair_names = [a["name_zh"] for a in alerts]
    subject = f"期货套利极端信号 - {', '.join(pair_names)} 触发警报 ({date})"

    # 发送邮件
    print(f"\n开始发送邮件...")
    success_count = 0
    for subscriber in active_subscribers:
        email = subscriber["email"]
        if send_email(email, subject, html_content, smtp_config):
            success_count += 1

    print(f"\n邮件发送完成: {success_count}/{len(active_subscribers)} 成功")


if __name__ == "__main__":
    main()
