# CrossProfit AI

接在 ERP 之后的活动决策层。妙手 ERP 是上游数据源；本系统帮助商家在报名前判断一场活动扣除全部成本后是否值得参加。

主路径只需三步：录入商品和实际成本 → 粘贴活动规则并确认折扣、费率与预计销量 → 查看单件利润、盈亏平衡点和风险结论。无需上传文件或取得平台 API 授权。结算单对账是可选的精度验证：愿意导入账单的商家，可用本店铺实测数据校准场景；没有账单也能完成主路径。

> 平台内置费率全部标记为 **DEMO DEFAULT**，仅用于离线演示，不代表 TikTok Shop、Amazon 或其他平台的当前官方费率。请按国家、站点、类目与卖家协议覆盖。

## 核心功能

- `/products` 管理商品、采购与包装成本、平台费用及店铺历史指标；`/analysis` 在报名前输入活动规则并计算；`/quick` 保留为辅助单品测算工具
- 独立商家账号；邮箱验证码注册、一次性验证码登录、密码登录和密码找回；两种登录方式都要求一次性图片验证码；商品、活动、分析和密钥按商家隔离
- 可选的 TikTok Shop 与 Amazon 结算单导入与对账，用于验证精度和积累本店铺校准样本
- 中文和英文界面、商家独立的 DeepSeek API Key、按平台保存历史访客/订单/退货数据
- TikTok Shop 与 Amazon 演示费率配置；其他平台由商家输入真实成本与费率
- 粘贴活动规则文本后进行确定性字段提取，缺失费用由商家确认
- 商品本体与多平台成本配置分离
- Decimal 确定性盈利引擎：折扣、佣金、采购、包装、物流、关税、支付、汇损、退货、其他费用及补贴
- 单件盈亏平衡价、固定成本存在时的盈亏平衡销量
- 5 档风险结论、成本瀑布图；有足够对账样本时给出实测分位数场景，否则仅展示成本敏感性
- 规则驱动策略建议和多活动横向排名；归档时冻结输入、费率来源、生效日期与引擎版本
- CSV 列映射预览、订单 SKU 关联、公式正确性与预测有效性分开报告，四 Sheet XLSX 对账报告
- CSV 与四 Sheet XLSX 报告
- 中英文 Next.js 界面、保留的 Streamlit 单机界面、FastAPI 与 SQLite
- DeepSeek 或 OpenAI 可选补充定性建议；没有 API Key 或调用失败时保留规则建议，利润计算始终由确定性引擎完成

企业反馈的逐项答复、妙手 ERP 接口与真实账单验证方案见 [docs/enterprise-feedback-plan.md](docs/enterprise-feedback-plan.md)。已找到公开业务接口文档，但尚未取得卖家授权、真实账单或访谈，不能将 Demo 结果视为真实业务验证。

首次使用可按 [docs/how-to-use.md](docs/how-to-use.md) 操作；它说明单品测算与活动分析的分工，以及商品、平台费用配置、活动规则和归档之间的关系。

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

