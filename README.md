# 比特币定投机器人 - 基于AHR999指标

![Pic](./dashboard_comprehensive.png)

## 这是什么？

这是一个**自动买比特币**的程序。它每天在OKX交易所自动帮你买一点比特币，不是固定金额，而是根据价格高低智能调整买入金额。

简单说：**比特币便宜的时候多买点，贵的时候少买点或不买。**

### 投资什么？
- **标的**：比特币（BTC）
- **交易所**：OKX现货市场
- **方式**：市价买入（用USDT买BTC）

### 钱怎么动？

程序会根据"AHR999指标"来决定每天投多少钱。你需要设置一个**基准金额**（比如每天5美元），然后程序会根据市场情况调整：

**举个例子**（假设你设置基准金额是5美元）：
- 比特币很便宜时（AHR999 < 0.45）：买 **$20**（4倍基准）
- 比特币比较便宜（AHR999 ≈ 0.7）：买 **$10**（2倍基准）
- 比特币价格正常（AHR999 ≈ 1.0）：买 **$5**（1倍基准）
- 比特币有点贵（AHR999 ≈ 1.5）：买 **$2**（0.4倍基准）
- 比特币太贵了（AHR999 > 2.0）：**不买**（等便宜了再说）

**资金范围**：每天投入金额在 **0到4倍基准金额** 之间浮动。如果你设置基准是$10，那么单日最少$0，最多$40。

### 什么是AHR999？

AHR999是一个判断比特币贵不贵的指标，数值越小说明越便宜。它通过比较：
1. 当前价格 vs 过去200天的平均价格
2. 当前价格 vs 比特币的"理论增长价格"

这个指标由国内比特币玩家"ahr999"发明，在币圈比较有名。

### 为什么要这样投？

对比传统定投（每天固定买$5）：
- 传统方式：不管价格高低，每天都买$5
- AHR999方式：在便宜的时候多买（比如$15），贵的时候少买或不买

**实际效果**：长期来看，这种方式能拿到更低的平均成本，收益通常比傻傻地固定定投要好。

---

## 功能说明

- **全自动交易**：通过GitHub Actions免费云服务器，每天自动运行
- **可视化图表**：自动生成7张图表，包括收益曲线、持仓变化、策略对比等
- **交易记录**：所有买入记录保存在CSV文件，方便导出分析
- **运行报告**：每次运行结果会自动发到GitHub Issue

---

## 快速开始（新手向）

### 你需要准备什么？

1. 一个GitHub账号（免费注册：https://github.com/signup）
2. 一个OKX交易所账号（注册地址：https://www.okx.com，建议用邀请码 **35373898** 可省20%手续费）
3. OKX账户里有点USDT（建议至少$20起步）
4. 完成OKX实名认证

大概需要15分钟完成配置，**完全免费运行**（GitHub Actions提供免费额度）。

### 配置步骤

#### 第一步：Fork这个项目

1. 点击页面右上角的 **Fork** 按钮
2. 选择你的GitHub账号
3. 等几秒钟，你的账号下就会有这个项目的副本了
4. 确认浏览器地址变成了：`github.com/你的用户名/DCA-with-ahr999`

Fork的意思就是复制一份到你自己的账号，之后所有操作都在你的副本里进行，不会影响原项目。

**⚠️ 重要：删除原CSV文件！**

Fork后，项目里的 `trade_log.csv` 是我（原作者）的交易记录，不是你的。**在运行Action之前，必须先删除这个文件**，否则你的交易数据会追加到我的记录里，图表和统计就全乱了。

删除方法：
1. 进入你Fork的项目
2. 点击 `trade_log.csv` 文件
3. 点击右上角的垃圾桶图标（Delete this file）
4. 点击"Commit changes"确认删除

删除后，程序第一次运行时会自动创建一个新的CSV文件，里面就只有你自己的交易记录了。

#### 第二步：获取OKX的API密钥

1. 登录OKX，点击右上角头像 → **API**（或直接访问 https://www.okx.com/account/my-api）
2. 点击"创建API"，选择"交易API"
3. 权限设置：
   - **读取**：勾选
   - **交易**：勾选
   - **提现**：不要勾选（安全考虑）
