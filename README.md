# 大豆期货套利数据分析系统

## 项目结构

```
arbitrage/
├── CLAUDE.md                    # Claude 工作环境配置
├── README.md                    # 本文件
├── pyproject.toml               # 项目配置
└── 豆类/                        # 豆类套利分析模块
    ├── ori_data/                # 原始数据文件夹
    │   ├── A/                   # 豆一原始数据
    │   ├── B/                   # 豆二原始数据
    │   ├── M/                   # 豆粕原始数据
    │   ├── Y/                   # 豆油原始数据
    │   ├── RM/                  # 菜粕原始数据
    │   ├── OI/                  # 菜油原始数据
    │   ├── P/                   # 棕榈油原始数据
    │   └── merge_data.py        # 数据合并工具
    ├── processed_data/          # 预处理后的数据（由01生成）
    ├── metrics_data/            # 比值/差值数据（由02生成）
    ├── seasonal_analysis/       # 季节性分析结果（由03生成）
    ├── 01_data_preprocessing.py # 数据预处理模块
    ├── 02_calculate_metrics.py  # 计算比值/差值模块
    ├── 03_seasonal_analysis.py  # 季节性规律分析模块
    ├── 04_test_ratio_reversion_time.py  # 回归时间测试模块
    └── 05_update_data.py        # 数据更新模块
```

## 使用说明

### 执行顺序

请按照以下顺序依次执行三个模块：

#### 1. 数据预处理 (`01_data_preprocessing.py`)

**功能**：
- 读取原始期货数据（ori_data文件夹，包含豆一、豆二、豆粕、豆油、菜粕、菜油、棕榈油）
- 以豆二为参考，分析每个交易日的主力合约（持仓量最大）
- 筛选出所有品种（豆一、豆二、豆粕、豆油、菜粕、菜油、棕榈油）的主力合约历史价格数据
- 所有品种使用豆二分析出的主力合约月份
- 保存到 `processed_data` 文件夹

**输出文件**：
- `processed_data/豆二主力合约月份记录.xlsx` - 主力合约月份记录（以豆二为参考）
- `processed_data/豆二主力合约历史价格数据.xlsx` - 豆二主力合约价格数据
- `processed_data/豆粕主力合约历史价格数据.xlsx` - 豆粕主力合约价格数据
- `processed_data/豆一主力合约历史价格数据.xlsx` - 豆一主力合约价格数据
- `processed_data/豆油主力合约历史价格数据.xlsx` - 豆油主力合约价格数据
- `processed_data/菜粕主力合约历史价格数据.xlsx` - 菜粕主力合约价格数据
- `processed_data/菜油主力合约历史价格数据.xlsx` - 菜油主力合约价格数据
- `processed_data/棕榈油主力合约历史价格数据.xlsx` - 棕榈油主力合约价格数据

**执行命令**：
```bash
python 01_data_preprocessing.py
```

#### 2. 计算比值/差值 (`02_calculate_metrics.py`)

**功能**：
- 从 `processed_data` 文件夹读取所有品种的主力合约价格数据
- 提取收盘价数据
- 计算多个品种对的价格比值或差值（每对只计算一种）：
  - 豆一与豆二：差值（豆一 - 豆二）
  - 豆油与豆粕：比值（豆油 / 豆粕）
  - 豆粕与菜粕：差值（豆粕 - 菜粕）
  - 菜油与豆油：差值（菜油 - 豆油）
  - 菜油与菜粕：比值（菜油 / 菜粕）
  - 豆油与棕榈油：差值（豆油 - 棕榈油）
- 为每个品种对绘制价格对比图（价格走势 + 差值或比值走势）
- 为每个品种对绘制概率分布统计图
- 保存到 `metrics_data` 文件夹

