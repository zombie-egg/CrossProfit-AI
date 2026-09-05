from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.app.config import settings
from backend.app.database import init_db, session_scope
from backend.app.models import AnalysisResult, Product, ProductPlatformConfig, PromotionActivity
from backend.app.schemas.domain import PlatformConfigInput, ProductInput, ProfitAnalysisRequest, PromotionActivityInput
from backend.app.services.demo_data import seed_demo_data
from backend.app.services.export_service import ExportService
from backend.app.services.factories import request_from_models
from backend.app.services.profit_engine import ProfitEngine
from backend.app.services.promotion_parser import PromotionParserService
from backend.app.services.scenario_engine import ScenarioEngine
from backend.app.services.strategy_engine import StrategyEngine

st.set_page_config(page_title="CrossProfit AI", page_icon="📈", layout="wide")
st.markdown("""
<style>
.stApp {background:#f5f7fb}.block-container{padding-top:1.4rem;max-width:1450px}
[data-testid="stMetric"]{background:white;border:1px solid #e7ecf3;border-radius:14px;padding:16px;box-shadow:0 3px 12px rgba(20,60,120,.05)}
.hero{background:linear-gradient(120deg,#075bd8,#2986ff);padding:28px 32px;border-radius:18px;color:white;margin-bottom:18px}
.hero h1{margin:0;font-size:2.1rem}.hero p{margin:.55rem 0 0;opacity:.9;font-size:1.06rem}
.cp-card{background:#fff;border:1px solid #e7ecf3;border-radius:14px;padding:18px;margin:8px 0}
.demo-note{background:#fff7e6;border-left:4px solid #f5a623;padding:10px 14px;border-radius:6px}
.good{color:#138a4b}.warn{color:#c87900}.bad{color:#d9363e}
</style>""", unsafe_allow_html=True)

init_db()
with session_scope() as session:
    seed_demo_data(session)


def d(value) -> Decimal:
    return Decimal(str(value))


def get_products():
    with session_scope() as session:
        return session.scalars(select(Product).options(selectinload(Product.platform_configs)).order_by(Product.id)).all()


def get_activities():
    with session_scope() as session:
        return session.scalars(select(PromotionActivity).order_by(PromotionActivity.id)).all()


def persist_analysis(product_id: int, activity_id: int, result, scenarios):
    with session_scope() as session:
        record = AnalysisResult(product_id=product_id, activity_id=activity_id, unit_profit=result.unit_profit, profit_margin=result.profit_margin, estimated_total_profit=result.estimated_total_profit, risk_level=result.risk_level, result_data={"result": result.model_dump(mode="json"), "scenarios": [x.model_dump(mode="json") for x in scenarios]})
        session.add(record)


def persist_activity(product_id: int, activity: PromotionActivityInput) -> int:
    common = {"extra_commission_rate", "creator_commission_rate", "shipping_subsidy", "seller_shipping_cost", "platform_subsidy", "coupon_amount", "return_rate_override", "registration_fee", "ad_budget", "creative_cost", "creator_fixed_fee"}
    with session_scope() as session:
        row = PromotionActivity(
            product_id=product_id, platform=activity.platform, activity_name=activity.activity_name, activity_type=activity.activity_type,
            source_url=activity.source_url, start_date=activity.start_date, end_date=activity.end_date, discount_type=activity.discount_type,
            discount_value=activity.discount_value, estimated_sales=activity.estimated_sales, currency=activity.currency, raw_text=activity.raw_text,
            parse_confidence=activity.parse_confidence, missing_fields=activity.missing_fields,
            parameters={key: str(getattr(activity, key)) for key in common if getattr(activity, key) is not None and getattr(activity, key) != 0},
        )
        session.add(row); session.flush()
        return row.id


def waterfall(result):
    costs = [x for x in result.breakdown if x.amount != 0]
    return go.Figure(go.Waterfall(
        orientation="v", measure=["absolute"] + ["relative"] * len(costs) + ["total"],
        x=["活动售价"] + [x.item for x in costs] + ["真实利润"],
        y=[float(result.selling_price)] + [-float(x.amount) for x in costs] + [float(result.unit_profit)],
        connector={"line": {"color": "#aab6c5"}}, increasing={"marker": {"color": "#1aaf67"}}, decreasing={"marker": {"color": "#ef5b5b"}}, totals={"marker": {"color": "#1769e0"}},
    )).update_layout(height=420, margin=dict(l=20, r=20, t=25, b=20), yaxis_title="USD / 单", showlegend=False)


