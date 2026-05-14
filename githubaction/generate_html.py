"""
使用 Jinja2 渲染生成静态 HTML 页面
"""

import json
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def format_metric(value, metric_type):
    """格式化指标值"""
    if metric_type == "ratio":
        return f"{value:.4f}"
    return f"{value:,.0f}"


def format_stat(value, metric_type):
    """格式化统计值"""
    if metric_type == "ratio":
        return f"{value:.4f}"
    return f"{value:,.2f}"


def main():
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"
    template_dir = script_dir / "templates"
    output_dir = Path(__file__).parent.parent / "docs"
    output_dir.mkdir(exist_ok=True)

    # 加载数据
    pairs_path = data_dir / "pairs_data.json"
    with open(pairs_path, "r", encoding="utf-8") as f:
        pairs_data = json.load(f)

    # 设置 Jinja2 环境
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    env.filters["format_metric"] = format_metric
    env.filters["format_stat"] = format_stat

    # 渲染页面
    template = env.get_template("index.html")

    # 准备模板数据
    pairs = pairs_data["pairs"]
    last_updated = pairs_data.get("last_updated", "")

    # 将数据转换为JSON字符串供JavaScript使用
    pairs_json = json.dumps(pairs, ensure_ascii=False)

    # GitHub仓库URL（需要在部署时配置）
    repo_url = "https://github.com/YOUR_USERNAME/YOUR_REPO"

    html = template.render(
        pairs=pairs,
        last_updated=last_updated,
        pairs_json=pairs_json,
        repo_url=repo_url,
    )

    # 写入文件
    output_path = output_dir / "index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    # 复制 CSS 文件
    css_src = script_dir / "css" / "style.css"
    css_dst = output_dir / "css" / "style.css"
    css_dst.parent.mkdir(exist_ok=True)
    shutil.copy2(css_src, css_dst)

    print(f"页面已生成: {output_path}")
    print(f"共渲染 {len(pairs)} 个品种对")


if __name__ == "__main__":
    main()