**输出文件**（每个品种对生成独立文件）：
- `metrics_data/豆一与豆二_价格差值数据.xlsx`
- `metrics_data/豆一与豆二_价格对比图.png`
- `metrics_data/豆一与豆二_概率分布统计图.png`
- `metrics_data/豆油与豆粕_价格比值数据.xlsx`
- `metrics_data/豆油与豆粕_价格对比图.png`
- `metrics_data/豆油与豆粕_概率分布统计图.png`
- `metrics_data/豆粕与菜粕_价格差值数据.xlsx`
- `metrics_data/豆粕与菜粕_价格对比图.png`
- `metrics_data/豆粕与菜粕_概率分布统计图.png`
- `metrics_data/菜油与豆油_价格差值数据.xlsx`
- `metrics_data/菜油与豆油_价格对比图.png`
- `metrics_data/菜油与豆油_概率分布统计图.png`
- `metrics_data/菜油与菜粕_价格比值数据.xlsx`
- `metrics_data/菜油与菜粕_价格对比图.png`
- `metrics_data/菜油与菜粕_概率分布统计图.png`
- `metrics_data/豆油与棕榈油_价格差值数据.xlsx`
- `metrics_data/豆油与棕榈油_价格对比图.png`
- `metrics_data/豆油与棕榈油_概率分布统计图.png`

**执行命令**：
```bash
python 02_calculate_metrics.py
```

#### 3. 季节性规律分析 (`03_seasonal_analysis.py`)

**功能**：
- 从 `metrics_data` 文件夹读取各品种对的比值或差值数据
- 为每个品种对统计概率分布
- 为每个品种对分析季节规律（按月份统计）
- 为每个品种对生成统计图表
- 保存到 `seasonal_analysis` 文件夹

**输出文件**（每个品种对生成独立文件）：
- `seasonal_analysis/豆一与豆二_差值概率分布图.png`
- `seasonal_analysis/豆一与豆二_差值季节规律图.png`
- `seasonal_analysis/豆一与豆二_统计结果.xlsx`
- `seasonal_analysis/豆油与豆粕_比值概率分布图.png`
- `seasonal_analysis/豆油与豆粕_比值季节规律图.png`
- `seasonal_analysis/豆油与豆粕_统计结果.xlsx`
- `seasonal_analysis/豆粕与菜粕_差值概率分布图.png`
- `seasonal_analysis/豆粕与菜粕_差值季节规律图.png`
- `seasonal_analysis/豆粕与菜粕_统计结果.xlsx`
- `seasonal_analysis/菜油与豆油_差值概率分布图.png`
- `seasonal_analysis/菜油与豆油_差值季节规律图.png`
- `seasonal_analysis/菜油与豆油_统计结果.xlsx`
- `seasonal_analysis/菜油与菜粕_比值概率分布图.png`
- `seasonal_analysis/菜油与菜粕_比值季节规律图.png`
- `seasonal_analysis/菜油与菜粕_统计结果.xlsx`
- `seasonal_analysis/豆油与棕榈油_差值概率分布图.png`
- `seasonal_analysis/豆油与棕榈油_差值季节规律图.png`
- `seasonal_analysis/豆油与棕榈油_统计结果.xlsx`

**执行命令**：
```bash
python 03_seasonal_analysis.py
```

#### 4. 比值/差值回归时间测试 (`04_test_ratio_reversion_time.py`)

**功能**：
- 测试不同品种对的价格比值或差值从指定入场值回归到目标值所需的时间
- 支持所有6个品种对的分析
- 统计回归时间的分布特征
- 检测回归过程中是否涉及主力合约月份或合约名称的改变

**配置参数**：
在脚本开头的配置区域修改以下参数：

```python
# 品种对选择（可选值：1-6）
# 1: 豆一与豆二, 2: 豆油与豆粕, 3: 豆粕与菜粕, 4: 菜油与豆油, 5: 菜油与菜粕, 6: 豆油与棕榈油
PAIR_SELECTION = 2

# 指标类型选择（可选值：'ratio' 或 'diff'）
# 'ratio': 比值, 'diff': 差值
METRIC_TYPE = 'ratio'

# 入场值（开始持仓的值）
ENTRY_VALUE = 2.98

# 出场值（目标回归值）
EXIT_VALUE = 2.75
```