4. 设置一个密码短语（Passphrase），自己想一个，比如 `MyBot2024`
5. 完成验证后，会显示三个密钥：
   - **API Key**（一串以xxx开头的字符）
   - **Secret Key**（一串以xxx开头的字符）
   - **Passphrase**（就是你刚才设的密码短语）

**重要**：这些密钥只显示一次，立即保存到安全的地方（密码管理器或记事本），千万别发给别人。

#### 第三步：在GitHub配置密钥

1. 进入你Fork的项目，点击 **Settings**（顶部标签栏）
2. 左侧菜单找到 **Secrets and variables** → 点击 **Actions**
3. 点击 **New repository secret**，依次添加三个密钥：

   **密钥1**：
   - Name：`OKX_API_KEY`
   - Secret：粘贴你的API Key

   **密钥2**：
   - Name：`OKX_SECRET_KEY`
   - Secret：粘贴你的Secret Key

   **密钥3**：
   - Name：`OKX_PASSWORD`
   - Secret：粘贴你的Passphrase

4. （可选）设置每日基准投资金额：
   - Name：`BASELINE_INVESTMENT`
   - Secret：输入数字，比如 `10` 表示基准$10/天
   - 不设置的话默认是$5/天

#### 第四步：启用自动运行

1. 点击项目顶部的 **Actions** 标签
2. 如果看到提示说"工作流未启用"，点击绿色按钮启用
3. 左侧找到 **Daily Investment Bot Runner**
4. 点击右上角 **Run workflow** → 选择 **main** 分支 → 再次点击 **Run workflow**
5. 等1-2分钟，刷新页面，看到绿色勾就是成功了

运行成功后，你会看到：
- 项目里出现了 `trade_log.csv` 文件（记录每次买入）
- 出现了 `dashboard_comprehensive.png` 图表
- **Issues** 标签页里有一条运行报告

**搞定！** 之后每天北京时间上午10点会自动运行。

### 修改运行时间（可选）

默认是每天上午10点运行，如果想改时间：

1. 打开项目里的 `.github/workflows/main.yml` 文件
2. 找到这行：`cron: '0 2 * * *'`
3. 改成你想要的时间（注意是UTC时区）：
   - 上午8点：`'0 0 * * *'`
   - 中午12点：`'0 4 * * *'`
   - 晚上10点：`'0 14 * * *'`
4. 点击"Commit changes"保存

### 常见问题

**Q：为什么没有买入？**
A：可能是当前AHR999指标显示价格太贵（>2.0），程序会自动跳过不买。这是正常的，等价格回落了自然会买。

**Q：钱会不会亏光？**
A：程序只会买入，不会卖出。最坏情况是比特币跌了，账面亏损，但币还在。而且便宜的时候会自动多买，长期能摊低成本。

**Q：怎么停止运行？**
A：进入Actions页面，点击工作流，右上角有"Disable workflow"按钮。或者直接删除GitHub里配置的OKX密钥。

**Q：我的交易记录别人能看到吗？**
A：如果你的项目是Public（公开），别人能看到你的交易记录CSV和图表。建议把项目改成Private（私有），或者把 `trade_log.csv` 和 `*.png` 添加到 `.gitignore` 文件里。

**特别提醒**：Fork之后记得先删除原作者的 `trade_log.csv` 文件，否则你的交易记录会混在原作者的数据里。

**Q：手续费怎么算？**
A：OKX现货交易手续费大概0.1%，用邀请码注册可以返佣20%。比如买$10的BTC，实际到手差不多$9.99。

**Q：API密钥安全吗？**
A：密钥配置在GitHub的Secrets里，别人看不到。而且我们只开启了读取和交易权限，没有提现权限，就算泄露也转不走币。

---

## 本地运行（懂点编程的可以看）

如果你想在自己电脑上跑，而不用GitHub Actions：

### 准备工作
- 安装Python 3.10或更高版本
- 有OKX账号和API密钥

### Windows系统

```powershell
# 下载项目
git clone https://github.com/xunyoyo/DCA-with-ahr999.git
cd DCA-with-ahr999

# 创建虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt

# 设置环境变量（改成你自己的密钥）
$env:OKX_API_KEY = "你的API_KEY"
$env:OKX_SECRET_KEY = "你的SECRET_KEY"
$env:OKX_PASSWORD = "你的PASSPHRASE"
$env:BASELINE_INVESTMENT = "10"  # 可选，默认5美元

# 运行
python trade_bot.py
```