def result_panel(request, result, scenarios, tips):
    color = "good" if result.profit_margin >= Decimal("0.10") else "warn" if result.profit_margin >= 0 else "bad"
    st.markdown(f"### {request.activity.activity_name}　<span class='{color}'>● {result.risk_label}</span>", unsafe_allow_html=True)
    cols = st.columns(5)
    cols[0].metric("活动成交价", f"${result.selling_price}", f"-${result.discount_amount} 折扣")
    cols[1].metric("单件真实利润", f"${result.unit_profit}")
    cols[2].metric("真实利润率", f"{result.profit_margin:.1%}")
    cols[3].metric("预计总利润", f"${result.estimated_total_profit}", f"{result.estimated_sales} 单")
    cols[4].metric("盈亏平衡活动价", f"${result.break_even_price or '不可达'}")
    if result.break_even_quantity:
        st.info(f"固定活动成本 ${result.fixed_cost}，预计销售至少 {result.break_even_quantity} 件覆盖固定投入。")
    elif result.fixed_cost == 0:
        st.info("当前活动主要为可变成本结构，单件盈利即整体正向。")
    if result.unit_profit < 0:
        st.error("销量增加不能解决负单件利润：每多卖一单，活动亏损会继续扩大。")
    tab1, tab2, tab3, tab4 = st.tabs(["成本拆解", "敏感性分析", "策略建议", "计算说明"])
    with tab1:
        st.plotly_chart(waterfall(result), width="stretch")
        pressure = sorted([x for x in result.breakdown if x.amount > 0], key=lambda x: x.amount, reverse=True)[:3]
        st.caption("主要利润压力：" + "　·　".join(f"{x.item} ${x.amount}" for x in pressure))
    with tab2:
        frame = pd.DataFrame([{"情景": s.name, "销量系数": f"{s.sales_multiplier:.0%}", "退货率": f"{s.return_rate:.1%}", "物流系数": f"{s.shipping_multiplier:.0%}", "单件利润": float(s.unit_profit), "利润率": f"{s.profit_margin:.1%}", "总利润": float(s.total_profit), "结论": "仍盈利" if s.profitable else "亏损"} for s in scenarios])
        st.dataframe(frame, hide_index=True, width="stretch")
        st.bar_chart(frame.set_index("情景")["总利润"], color="#1769e0")
        pessimistic = next(x for x in scenarios if x.name == "悲观")
        (st.success if pessimistic.profitable else st.warning)(f"悲观情况下：{'仍然盈利' if pessimistic.profitable else '会转为亏损'}（总利润 ${pessimistic.total_profit}）。")
    with tab3:
        for tip in tips:
            st.markdown(f"- {tip}")
    with tab4:
        st.dataframe(pd.DataFrame([{"项目": x.item, "公式": x.formula, "金额": float(x.amount), "说明": x.description} for x in result.breakdown]), hide_index=True, width="stretch")
        for assumption in result.assumptions:
            st.caption(f"假设：{assumption}")
    exporter = ExportService()
    c1, c2 = st.columns(2)
    c1.download_button("导出 CSV", exporter.to_csv(request, result), f"{request.activity.activity_name}.csv", "text/csv", width="stretch")
    c2.download_button("导出 Excel 报告", exporter.to_xlsx(request, result, scenarios, tips), f"{request.activity.activity_name}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")


st.sidebar.markdown("## CrossProfit AI")
page = st.sidebar.radio("导航", ["Dashboard", "活动分析", "活动对比", "商品管理", "历史记录", "设置"], label_visibility="collapsed")
st.sidebar.markdown("<div class='demo-note'><b>DEMO DEFAULT</b><br>内置费率仅用于演示，请根据站点、类目和卖家协议修改。</div>", unsafe_allow_html=True)
st.sidebar.caption("没有 API Key 也可完整运行 · 当前使用" + (" OpenAI 辅助模式" if settings.openai_api_key else "规则分析模式"))

st.markdown("<div class='hero'><h1>跨境活动盈利 AI 助手</h1><p>别只看平台流量，先算清这场活动到底赚不赚钱。</p></div>", unsafe_allow_html=True)

