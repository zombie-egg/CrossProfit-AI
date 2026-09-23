# CrossProfit AI

跨境电商促销活动盈利分析 AI 助手。它把活动规则、商品成本和平台费用统一成可追溯的财务口径，在卖家报名活动前回答：**扣掉所有真实成本后，这场活动到底赚不赚钱？**

> 平台内置费率全部标记为 **DEMO DEFAULT**，仅用于离线演示，不代表 TikTok Shop、Amazon 或其他平台的当前官方费率。请按国家、站点、类目与卖家协议覆盖。

## 核心功能

- `/quick` 单品手动测算：无需 TikTok / ERP 接口权限；输入实际费用与来源后使用确定性引擎计算，预览不自动归档
- TikTok Shop 与 Amazon 完整 Demo；Temu、SHEIN 可扩展 Adapter
- URL 安全读取、HTML 正文提取、规则结构化解析、抓取失败智能补录
- 商品本体与多平台成本配置分离
- Decimal 确定性盈利引擎：折扣、佣金、采购、包装、物流、关税、支付、汇损、退货、其他费用及补贴
- 单件盈亏平衡价、固定成本存在时的盈亏平衡销量
- 5 档风险结论、成本瀑布图、乐观/基准/悲观敏感性分析
- 规则驱动策略建议和多活动横向排名
- CSV 与四 Sheet XLSX 报告
- 中文 SaaS Next.js 比赛主界面、保留的 Streamlit 界面、FastAPI、SQLite 与离线演示数据
- DeepSeek 可选补充定性分析，OpenAI 可选辅助规则提取；没有 API Key 或调用失败时保留规则建议，利润计算始终由确定性引擎完成

企业反馈的逐项答复、Easyboss 接口缺口与真实账单验证方案见 [docs/enterprise-feedback-plan.md](docs/enterprise-feedback-plan.md)。目前尚未取得真实卖家账单、访谈或 Easyboss 业务接口文档，不能将 Demo 结果视为真实业务验证。

## 快速启动（比赛主界面）

要求 Python 3.11+ 与 Node.js 18+。

```bash
cd crossprofit-ai
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd web && npm install && cd ..
python run.py
```

浏览器打开 `http://127.0.0.1:3000`。统一入口会同时启动 Next.js 与 FastAPI（`http://127.0.0.1:8000`），首次运行自动创建 SQLite 并写入 Demo 数据。前端默认通过同源 `/api` 代理调用后端，不需要单独配置跨端口地址。

也可运行：

```bash
./run_web.sh
```

Windows 可双击或执行 `run_web.bat`。

macOS 已提供 `scripts/com.crossprofit.ai.plist`，可作为登录自启动服务使用；项目会在后台同时维持网页与 API 服务。

原 Streamlit 界面仍完整保留，可通过 `python run_streamlit.py` 或 `./run_dev.sh` 启动，默认地址为 `http://127.0.0.1:8501`。

## 可选环境变量

复制 `.env.example` 为 `.env`，或在 Shell 中设置：

```bash
export OPENAI_API_KEY="..."      # 可选
export OPENAI_MODEL="gpt-4.1-mini"
export DEEPSEEK_API_KEY="..."    # 可选；若同时配置，优先使用 DeepSeek
export DEEPSEEK_MODEL="deepseek-flash"
export CROSSPROFIT_PORT=8501
export CROSSPROFIT_API_PORT=8000
export CROSSPROFIT_WEB_PORT=3000
export NEXT_PUBLIC_API_URL="http://127.0.0.1:8000"
```

当前版本读取进程环境变量。未配置 Key 时 UI 会明确显示“规则分析模式”。DeepSeek 仅追加定性建议，不自动填充费用或改写利润数字；规则字段仍由传统解析器提取并需卖家核对。`GET /ai/status` 只返回服务端配置状态与模型名，不返回密钥。DeepSeek 请求仅发送计算结果摘要和原有建议；调用失败时退回规则建议。

## Demo Mode

在顶部点击“加载演示案例”，或进入“活动分析”后选择 Demo：

1. `TikTok Summer Mega Sale`：高流量、高佣金，利润安全边际被压缩。
2. `Amazon Prime Promotion`：折扣适中，利润相对健康。
3. `TikTok Creator Flash Sale`：30% 折扣、20% 达人佣金和固定投入，演示“销量越大，亏得越多”。

选择案例后可修改折扣、销量、佣金、物流、退货、补贴和固定投入，再点击“开始盈利分析”。

## FastAPI

Next.js 通过 FastAPI 使用同一 service layer；Streamlit 仍可直接调用服务层。API 可独立启动：