### Mac/Linux系统

```bash
# 下载项目
git clone https://github.com/xunyoyo/DCA-with-ahr999.git
cd DCA-with-ahr999

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 设置环境变量（改成你自己的密钥）
export OKX_API_KEY="你的API_KEY"
export OKX_SECRET_KEY="你的SECRET_KEY"
export OKX_PASSWORD="你的PASSPHRASE"
export BASELINE_INVESTMENT="10"  # 可选，默认5美元

# 运行
python trade_bot.py
```

运行成功后会在当前目录生成 `trade_log.csv` 和图表文件。

---

## 进阶设置

### 图表主题

程序支持三种图表风格：
- `light`：白底简约风（默认）
- `midnight`：深色酷炫风
- `neon`：科技霓虹风

在GitHub配置：
- Name：`DCA_CHART_THEME`
- Secret：填 `light`、`midnight` 或 `neon`

本地运行加一行环境变量：
```bash
export DCA_CHART_THEME="midnight"
```

### 修改策略参数

如果你懂编程，想调整策略参数，可以编辑 `trade_bot.py` 文件的这几行：

```python
BASELINE_INVESTMENT = 5.0    # 基准金额
ALPHA = 1.5                  # 低价加倍系数（越大，便宜时买得越多）
BETA = 0.8                   # 高价减少系数（越大，贵的时候减得越快）
DAILY_CAP_X = 4.0           # 单日最高倍数（最多买几倍基准）
PAUSE_THRESHOLD = 2.0        # 暂停阈值（AHR999超过这个就不买）
```

**警告**：改参数有风险，建议先小金额测试。

---

## 项目结构

```
DCA-with-ahr999/
├── .github/workflows/
│   └── main.yml                    # GitHub Actions配置
├── trade_bot.py                    # 主程序
├── requirements.txt                # Python依赖
├── trade_log.csv                   # 交易记录（运行后生成）
├── dashboard_comprehensive.png     # 图表（运行后生成）
└── README.md                       # 说明文档
```

核心就是 `trade_bot.py`，它做这些事：
1. 从OKX获取比特币历史价格（过去250天）
2. 计算AHR999指标
3. 根据指标决定今天买多少
4. 如果要买，就下市价单
5. 记录到CSV文件
6. 生成图表
7. （如果在GitHub上运行）发个Issue汇报

---

## 故障排查

### 报错：`ModuleNotFoundError`
说明依赖没装好，重新跑：
```bash
pip install -r requirements.txt
```

### 报错：`Authentication failed`
API密钥配置错了，检查：
1. 密钥复制对了没（别有空格）
2. Passphrase设对了没
3. API密钥有没有过期

### 报错：`Insufficient balance`
USDT余额不够了，去OKX充值。

### Actions运行失败
1. 进Actions页面，点失败的记录，看详细日志
2. 通常是密钥配置问题
3. 也可能是OKX API网络问题，过会儿再试

---

## 风险提示

**认真读一下**：

1. **投资有风险**：比特币价格波动很大，可能亏钱，投资前想清楚
2. **只投闲钱**：别拿生活费或借钱来玩，只投亏了也不影响生活的钱
3. **不是理财建议**：这只是个开源工具，不保证赚钱，自己的决定自己负责
4. **API安全**：妥善保管API密钥，定期更换，不要开提现权限
5. **代码审查**：Fork之前可以看看代码，确保没有恶意操作
6. **市场风险**：策略基于历史数据，不代表未来，市场变化可能导致策略失效

---

## 贡献与反馈

欢迎提建议或报bug：
1. 提Issue：https://github.com/xunyoyo/DCA-with-ahr999/issues
2. 提PR：Fork后改代码，然后提Pull Request
3. 讨论交流：在Issues里聊聊你的改进想法

---

## 开源协议

MIT License - 随便用，随便改，但后果自负。

---

## 致谢

- AHR999指标由[@ahr999](https://weibo.com/ahr999)发明
- 感谢OKX提供API接口
- 感谢GitHub提供免费的Actions服务

祝定投顺利！记住：**投资需谨慎，闲钱慢慢投。**