if page == "Dashboard":
    with session_scope() as session:
        pc = session.scalar(select(func.count(Product.id))) or 0
        ac = session.scalar(select(func.count(PromotionActivity.id))) or 0
        records = session.scalars(select(AnalysisResult).order_by(AnalysisResult.created_at.desc())).all()
    cols = st.columns(4)
    cols[0].metric("商品数", pc); cols[1].metric("可分析活动", ac); cols[2].metric("盈利分析", sum(1 for x in records if x.unit_profit > 0)); cols[3].metric("亏损分析", sum(1 for x in records if x.unit_profit < 0))
    st.subheader("30 秒看懂真实利润")
    st.markdown("<div class='cp-card'>活动规则 → 商品与平台成本 → 确定性利润计算 → 风险和敏感性 → 可执行策略。AI 负责理解和表达，Python 财务引擎负责每一分钱。</div>", unsafe_allow_html=True)
    if st.button("立即分析活动", type="primary", width="stretch"):
        st.session_state["jump_hint"] = True
        st.info("请在左侧进入「活动分析」，选择演示案例即可开始。")
    st.subheader("演示案例")
    for activity in get_activities():
        with st.container(border=True):
            st.markdown(f"**{activity.activity_name}**　`{activity.platform}`")
            st.caption(f"折扣 {activity.discount_value:.0%} · 预计 {activity.estimated_sales} 单")

elif page == "活动分析":
    products = get_products(); activities = get_activities()
    st.subheader("1 · 选择商品与活动获取方式")
    pmap = {f"{p.name} · {p.sku}": p for p in products}
    product = pmap[st.selectbox("商品", list(pmap))]
    mode = st.radio("活动来源", ["加载演示案例", "粘贴活动规则文本", "读取活动 URL"], horizontal=True)
    selected_activity = None
    parsed = None
    if mode == "加载演示案例":
        candidates = [a for a in activities if a.product_id == product.id]
        amap = {a.activity_name: a for a in candidates}
        if amap:
            selected_activity = amap[st.selectbox("演示活动", list(amap))]
    else:
        url = st.text_input("活动页面 URL", placeholder="https://...（读取失败会自动进入智能补录）") if mode == "读取活动 URL" else None
        text = st.text_area("活动规则文本（推荐同时粘贴，可提高识别率）", height=150, placeholder="例如：TikTok Summer Sale，折扣 25%，达人佣金 12%，预计销量 500...")
        if st.button("自动识别活动规则", type="primary"):
            parsed = PromotionParserService().parse(url=url, raw_text=text)
            st.session_state["parsed"] = parsed.model_dump(mode="json")
        if "parsed" in st.session_state:
            from backend.app.schemas.domain import ParsedPromotion
            parsed = ParsedPromotion.model_validate(st.session_state["parsed"])
            if parsed.fetch_warning: st.warning(parsed.fetch_warning)
            st.success(f"已识别 {len(parsed.recognized_fields)} 项 · 置信度 {parsed.activity.parse_confidence:.0%}")
            st.json(parsed.recognized_fields)
            if parsed.missing_suggestions:
                st.markdown("**仍建议补充（可填写、跳过或采用默认值）**")
                for item in parsed.missing_suggestions:
                    st.markdown(f"- **{item['label']}**：{item['reason']}　_默认：{item['default_action']}_")
    if selected_activity or parsed:
        base = selected_activity
        platform = base.platform if base else parsed.activity.platform
        configs = {c.platform: c for c in product.platform_configs}
        if platform not in configs:
            st.error(f"商品尚无 {platform} 平台成本配置，请先在商品管理中添加。")
        else:
            cfg = configs[platform]
            params = base.parameters if base else {}
            source = request_from_models(product, cfg, base).activity if base else parsed.activity
            st.subheader("2 · 参数确认")
            c1, c2, c3, c4 = st.columns(4)
            discount = c1.number_input("折扣比例 (%)", 0.0, 95.0, float(source.discount_value * 100), 1.0)
            sales = c2.number_input("预计销量", 0, 1000000, int(source.estimated_sales), 10)
            extra = c3.number_input("额外活动佣金 (%)", 0.0, 100.0, float(source.extra_commission_rate * 100), 0.5)
            creator = c4.number_input("达人佣金 (%)", 0.0, 100.0, float((source.creator_commission_rate if source.creator_commission_rate is not None else cfg.creator_commission_rate) * 100), 0.5)
            c5, c6, c7, c8 = st.columns(4)
            shipping = c5.number_input("卖家物流 / 单", 0.0, 10000.0, float(cfg.shipping_cost), 0.1)
            return_rate = c6.number_input("退货率 (%)", 0.0, 100.0, float(cfg.return_rate * 100), 0.5)
            subsidy = c7.number_input("平台补贴 / 单", 0.0, 10000.0, float(source.platform_subsidy), 0.1)
            fixed = c8.number_input("固定活动投入", 0.0, 1000000.0, float(source.fixed_cost), 10.0)
            if st.button("开始盈利分析", type="primary", width="stretch"):
                activity_input = source.model_copy(update={"discount_type": "percentage", "discount_value": d(discount) / 100, "estimated_sales": sales, "extra_commission_rate": d(extra) / 100, "creator_commission_rate": d(creator) / 100, "seller_shipping_cost": d(shipping), "return_rate_override": d(return_rate) / 100, "platform_subsidy": d(subsidy), "ad_budget": d(fixed)})
                request = request_from_models(product, cfg, base) if base else ProfitAnalysisRequest(product=ProductInput.model_validate(product), platform_config=PlatformConfigInput.model_validate(cfg), activity=activity_input)
                request.activity = activity_input
                result = ProfitEngine().calculate(request); scenarios = ScenarioEngine().analyze(request); tips = StrategyEngine().generate(request, result, scenarios)
                activity_id = base.id if base else persist_activity(product.id, activity_input)
                persist_analysis(product.id, activity_id, result, scenarios)
                context_key = f"{product.id}:{base.id if base else activity_input.activity_name}"
                st.session_state["last_analysis"] = {"context": context_key, "request": request.model_dump(mode="json"), "result": result.model_dump(mode="json"), "scenarios": [x.model_dump(mode="json") for x in scenarios], "tips": tips}
            current_context = f"{product.id}:{base.id if base else source.activity_name}"
            if "last_analysis" in st.session_state and st.session_state["last_analysis"].get("context") == current_context:
                from backend.app.schemas.domain import ProfitResult, ScenarioResult
                data = st.session_state["last_analysis"]
                result_panel(ProfitAnalysisRequest.model_validate(data["request"]), ProfitResult.model_validate(data["result"]), [ScenarioResult.model_validate(x) for x in data["scenarios"]], data["tips"])