**回归方向说明**：
- 入场值 > 出场值：等待指标下降到出场值以下（如比值从3.0回归到2.75，即降低到2.75以下）
- 入场值 < 出场值：等待指标上升到出场值以上（如比值从1.8回归到2.0，即升高到2.0以上）

**配置示例**：

示例1：测试豆油与豆粕比值从2.98回归到2.75的时间（降低到2.75以下）
```python
PAIR_SELECTION = 2
METRIC_TYPE = 'ratio'
ENTRY_VALUE = 2.98
EXIT_VALUE = 2.75
```

示例2：测试菜油与豆油差值从100回归到50的时间（降低到50以下）
```python
PAIR_SELECTION = 4
METRIC_TYPE = 'diff'
ENTRY_VALUE = 100
EXIT_VALUE = 50
```

示例3：测试豆一与豆二差值从-50回归到0的时间（升高到0以上）
```python
PAIR_SELECTION = 1
METRIC_TYPE = 'diff'
ENTRY_VALUE = -50
EXIT_VALUE = 0
```

**输出文件**：
- `{品种对}_{指标类型}_回归时间结果.xlsx` - 详细的回归周期数据和统计信息
  - 详细结果工作表：每个入场时点的详细信息（入场日期、入场值、出场日期、出场值、持仓天数、合约变化信息）
  - 统计信息工作表：回归时间的统计分析（平均值、中位数、最短/最长持仓天数、标准差、各分位数）

**合约变化检测**：
- 自动读取 `processed_data` 文件夹中的主力合约历史价格数据
- 检测回归过程中每个品种的合约名称变化
- 在Excel输出中包含以下列：
  - `{品种}_合约变化`：是否发生合约变化（是/否）
  - `{品种}_合约列表`：回归期间涉及的所有合约名称
  - `{品种}_变化详情`：合约变化的具体日期和变化情况

**执行命令**：
```bash
conda run -n graph-rag-agent-master python 04_test_ratio_reversion_time.py
```

**注意事项**：
1. 确保 `metrics_data` 文件夹中存在对应品种对的数据文件
2. 数据文件命名格式：`{品种对}_价格差值数据.xlsx` 或 `{品种对}_价格比值数据.xlsx`
3. 入场值和出场值的设置应该基于实际数据范围

#### 5. 数据更新 (`05_update_data.py`)

**功能**：
- 使用Selenium从东方财富网自动爬取最新的期货数据
- 支持7个品种的数据更新（菜油、菜粕、豆油、豆粕、豆一、豆二、棕榈油）
- 增量更新到 `processed_data` 文件夹的主力合约历史价格数据Excel文件
- 自动检查运行时间（建议在15:01-20:00之间运行）
- 检查上一个交易日数据是否存在，提醒可能缺失的数据
- 自动格式化数据以匹配现有Excel文件格式
- 支持数据覆盖更新（如果日期已存在）

**数据来源**：
- 菜油：https://quote.eastmoney.com/qihuo/OIM.html
- 菜粕：https://quote.eastmoney.com/qihuo/RMM.html
- 豆油：https://quote.eastmoney.com/qihuo/Ym.html
- 豆粕：https://quote.eastmoney.com/qihuo/mm.html
- 豆一：https://quote.eastmoney.com/qihuo/am.html
- 豆二：https://quote.eastmoney.com/qihuo/bm.html
- 棕榈油：https://quote.eastmoney.com/qihuo/pm.html

**爬取字段**：
- 商品名称、交易日期、合约名称
- 前结算价、开盘价、最高价、最低价、收盘价、结算价
- 涨跌、涨跌1
- 成交量(手)、持仓量、持仓量变化
- 成交额(万元)

**执行命令**：
```bash
conda run -n graph-rag-agent-master python 05_update_data.py
```