浏览器打开 `http://127.0.0.1:3000`。统一入口会同时启动 Next.js 与 FastAPI（`http://127.0.0.1:8000`），首次运行自动创建 SQLite。前端默认通过同源 `/api` 代理调用后端。注册前须配置 QQ 邮箱授权码；本机调试时也可在测试中替换邮件发送器。

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
export CROSSPROFIT_SECRET_KEY="<持久随机密钥>"
export CROSSPROFIT_COOKIE_SECURE=0 # 生产 HTTPS 环境设为 1
export QQ_EMAIL="<发件 QQ 邮箱>"
export QQ_EMAIL_AUTH_CODE="<QQ 邮箱 SMTP 授权码>"
export CROSSPROFIT_PORT=8501
export CROSSPROFIT_API_PORT=8000
export CROSSPROFIT_WEB_PORT=3000
export NEXT_PUBLIC_API_URL="http://127.0.0.1:8000"
```

生产环境必须配置持久的 `CROSSPROFIT_SECRET_KEY` 和 HTTPS Cookie。可在登录后的“设置”中保存商家自己的 DeepSeek Key；密钥在数据库中加密保存，接口只返回配置状态。DeepSeek 仅补充定性建议并保留确定性 fallback；利润数始终由确定性引擎计算。建议定期备份数据库和密钥；旧版商家连接凭据仍保存在数据库中。

冷启动路径是录入商品与成本、粘贴活动规则、确认活动费率并查看利润结论。活动费率以商家店铺协议为准。平台 API 是后期优化，不是使用前提。旧平台连接数据保留在数据库中，不再提供凭据录入入口。

可选精度验证：先在“活动分析”填写费率来源和生效日期并归档；在“精度验证”选该快照，上传不超过 5 MB、10,000 行的 CSV。界面会识别 UTF-8 BOM 或 GBK，要求把订单 ID、SKU、结算时间、币种、收入及费用列映射到系统口径。费用为负数的导出可逐列选择反转符号。预览列出未识别列与未映射费项；确认后才保存文件解析结果并运行对账。报告分开显示公式正确性和销量、退货率预测偏差。未知列或缺少可核对费项时公式结论为 `PARTIAL`；未取得真实样单前，不宣称已通过实账验证。

“组合分析”可选同平台、同币种的多个 SKU，按各商品的预计销量计算边际贡献，报名费、广告预算、素材费和达人固定费在组合上只扣一次。场景校准按商家、平台、类目及最近 90 天的对账报告计算；至少 20 单且来自 3 份报告才启用实测分位数。样本不足时不提供销量预测区间，只展示由当前输入推导的物流和退货率成本敏感性。

## Demo Mode

本机可通过测试数据生成器体验以下案例。线上新注册商家不会自动看到其他账号或旧演示数据：

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
- `GET /auth/captcha`、`POST /auth/code`、`POST /auth/register`、`POST /auth/login`、`POST /auth/login/code`、`POST /auth/reset-password`、`GET /auth/me`、`POST /auth/logout`
- `GET/POST /historical-metrics`、`GET/PUT /ai/key`
- `GET/POST /products`、`GET/PUT/DELETE /products/{id}`
- `POST /products/{id}/platform-configs`
- `GET/POST /activities`、`GET /activities/{id}`
- `POST /activities/parse`
- `POST /analysis/profit`
- `POST /analysis/compare`
- `POST /analysis/portfolio`
- `GET /forecasts`、`POST /settlements/import`、`POST /settlements/confirm`
- `POST /reconciliation/run`、`GET /reconciliation`、`GET /reconciliation/{id}`、`GET /reconciliation/{id}/export`
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

测试覆盖盈利/亏损、折扣、零佣金、高退货、达人佣金、平台/物流补贴、关税策略、盈亏平衡价和量、缺失字段默认、金额精度、场景、平台差异、文本规则解析与 API。

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
│       ├── promotion_parser.py  文本活动规则解析
│       ├── platforms/       平台 Adapter
│       ├── llm/             OpenAI/Mock provider
│       └── export_service.py
├── frontend/streamlit_app.py
├── web/                     Next.js 14 / TypeScript / Tailwind / shadcn 主界面
│   └── src/app/             Dashboard、分析、对比、商品、历史、导出、设置
├── tests/                   单元与集成测试
├── docs/                    架构与比赛演示脚本
├── data/                    运行时 SQLite
├── run.py                   统一启动 FastAPI + Next.js
├── run_streamlit.py         启动保留的 Streamlit 界面
└── run_web.py               统一服务进程管理
```

详见 [docs/architecture.md](docs/architecture.md)。

## 隐私与安全

- 核心财务计算与 SQLite 数据均在本地。
- 若启用 OpenAI，只应发送活动理解和建议所需的最小字段，不上传完整店铺数据；利润数字不交给模型生成或修改。

## 已知限制

- 平台规则与费率不是实时同步；需卖家确认。
- 未积累足够对账样本时不提供销量预测区间，只提供基于商家输入的成本敏感性。
- 规则解析覆盖中英文常见折扣、佣金、销量和日期表达，不等同于生产级文档理解。
- 当前单币种活动内计算，不进行实时汇率换算；汇损用配置比例估算。
- CSV 列名随站点和导出版本变化，需要在导入时确认映射；多件订单和调整行应先核对 `gross_revenue` 口径。

## 截图占位

比赛提交前建议补充：Dashboard、盈利结论与瀑布图、成本敏感性、多活动对比、Excel 报告截图。

## 未来规划

- 接入经用户授权的平台官方活动与订单 API，并维护分站点/类目版本化费率
- OCR/PDF 活动规则解析、币种换算、税务规则包
- 团队协作、审计日志
- 云部署、鉴权与加密密钥管理