elif page == "活动对比":
    products = get_products(); activities = get_activities()
    pmap = {f"{p.name} · {p.sku}": p for p in products}; product = pmap[st.selectbox("比较商品", list(pmap))]
    candidates = [a for a in activities if a.product_id == product.id]
    chosen = st.multiselect("勾选活动", [a.activity_name for a in candidates], default=[a.activity_name for a in candidates])
    rows, named = [], []
    for activity in candidates:
        if activity.activity_name not in chosen: continue
        cfg = next((x for x in product.platform_configs if x.platform == activity.platform), None)
        if not cfg: continue
        req = request_from_models(product, cfg, activity); res = ProfitEngine().calculate(req); named.append((activity.activity_name, res))
        item = {x.item: x.amount for x in res.breakdown}
        rows.append({"平台": activity.platform, "活动名称": activity.activity_name, "活动价": float(res.selling_price), "平台费": float(item.get("平台佣金", 0) + item.get("活动额外佣金", 0)), "达人佣金": float(item.get("达人佣金", 0)), "物流": float(item.get("物流成本", 0)), "退货准备金": float(item.get("退货风险准备金", 0)), "单件利润": float(res.unit_profit), "利润率": float(res.profit_margin), "预计销量": res.estimated_sales, "预计总利润": float(res.estimated_total_profit), "风险等级": res.risk_label})
    if rows:
        frame = pd.DataFrame(rows).sort_values(["预计总利润", "利润率"], ascending=False).reset_index(drop=True); frame.insert(0, "排名", range(1, len(frame)+1))
        st.dataframe(frame.style.map(lambda v: "color:#16834b;font-weight:600" if isinstance(v, (int,float)) and v > 0 else "color:#d9363e;font-weight:600" if isinstance(v, (int,float)) and v < 0 else "", subset=["单件利润", "预计总利润"]), hide_index=True, width="stretch")
        metric = st.selectbox("图表指标", ["单件利润", "利润率", "预计总利润"])
        fig = go.Figure(go.Bar(x=frame["活动名称"], y=frame[metric], marker_color=["#23a566" if x >= 0 else "#e44949" for x in frame[metric]], text=frame[metric], textposition="outside")); fig.update_layout(height=390, yaxis_title=metric)
        st.plotly_chart(fig, width="stretch")
        for tip in StrategyEngine().compare(named): st.info(tip)

