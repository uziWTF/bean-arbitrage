# Claude 工作环境配置

## Python 环境
- 使用 conda 虚拟环境：`zeshi`
- 运行 Python 脚本时使用：`conda run -n zeshi python script.py`
- 或直接使用环境的 Python：`C:/Users/13741/miniconda3/envs/zeshi/python.exe script.py`

## 项目说明
- 项目路径：E:\project\arbitrage
- 豆类套利分析代码和数据位于 `豆类/` 子目录下
- 数据文件夹：豆类/ori_data
  - A：豆一期货数据
  - B：豆二期货数据
  - M：豆粕期货数据
  - Y：豆油期货数据
  - RM：菜粕期货数据
  - OI：菜油期货数据

## 品种对分析
当前系统分析以下5个品种对的价格关系：
1. 豆一与豆二
2. 豆粕与豆油
3. 豆粕与菜粕
4. 豆油与菜油
5. 菜粕与菜油


