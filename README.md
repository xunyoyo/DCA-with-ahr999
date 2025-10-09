# AHR999 Dollar-Cost Averaging Bot

Automates a daily Bitcoin dollar-cost averaging strategy on OKX, enhanced with the AHR999 indicator and a rich visual dashboard.

## ✨ 项目亮点
- **智能买入**：基于 AHR999 指标动态调整每日投入金额，自动下单至 OKX 现货市场。
- **可视化面板**：自动生成 ROI 曲线、资产净值曲线以及投入成本对比图，帮助快速洞察投资表现。
- **运营日志**：所有成交记录保存在 `trade_log.csv`，支持复盘与数据分析。
- **GitHub 自动同步**：运行结果自动推送到仓库 Issue，便于团队追踪与审计。

## 🏗️ 技术栈
- Python 3.10+
- [ccxt](https://github.com/ccxt/ccxt)：统一访问加密货币交易所 API
- pandas / numpy：数据处理与指标计算
- matplotlib：生成多张高分辨率数据可视化图表
- requests：与 GitHub API 通信

## ⚙️ GitHub Action 自动化
仓库自带 `Daily Investment Bot Runner` 工作流（位于 `.github/workflows/main.yml`），可在 GitHub 上按计划或手动运行：

### 运行方式
- **定时触发**：默认在每天 `02:00 UTC`（北京时间上午 10 点）执行，自动下载行情、下单、生成图表并推送 Issue。想调整时间，可修改 `cron: '0 2 * * *'`。
- **手动触发**：进入 GitHub 仓库的 **Actions ➜ Daily Investment Bot Runner**，点击 `Run workflow` 立即执行。

### 必要密钥配置
1. 打开仓库 `Settings ➜ Secrets and variables ➜ Actions`。
2. 新建下列 Repository secrets，用于授权交易与 Issue 写入：
   - `OKX_API_KEY`
   - `OKX_SECRET_KEY`
   - `OKX_PASSWORD`
   - `GITHUB_TOKEN`（需具备 `repo` 范围或使用默认 `GITHUB_TOKEN` 权限即可）

### 工作流步骤概览
```mermaid

    A[Checkout 仓库] --> B[安装 Python 3.10]
    B --> C[pip install -r requirements.txt]
    C --> D[运行 trade_bot.py]
    D --> E{有新日志/图表?}
    E -- 是 --> F[提交并推送变更]
    E -- 否 --> G[不提交]
```

> **提示**：工作流运行时会使用最新提交的代码，确保策略更新后的首个版本已推送到 `main` 分支。
## 🚀 安装与启动
```powershell
# 1. 克隆仓库
git clone https://github.com/xunyoyo/DCA-with-ahr999.git
cd DCA-with-ahr999

# 2. 创建并激活虚拟环境（可选）
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 4. 配置环境变量（Windows PowerShell 示例）
$env:OKX_API_KEY     = "<your_okx_api_key>"
$env:OKX_SECRET_KEY  = "<your_okx_secret>"
$env:OKX_PASSWORD    = "<your_okx_passphrase>"
$env:GITHUB_REPOSITORY = "<owner>/<repo>"
$env:GITHUB_TOKEN      = "<personal_access_token_with_repo_scope>"
# 可选：覆盖默认基准投入与主题
$env:BASELINE_INVESTMENT = "5"
$env:DCA_CHART_THEME     = "light"  # light | midnight | neon

# 5. 启动 bot（将尝试真实下单，请在模拟或小额度环境中先行验证）
python trade_bot.py
```

> **提示**：生产环境建议使用安全的 Secret 管理方案（CI/CD Secret、.env 文件等），勿将敏感信息写入源码。

## 📈 使用方法
1. 按上述步骤运行 `trade_bot.py`。程序会：
   - 拉取 OKX 现货 BTC/USDT 日线数据；
   - 计算 AHR999 指数并确定当日投入金额；
   - 若条件满足，提交市价买单并记录成交信息；
   - 更新 `trade_log.csv` 并生成三张图表：`roi_chart.png`、`equity_curve.png`、`value_vs_cost.png`；
   - 向 GitHub Issue 推送本次运行的摘要报告。
2. 想切换图表风格，可在运行前设置环境变量 `DCA_CHART_THEME`：
   - `light`（默认）：简约白底风格
   - `midnight`：暗黑仪表盘风格
   - `neon`：科技感霓虹风格
3. 图表与日志生成在项目根目录，可用于周报、复盘或进一步分析。

## 📂 项目结构
```
DCA-with-ahr999/
├── trade_bot.py        # 主程序，含策略逻辑与可视化
├── trade_log.csv       # 运行后生成的成交日志
├── requirements.txt    # Python 依赖列表
├── roi_chart.png       # ROI 曲线图（运行后生成）
├── equity_curve.png    # 资产净值曲线（运行后生成）
└── value_vs_cost.png   # 投入成本 vs. 当前价值图（运行后生成）
```

## 🤝 贡献指南
1. Fork 仓库并新建分支（如 `feature/my-awesome-improvement`）。
2. 为新功能编写必要的文档或测试。
3. 运行静态检查或单元测试，确保通过。
4. 提交 Pull Request，说明变更动机与实现细节。

## 📄 许可证
本项目采用 [MIT License](./LICENSE) 授权，细节请参阅许可证文本。

---
欢迎提交 Issue 或 PR 与我们交流想法，祝你投资顺利！