```bash
uvicorn backend.app.main:app --reload --port 8000
```

接口包括：

- `GET /health`
- `GET/POST /products`、`GET/PUT/DELETE /products/{id}`
- `POST /products/{id}/platform-configs`
- `GET/POST /activities`、`GET /activities/{id}`
- `POST /activities/parse`
- `POST /analysis/profit`
- `POST /analysis/compare`
- `POST /analysis/run`、`GET /analysis`
- `GET /analysis/{id}`
- `GET /ui/bootstrap`
- `GET /export/{id}`
- Swagger：`http://127.0.0.1:8000/docs`

## 测试

```bash
PYTHONPATH=. python -m pytest -q
cd web
npm run typecheck
npm run lint
npm run build
```

测试覆盖盈利/亏损、折扣、零佣金、高退货、达人佣金、平台/物流补贴、关税策略、盈亏平衡价和量、缺失字段默认、金额精度、场景、平台差异、HTML fixture 解析、抓取 fallback 与 API。

## 计算口径

活动价由原价与折扣方式确定。单件利润：

```text
活动成交价
- 平台佣金 - 活动额外佣金 - 达人佣金
- 采购 - 包装 - 物流 - 关税
- 支付手续费 - 汇率损耗 - 退货风险准备金 - 其他费用 - 卖家优惠券
+ 平台补贴 + 物流补贴
```

退货准备金不是简单的 `售价 × 退货率`，而是：

```text
退货率 ×（不可回收物流 + 包装 + 商品损耗 + 不可退平台手续费）
```

关税基数可选采购成本或成交价。盈亏平衡价通过把价格相关费率合并后解析线性方程获得；当费率合计达到或超过 100% 时返回“不可达”。固定活动成本（报名费、广告、素材、达人固定费）存在且单件贡献为正时，盈亏平衡量向上取整。

风险阈值集中配置：≥20% 强烈推荐；10%-20% 可以参加；3%-10% 谨慎参加；0%-3% 不建议参加；<0% 明确亏损。

## 架构

```text
crossprofit-ai/
├── backend/app/
│   ├── api/                 FastAPI 路由
│   ├── models/              SQLAlchemy 表
│   ├── schemas/             Pydantic 领域对象
│   └── services/
│       ├── profit_engine.py 确定性财务核心
│       ├── scenario_engine.py / strategy_engine.py
│       ├── promotion_parser.py / scraper/
│       ├── platforms/       平台 Adapter
│       ├── llm/             OpenAI/Mock provider
│       └── export_service.py
├── frontend/streamlit_app.py
├── web/                     Next.js 14 / TypeScript / Tailwind / shadcn 主界面
│   └── src/app/             Dashboard、分析、对比、商品、历史、导出、设置
├── tests/                   单元与集成测试、HTML fixtures
├── docs/                    架构与比赛演示脚本
├── data/                    运行时 SQLite
├── run.py                   统一启动 FastAPI + Next.js
├── run_streamlit.py         启动保留的 Streamlit 界面
└── run_web.py               统一服务进程管理
```

详见 [docs/architecture.md](docs/architecture.md)。

## 隐私与安全

- URL 只允许 HTTP/HTTPS，拒绝 localhost、环回、私网、链路本地、保留和组播地址；设置超时、User-Agent、响应类型与错误降级。
- 当前抓取器不跟随重定向，避免通过重定向绕过 SSRF 校验；遇到登录、反爬或动态页面时转为规则文本补录。
- 核心财务计算与 SQLite 数据均在本地。
- 若启用 OpenAI，只应发送活动理解和建议所需的最小字段，不上传完整店铺数据；利润数字不交给模型生成或修改。

## 已知限制

- 平台规则与费率不是实时同步；需卖家确认。
- 通用 HTTP 抓取不执行 JavaScript，不绕过登录、验证码或反爬。
- 规则解析覆盖中英文常见折扣、佣金、销量和日期表达，不等同于生产级文档理解。
- 当前单币种活动内计算，不进行实时汇率换算；汇损用配置比例估算。
- 无用户/权限系统，定位为单机比赛 MVP。

## 截图占位

比赛提交前建议补充：Dashboard、盈利结论与瀑布图、三情景分析、多活动对比、Excel 报告截图。

## 未来规划

- 接入经用户授权的平台官方活动与订单 API，并维护分站点/类目版本化费率
- Playwright 作为可选异步抓取队列，不成为主流程依赖
- OCR/PDF 活动规则解析、币种换算、税务规则包
- 历史实际销量回填与预测校准、团队协作、审计日志
- 云部署、鉴权与加密密钥管理