elif page == "商品管理":
    st.subheader("商品与平台成本配置")
    products = get_products()
    for product in products:
        with st.expander(f"{product.name} · {product.sku}"):
            st.write(f"采购 ${product.purchase_cost} · 包装 ${product.packaging_cost} · 重量 {product.weight_kg} kg")
            with st.form(f"base-{product.id}"):
                ba, bb, bc, bd = st.columns(4)
                edit_name = ba.text_input("商品名称", product.name)
                edit_cost = bb.number_input("采购成本", 0.0, value=float(product.purchase_cost))
                edit_pack = bc.number_input("包装成本", 0.0, value=float(product.packaging_cost))
                edit_weight = bd.number_input("重量 kg", 0.0, value=float(product.weight_kg))
                if st.form_submit_button("保存商品信息"):
                    with session_scope() as session:
                        row = session.get(Product, product.id); row.name=edit_name; row.purchase_cost=d(edit_cost); row.packaging_cost=d(edit_pack); row.weight_kg=d(edit_weight)
                    st.success("商品信息已更新"); st.rerun()
            st.dataframe(pd.DataFrame([{"平台": c.platform, "售价": float(c.original_price), "物流": float(c.shipping_cost), "平台佣金": f"{c.platform_commission_rate:.1%}", "达人佣金": f"{c.creator_commission_rate:.1%}", "退货率": f"{c.return_rate:.1%}", "默认值": "DEMO DEFAULT" if c.demo_default else "自定义"} for c in product.platform_configs]), hide_index=True, width="stretch")
            if product.platform_configs:
                edit_map = {c.platform: c for c in product.platform_configs}
                edit_platform = st.selectbox("修改平台配置", list(edit_map), key=f"platform-{product.id}")
                current = edit_map[edit_platform]
                with st.form(f"edit-{product.id}-{edit_platform}"):
                    ea, eb, ec, ed = st.columns(4)
                    edit_price = ea.number_input("原售价", 0.01, value=float(current.original_price))
                    edit_ship = eb.number_input("物流成本", 0.0, value=float(current.shipping_cost))
                    edit_fee = ec.number_input("平台佣金 %", 0.0, 100.0, float(current.platform_commission_rate * 100))
                    edit_creator = ed.number_input("达人佣金 %", 0.0, 100.0, float(current.creator_commission_rate * 100))
                    ea, eb, ec, ed = st.columns(4)
                    edit_payment = ea.number_input("支付费率 %", 0.0, 100.0, float(current.payment_fee_rate * 100))
                    edit_fx = eb.number_input("汇损率 %", 0.0, 100.0, float(current.fx_loss_rate * 100))
                    edit_tariff = ec.number_input("关税率 %", 0.0, 100.0, float(current.tariff_rate * 100))
                    edit_return = ed.number_input("退货率 %", 0.0, 100.0, float(current.return_rate * 100))
                    if st.form_submit_button("保存平台成本配置"):
                        with session_scope() as session:
                            row = session.get(ProductPlatformConfig, current.id)
                            row.original_price=d(edit_price); row.shipping_cost=d(edit_ship); row.platform_commission_rate=d(edit_fee)/100; row.creator_commission_rate=d(edit_creator)/100
                            row.payment_fee_rate=d(edit_payment)/100; row.fx_loss_rate=d(edit_fx)/100; row.tariff_rate=d(edit_tariff)/100; row.return_rate=d(edit_return)/100; row.demo_default=False
                        st.success("配置已更新并标记为自定义"); st.rerun()
            missing_platforms = [x for x in ["tiktok_shop", "amazon", "temu", "shein"] if x not in {c.platform for c in product.platform_configs}]
            if missing_platforms:
                with st.form(f"add-platform-{product.id}"):
                    st.markdown("**添加平台成本配置**")
                    add_platform = st.selectbox("平台", missing_platforms)
                    aa, ab, ac, ad = st.columns(4)
                    add_price = aa.number_input("平台原售价", 0.01, value=29.99)
                    add_ship = ab.number_input("平台物流", 0.0, value=4.5)
                    add_fee = ac.number_input("平台佣金 %", 0.0, 100.0, value=10.0)
                    add_creator = ad.number_input("平台达人佣金 %", 0.0, 100.0, value=0.0)
                    if st.form_submit_button("添加平台"):
                        with session_scope() as session:
                            session.add(ProductPlatformConfig(product_id=product.id, platform=add_platform, original_price=d(add_price), shipping_cost=d(add_ship), platform_commission_rate=d(add_fee)/100, creator_commission_rate=d(add_creator)/100, demo_default=False))
                        st.success("平台配置已添加"); st.rerun()
            if st.button("删除商品", key=f"del-{product.id}"):
                with session_scope() as session: session.delete(session.get(Product, product.id))
                st.rerun()
    with st.form("new-product"):
        st.markdown("#### 新增商品")
        ca,cb,cc,cd = st.columns(4); name=ca.text_input("商品名称"); sku=cb.text_input("SKU"); cost=cc.number_input("采购成本",0.0); pack=cd.number_input("包装成本",0.0)
        platform=st.selectbox("首个平台",["tiktok_shop","amazon","temu","shein"]); ca,cb,cc,cd=st.columns(4); price=ca.number_input("原售价",0.01); ship=cb.number_input("物流",0.0); fee=cc.number_input("平台佣金 %",0.0,100.0,6.0); creator=cd.number_input("达人佣金 %",0.0,100.0,10.0)
        if st.form_submit_button("创建商品", type="primary"):
            if not name or not sku: st.error("商品名称和 SKU 必填")
            else:
                with session_scope() as session:
                    p=Product(name=name,sku=sku,purchase_cost=d(cost),packaging_cost=d(pack),currency="USD"); session.add(p);session.flush();session.add(ProductPlatformConfig(product_id=p.id,platform=platform,original_price=d(price),shipping_cost=d(ship),platform_commission_rate=d(fee)/100,creator_commission_rate=d(creator)/100,demo_default=False))
                st.success("商品已创建"); st.rerun()

