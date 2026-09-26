# CrossProfit AI 全面改造任务书

你在 `/Users/zombie/Desktop/跨境AI/crossprofit-ai` 工作。这是一个已运行的 FastAPI + Next.js 14 + SQLite 项目，`backend/app` 是后端，`web/src` 是前端主界面，`frontend/streamlit_app.py` 是保留的旧界面。先通读 `README.md`、`docs/enterprise-feedback-plan.md`、`backend/app/models/entities.py`、`backend/app/schemas/domain.py`、`backend/app/api/routes.py`、`backend/app/services/profit_engine.py`、`backend/app/services/scenario_engine.py`，再动手。

## 战略前提（决定所有取舍，先理解再改代码）

当前产品是一个正确但可替代的活动利润计算器。Excel 能做同样的计算，妙手 ERP 加一个页面也能做，所以"我算得对"不构成优势。

真正的结构性空档是：**没有任何工具做"事前预测 → 事后结算单对账 → 参数自校准"的闭环。** 妙手是事后记账系统，它从未在报名前做过预测，因此手里没有"预测 vs 实际"这组数据；外包分析公司人工滞后，对不起几百笔订单；Excel 算完就扔，没人回头核对当初拍的退货率对不对。

所以本次改造的唯一主线是：让系统积累每个店铺自己的实测参数，越用越准。这个资产不可迁移、随使用次数单调递增，是唯一守得住的东西。

关键约束：**不依赖任何平台 API 授权。** 卖家自己能从 Seller Center 导出结算单 CSV，这就是数据入口。项目此前因 TikTok 接口权限申请失败而受阻，本方案绕开该阻塞。

## 任务一：预测快照冻结（对账的前提）

现在 `POST /analysis/archive` 和 `POST /analysis/run` 归档时，只把结果塞进 `analysis_results.result_data` 这个 JSON 列，没有任何"输入快照"和"费率版本"语义。活动结束后无法回答"当初我们假设的费率是多少"。

改造：

- 新增表 `forecast_snapshots`：`id`、`merchant_id`（外键 merchants.id，索引）、`analysis_id`（外键 analysis_results.id）、`product_id`、`activity_id`、`snapshot_data`（JSON，存完整的 `ProfitAnalysisRequest` 序列化结果）、`engine_version`（String(32)）、`rate_source`（Text，费率来源说明）、`rate_effective_date`（Date，费率生效日期）、`frozen_at`（DateTime）、`locked`（Boolean，默认 True）。
- `ProfitAnalysisRequest` 新增可选字段 `rate_source: str | None` 和 `rate_effective_date: date | None`，走 `PlatformConfigInput` 或顶层都可以，你选一个更自然的位置并保持一致。
- `engine_version` 在 `backend/app/config.py` 的 `Settings` 里加一个常量 `engine_version: str = "1.0.0"`，公式改动时手动 bump。快照必须记录它，否则日后对账无法区分"公式改了"和"假设错了"。
- 归档后快照不可修改。若商家要改参数，产生一条新快照并在响应里说明这是第 N 次修订，不要覆盖历史。
- `POST /analysis/archive` 同一事务内写入快照。

## 任务二：结算单导入与逐项对账（本次改造的核心，目前完全缺失）

这是整个项目唯一真正的护城河，优先级最高，代码量也最大。

### 2.1 结算单解析

新建 `backend/app/services/reconciliation/` 目录：

- `base.py`：定义 `SettlementParser` 抽象基类和统一的中间表示 `SettlementLine`（Pydantic 模型）：`order_id`、`sku`、`settled_at`、`currency`、`gross_revenue`、`fee_items: dict[str, Decimal]`（费项名 → 金额）、`refund_amount`、`subsidy_amount`、`raw_row: dict`。
- `tiktok.py`、`amazon.py`：各自把平台结算 CSV 的列名映射到 `SettlementLine`。真实列名你无法确定，所以必须做成**可配置的列映射**：映射表放 JSON/YAML 配置，解析器读配置而不是硬编码列名，并在列缺失时报出"未识别的列"清单而非静默丢弃。
- `mapper.py`：把 `SettlementLine.fee_items` 里的平台费项名归一到引擎的费项口径（`平台佣金`、`达人佣金`、`支付手续费`、`物流成本`…，与 `profit_engine.py` 里 `raw_costs` 的 item 名严格一致）。**无法归一的费项不许丢弃、不许归零**，必须原样进入"未映射费项"列表。