**注意事项**：
1. 建议在15:01-20:00之间运行，此时间段外数据可能不准确
2. 如果某个日期的数据已存在，程序会询问是否需要更新
3. 程序会自动检查上一个交易日数据，如果间隔超过3天会发出警告
4. 需要安装Selenium和Chrome浏览器驱动
5. 数据会自动格式化（千位分隔符、小数位数）以匹配现有Excel格式

**依赖要求**：
```bash
pip install selenium pandas openpyxl
```

## 完整执行流程

```bash
# 步骤1: 数据预处理
python 01_data_preprocessing.py

# 步骤2: 计算比值/差值
python 02_calculate_metrics.py

# 步骤3: 季节性规律分析
python 03_seasonal_analysis.py

# 步骤4: 比值/差值回归时间测试（可选，需要先配置参数）
conda run -n graph-rag-agent-master python 04_test_ratio_reversion_time.py

# 步骤5: 数据更新（可选，用于更新最新的期货数据）
conda run -n graph-rag-agent-master python 05_update_data.py
```

## 依赖要求

- Python 3.7+
- pandas
- numpy
- matplotlib
- openpyxl
- selenium（05_update_data.py需要）

安装依赖：
```bash
pip install pandas numpy matplotlib openpyxl selenium
```

## 注意事项

1. **执行顺序**：必须按照 01 → 02 → 03 的顺序执行，因为每个模块依赖前一个模块的输出
2. **数据准备**：确保 `ori_data` 文件夹中有完整的原始数据文件（豆一、豆二、豆粕、豆油、菜粕、菜油、棕榈油，年份范围2018-2026）
3. **文件夹结构**：程序会自动创建输出文件夹，无需手动创建
4. **数据格式**：原始数据文件应包含日期、合约、收盘价、持仓量等必要字段
5. **主力合约确定**：所有品种（豆一、豆二、豆粕、豆油、菜粕、菜油、棕榈油）均使用豆二分析出的主力合约月份，确保品种间的一致性

## 模块说明

### 01_data_preprocessing.py
- **主力合约分析**：以豆二为参考，基于持仓量最大原则分析每个交易日的主力合约
- **合约月份提取**：从合约代码中提取YYMM格式的月份
- **主力合约约束**：确保主力合约不会从较晚月份迁移到较早月份
- **多品种处理**：处理豆一、豆二、豆粕、豆油、菜粕、菜油、棕榈油七个品种，所有品种使用豆二的主力合约月份
- **数据年份**：支持2018-2026年的数据

### 02_calculate_metrics.py
- **品种对分析**：分析6个品种对的关系（每对只计算一种指标）：
  - 豆一与豆二：差值（豆一 - 豆二）
  - 豆油与豆粕：比值（豆油 / 豆粕）
  - 豆粕与菜粕：差值（豆粕 - 菜粕）
  - 菜油与豆油：差值（菜油 - 豆油）
  - 菜油与菜粕：比值（菜油 / 菜粕）
  - 豆油与棕榈油：差值（豆油 - 棕榈油）
- **价格对比图**：两个subplot，价格图与差值/比值图各占50%
- **概率分布图**：包含直方图和箱线图
- **独立输出**：每个品种对生成独立的数据文件和图表

### 03_seasonal_analysis.py
- **多品种对支持**：为每个品种对进行独立的季节性分析
- **概率分布统计**：统计每个品种对比值或差值的整体概率分布
- **季节规律分析**：分析每个品种对比值或差值的季节规律（按月份统计）
- **图表生成**：为每个品种对生成概率分布图和季节规律图表
- **统计结果**：保存每个品种对的详细统计结果到Excel文件

## 备份说明

所有原始代码和结果文件已备份到 `backup_*` 文件夹中，包括：
- 所有Python代码文件
- proportion文件夹（比值分析结果）
- difference文件夹（差值分析结果）
- comparison文件夹（价格对比图）
- main_continuous文件夹（原主力合约数据）