elif page == "历史记录":
    with session_scope() as session: records=session.scalars(select(AnalysisResult).order_by(AnalysisResult.created_at.desc())).all()
    if not records: st.info("尚无分析记录；运行一个演示活动后会自动保存。")
    else:
        st.dataframe(pd.DataFrame([{"ID":x.id,"时间":x.created_at,"单件利润":float(x.unit_profit),"利润率":f"{x.profit_margin:.1%}","预计总利润":float(x.estimated_total_profit),"风险":x.risk_level} for x in records]),hide_index=True,width="stretch")
        selected_id = st.selectbox("重新打开分析记录", [x.id for x in records])
        selected = next(x for x in records if x.id == selected_id)
        stored = (selected.result_data or {}).get("result", {})
        ca, cb, cc = st.columns(3)
        ca.metric("单件利润", f"${stored.get('unit_profit', selected.unit_profit)}")
        cb.metric("利润率", f"{float(stored.get('profit_margin', selected.profit_margin)):.1%}")
        cc.metric("预计总利润", f"${stored.get('estimated_total_profit', selected.estimated_total_profit)}")
        if stored.get("breakdown"):
            st.dataframe(pd.DataFrame(stored["breakdown"])[["item", "formula", "amount", "description"]], hide_index=True, width="stretch")

else:
    st.subheader("设置与声明")
    st.success("OpenAI API Key 已配置" if settings.openai_api_key else "当前使用规则分析模式；无需 API Key，核心计算与演示均可运行。")
    st.code("OPENAI_API_KEY=你的密钥\nOPENAI_MODEL=gpt-4.1-mini", language="bash")
    st.markdown("**利润风险阈值**：≥20% 强烈推荐；10%-20% 可以参加；3%-10% 谨慎参加；0%-3% 不建议；<0% 明确亏损。")
    st.warning("平台默认费率均为 DEMO DEFAULT，不代表平台当前官方费率。真实费率随国家、站点、类目和卖家协议变化。")
    st.caption("隐私：核心计算完全本地执行。配置 LLM 时只发送活动解析/建议所需的最小字段，不上传完整店铺数据。")