### 2.2 对账引擎

新建 `backend/app/services/reconciliation/engine.py`：

输入一份 `forecast_snapshots` 记录 + 一批 `SettlementLine`，输出逐费项差异表。要求：

- 按 `order_id + sku` 关联，关联不上的订单单列为"无法映射"。
- 每个费项输出：预测值、实际值、绝对差额、相对差额。
- 差异归因分类，至少区分这几类，用枚举而非自由文本：`REFUND_TIMING`（退款时点）、`SUBSIDY`（补贴口径）、`TAX`（税费）、`ROUNDING`（舍入）、`FX`（币种换算）、`RATE_ERROR`（费率填错）、`FEE_ATTRIBUTION`（费用归属）、`UNMAPPED`（未映射）、`UNKNOWN`。
- 区分两个截然不同的结论，**不许混为一谈**：
  1. **公式正确性**：用相同的真实输入核对每个费用项。这里的验收标准是差额绝对值 ≤ 0.01 计价币种。
  2. **预测有效性**：预测销量、退货率与事后结果的偏差。销量预测偏差不是公式错误，报告里必须分开呈现。

### 2.3 数据模型与接口

- 新增表 `settlement_imports`：`id`、`merchant_id`、`platform`、`file_name`、`row_count`、`unmapped_count`、`imported_at`、`status`。
- 新增表 `reconciliation_reports`：`id`、`merchant_id`、`snapshot_id`（外键 forecast_snapshots.id）、`import_id`（外键 settlement_imports.id）、`formula_verdict`（String，PASS/FAIL/PARTIAL）、`max_fee_diff`（Numeric(12,4)）、`forecast_diff`（JSON，销量/退货率偏差）、`diff_data`（JSON，完整差异表）、`created_at`。
- 新增接口，全部挂在需要登录的 `router` 上并按 `merchant_id` 隔离：
  - `POST /settlements/import`（multipart 上传 CSV，返回解析预览 + 未识别列 + 未映射费项，**不立即入库**，让商家先确认）
  - `POST /settlements/confirm`（确认后入库）
  - `POST /reconciliation/run`（传 snapshot_id + import_id，跑对账）
  - `GET /reconciliation`、`GET /reconciliation/{id}`
- 导出：对账报告要能导出 XLSX，Sheet 结构为 `Summary` / `Fee Diff` / `Unmapped` / `Forecast Accuracy`，复用 `backend/app/services/export_service.py` 的风格。

### 2.4 前端

`web/src/app/` 下新增 `reconciliation/page.tsx`，流程为：选择已归档分析 → 上传结算单 → 确认列映射 → 查看差异表。差异表要突出显示超阈值的费项。沿用现有 shadcn 组件和 `web/src/lib/api.ts` 的调用风格，中英文双语走现有 `auto-translations.json` 机制。

## 任务三：参数自校准，替掉硬编码假设

`backend/app/services/scenario_engine.py` 的 `definitions` 目前是写死的 `("乐观", 1.20, -0.03, 0.95)` 之类的占位值。这是演示数据，不是分析。

改造：

- 新增表 `calibrated_parameters`：`id`、`merchant_id`、`platform`、`category`（String，类目）、`parameter`（String，如 `return_rate`、`sales_multiplier`）、`p25`/`p50`/`p75`（Numeric）、`sample_size`（Integer）、`window_days`（Integer）、`updated_at`。
- 新建 `backend/app/services/calibration.py`：从该商家该平台该类目的历史 `reconciliation_reports` 里算实测分布分位数，写入上表。
- `ScenarioEngine` 改为优先读 `calibrated_parameters`，读不到才退回当前硬编码值，并在 `ScenarioResult` 上新增字段 `sample_size: int | None` 和 `source: Literal["calibrated", "default"]`。
- **样本不足时必须显式说"样本 N 单，区间不可信"**，不许给一个假装精确的数字。前端也要显示样本量。这一条是信任的来源，不能省。
- `ProfitResult.assumptions` 里，凡是用了自校准参数的，要写明来源、样本量和统计窗口。

## 任务四：多 SKU 组合分析

引擎目前一次只算一个商品一个活动，而真实场景是"选 30 个 SKU 报这场活动"。`POST /analysis/compare` 是多活动横向排名，不是这个东西。Excel 在组合层面最吃力，这里最容易做出体感差异。

- 新增 `POST /analysis/portfolio`：接受一个活动 + 多个 SKU（每个 SKU 带自己的 `PlatformConfigInput` 与预计销量），返回组合层面的总利润、加权利润率、风险分布，以及**应当剔除的 SKU 列表**（按边际贡献排序，标出拖累组合的那些）。
- 固定成本（`registration_fee`、`ad_budget`、`creative_cost`、`creator_fixed_fee`）在组合层面只计一次，不能每个 SKU 重复扣。这是最容易算错的地方，写测试覆盖。
- 前端在 `web/src/app/analysis/` 或新建页面里支持多选 SKU。

## 任务五：收窄范围，删掉负资产

这两块在演示和商务场合是减分项，一问就露。

- **平台连接收窄**：`README.md` 自己写了"凭据已保存，不表示平台授权已通过"。8 个平台（淘宝、拼多多、抖音、闲鱼、TikTok、Amazon、Temu、SHEIN、妙手）目前只是存凭据。收窄到 TikTok Shop + Amazon 两个真正做通对账，其余从 `web/src/app/connections/page.tsx` 和 `GET /platform-catalog` 的默认列表里下架。已存数据不删，加迁移标记为 `deprecated` 即可。
- **删掉公开网页调研模块**：移除 `backend/app/services/research_analysis.py`、`POST /analysis/research`、以及 `tests/test_research_analysis.py`。理由：利润数字的确定性是本产品的核心优点，拼贴公开网页的 AI 定性分析反而稀释它。DeepSeek 的定性增强保留在 `strategy_engine.py` 里即可（它有确定性 fallback）。
- 定位口径改写：`README.md` 里把妙手 ERP 表述为**上游数据源**，不是竞品。本产品是"接在 ERP 之后的活动决策与对账层"。冷启动路径明确为 CSV 导入，接入成本压到 5 分钟以内，平台 API 列为后期优化而非前置依赖。

## 工程要求

- 金额一律用 `Decimal`，沿用 `profit_engine.py` 里的 `money()`/`rate()` 量化函数和 `ROUND_HALF_UP`。不许出现 `float` 参与财务计算。
- 所有新接口挂在 `backend/app/api/routes.py` 的 `router`（已带 `Depends(require_merchant)`），每个查询都必须过滤 `merchant_id`。现有代码的隔离模式照抄，不要发明新写法。
- SQLite 没有迁移框架，项目靠 `database.py` 建表。新表按同样方式创建；对已有表加列时写一个幂等的 `ALTER TABLE` 兼容脚本放 `scripts/`，老库能平滑升级。
- CSV 上传要有大小上限、编码探测（结算单常见 UTF-8 BOM 和 GBK）、以及行数上限，解析失败给出具体行号。
- 测试写在 `tests/` 下，沿用现有 `conftest.py`。新增至少：结算单解析、费项归一、对账差异归因、组合固定成本只计一次、自校准样本不足时的降级行为。CSV fixture 放 `tests/fixtures/`。
- 验证命令：`PYTHONPATH=. python -m pytest -q`，以及 `cd web && npm run typecheck && npm run lint && npm run build`。全部通过再报完成。

## 交付顺序

严格按此顺序，每步可独立验证后再进入下一步：

1. 任务一（快照冻结）— 没有它对账无从下手
2. 任务二（结算单导入与对账）— 核心，最大工作量
3. 任务五（删负资产）— 快，先清干净再叠新功能
4. 任务四（多 SKU 组合）
5. 任务三（参数自校准）— 依赖任务二积累的数据，最后做

每完成一步，报告改了哪些文件、测试结果、以及哪些地方你做了假设。**不确定的地方明确问，不要猜一个实现糊过去** —— 尤其是平台结算单的真实列名，那个必须做成可配置而不是猜。
