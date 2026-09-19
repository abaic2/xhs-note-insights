#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
小红书笔记 × 评论 数据分析 Demo（Streamlit 版）
================================================

    streamlit run app.py

设计说明
--------
* **公网版是只读展示**：数据来自公开数据集 + 已完成的离线分析结果。
  实时爬取依赖 Playwright 启动真实浏览器 + 人工扫码登录，
  这在无头云端容器里做不到 —— 那部分保留在本地版（见「方法与合规」页）。
* **不转载他人图片**：demo 里单篇笔记的图片墙用占位块 + 数量说明，
  不放真实用户拍摄的照片。
* **昵称已脱敏**：统一打码为「前两字 + ***」（预处理阶段完成）。
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go

DATA = Path(__file__).resolve().parent / "data"

st.set_page_config(
    page_title="小红书笔记 × 评论 数据分析",
    page_icon="📕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# 设计系统：浅色主题 + 小红书红
# ---------------------------------------------------------------------------
RED = "#FF2442"
RED_SOFT = "#FFF0F2"
POS, NEU, NEG = "#FF4D6D", "#C9CCD6", "#5B7DB1"
T1, T2, T3 = "#1B1F26", "#5A6070", "#8C93A3"
LINE = "#E8EAF0"
FEAT_COLOR = {
    "广告营销": "#FF7A8A", "汽车": "#6C8AE4", "时尚": "#D98AE4", "美食": "#F2A65A",
    "文学": "#57BFA0", "印刷设计": "#8FA5C7", "运动健身": "#E4A0B8", "科技数码": "#7C9CD6",
}

CSS = f"""
<style>
.stApp {{ background: #F5F6F8; }}
.block-container {{ padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1240px; }}

/* ---- 侧边栏：浅色 + 红调 ---- */
section[data-testid="stSidebar"], div[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, #FFF6F8 0%, #FFFFFF 60%, #FDFDFE 100%) !important;
  border-right: 1px solid {LINE};
}}
section[data-testid="stSidebar"] > div, div[data-testid="stSidebar"] > div,
div[data-testid="stSidebarContent"], div[data-testid="stSidebarUserContent"] {{
  background: transparent !important;
}}
section[data-testid="stSidebar"] *, div[data-testid="stSidebar"] * {{
  color: {T1} !important;
}}
section[data-testid="stSidebar"] .stCaption, section[data-testid="stSidebar"] small {{
  color: {T3} !important;
}}

/* ---- Hero ---- */
.hero {{
  position: relative; overflow: hidden; border-radius: 18px; padding: 30px 32px;
  background: linear-gradient(120deg, #FF2442 0%, #FF5C7C 48%, #FF8FA3 100%);
  color: #fff; margin-bottom: 18px;
  box-shadow: 0 10px 30px rgba(255,36,66,.22);
}}
.hero::after {{
  content: ""; position: absolute; right: -60px; top: -70px; width: 260px; height: 260px;
  border-radius: 50%; background: rgba(255,255,255,.18); filter: blur(6px);
}}
.hero h1 {{ font-size: 30px; font-weight: 800; margin: 0 0 8px; letter-spacing: -.5px; color:#fff; }}
.hero p {{ margin: 0; font-size: 14.5px; color: rgba(255,255,255,.92); max-width: 780px; line-height: 1.7; }}
.hero .chips {{ margin-top: 14px; display: flex; gap: 8px; flex-wrap: wrap; }}
.hero .chip {{
  background: rgba(255,255,255,.20); border: 1px solid rgba(255,255,255,.35);
  border-radius: 999px; padding: 4px 12px; font-size: 12.5px; color: #fff;
}}

/* ---- 卡片 ---- */
.card {{
  background: #fff; border: 1px solid {LINE}; border-radius: 14px; padding: 18px 20px;
  box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 6px 20px rgba(16,24,40,.05);
  margin-bottom: 14px;
}}
.card h3 {{ font-size: 15px; font-weight: 700; margin: 0 0 6px; color: {T1}; }}
.card p  {{ font-size: 12.5px; color: {T3}; margin: 0; line-height: 1.65; }}

/* ---- KPI ---- */
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(158px, 1fr)); gap: 12px; }}
.kpi {{
  position: relative; overflow: hidden; background: #fff; border: 1px solid {LINE};
  border-radius: 13px; padding: 14px 16px;
  box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 6px 18px rgba(16,24,40,.05);
}}
.kpi::before {{ content:""; position:absolute; left:0; top:0; width:3px; height:100%; background:{RED}; opacity:.9; }}
.kpi .k {{ font-size: 12px; color: {T3}; }}
.kpi .v {{ font-size: 25px; font-weight: 800; letter-spacing: -.8px; color: {T1}; line-height: 1.25; }}
.kpi .n {{ font-size: 11.5px; color: {T3}; }}

/* ---- 提示条 ---- */
.notice {{
  background: {RED_SOFT}; border: 1px solid #FFD9DF; border-radius: 12px;
  padding: 13px 16px; font-size: 13px; color: #A81D33; line-height: 1.75;
}}
.okbox {{
  background: #EFFAF3; border: 1px solid #C9EBD8; border-radius: 12px;
  padding: 13px 16px; font-size: 13px; color: #1D7A45; line-height: 1.75;
}}

/* ---- 评论卡 ---- */
.cmt {{
  border: 1px solid {LINE}; border-left: 3px solid {RED}; border-radius: 11px;
  padding: 11px 14px; background: #fff; margin-bottom: 9px;
}}
.cmt .meta {{ font-size: 11.5px; color: {T3}; margin-bottom: 5px; }}
.cmt .body {{ font-size: 13.5px; color: {T1}; line-height: 1.65; }}
.cmt .foot {{ font-size: 11.5px; color: {T3}; margin-top: 6px; }}
.cmt .likes {{ color: {RED}; font-weight: 700; }}

/* ---- 图片占位 ---- */
.tile {{
  height: 132px; border-radius: 11px; border: 1px solid {LINE};
  background: repeating-linear-gradient(45deg, #F7F8FA, #F7F8FA 10px, #F1F3F7 10px, #F1F3F7 20px);
  display: flex; align-items: center; justify-content: center;
  color: {T3}; font-size: 12px;
}}

/* ---- 判词 ---- */
.verdict {{ font-size: 14px; line-height: 1.75; color: {T1}; }}
.verdict b {{ color: #C7243E; }}

/* 表格 */
[data-testid="stDataFrame"] {{ border-radius: 10px; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 数据
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_json(path: str):
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def dash() -> dict | None:
    return load_json(str(DATA / "dashboard_data.json"))


def note_index() -> list:
    return load_json(str(DATA / "notes" / "index.json")) or []


def note_data(key: str) -> dict | None:
    return load_json(str(DATA / "notes" / f"{key}.json"))


def base_layout(fig: go.Figure, height: int = 340, title: str = "") -> go.Figure:
    layout = dict(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="PingFang SC, Microsoft YaHei, sans-serif",
                  size=12, color=T2),
        margin=dict(l=10, r=10, t=46 if title else 14, b=10),
        colorway=[RED, "#FF8FA3", "#6C8AE4", "#57BFA0", "#F2A65A"],
        hoverlabel=dict(bgcolor="#fff", bordercolor=LINE,
                        font=dict(color=T1, size=12)),
    )
    if title:
        # 左对齐 + 加深色：plotly 默认的居中灰标题放进卡片里既不够醒目、
        # 也和卡片自身的左对齐标题对不齐。
        layout["title"] = dict(text=title, x=0, xanchor="left",
                               font=dict(size=13.5, color=T1))
    fig.update_layout(**layout)
    tick = dict(size=11, color="#6B7280")
    fig.update_xaxes(gridcolor="#F2F4F8", linecolor=LINE, zeroline=False,
                     tickfont=tick)
    fig.update_yaxes(gridcolor="#F2F4F8", linecolor=LINE, zeroline=False,
                     tickfont=tick)
    return fig


def kpis(items: list[tuple[str, str, str]]) -> None:
    html = '<div class="kpis">'
    for label, value, note in items:
        html += (f'<div class="kpi"><div class="k">{label}</div>'
                 f'<div class="v">{value}</div><div class="n">{note}</div></div>')
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def verdict_html(kinds: list[dict]) -> str:
    k = {x["key"]: x for x in kinds}
    ask = k.get("ask", {}).get("pct", 0)
    dis = k.get("discuss", {}).get("pct", 0)
    if ask >= 50:
        return (f'<b>引流型评论区</b>：{ask}% 是求资源/求关注，实质讨论仅 {dis}%。'
                '这类笔记的互动数据好看，但社区讨论价值低。')
    if dis >= 40:
        return f'<b>深度讨论型评论区</b>：{dis}% 是实质表达，求资源仅 {ask}%。'
    if dis >= 20:
        return (f'<b>讨论型评论区</b>：{dis}% 是实质表达，另有大量简短回应/表情，'
                '整体氛围活跃。')
    if ask >= 25:
        return f'<b>混合型评论区</b>：求资源 {ask}% / 实质讨论 {dis}%，两种动机并存。'
    return (f'<b>轻互动评论区</b>：求资源 {ask}% / 实质讨论仅 {dis}%，'
            '绝大多数评论是简短回应或表情。')


# ---------------------------------------------------------------------------
# 页面
# ---------------------------------------------------------------------------
def page_overview() -> None:
    d = dash()
    if not d:
        st.error("缺少 data/dashboard_data.json，请先运行 streamlit_app/prepare_data.py")
        return
    K = d["kpi"]

    st.markdown(
        '<div class="hero"><h1>小红书笔记 × 评论 数据分析</h1>'
        '<p>从评论采集、清洗、情感判定到多维可视化的完整链路。'
        f'本页展示的是对 <b>{K["comments"]:,}</b> 条真实评论与 <b>{K["posts"]:,}</b> 篇笔记'
        '的离线分析结果 —— 数据来自 GitHub 上的公开数据集。</p>'
        '<div class="chips">'
        '<span class="chip">65,097 条评论</span>'
        '<span class="chip">1,582 篇笔记</span>'
        '<span class="chip">8 个垂类</span>'
        '<span class="chip">情感模型留出集 86.7%</span>'
        '</div></div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="notice"><b>关于公网版：</b>这里是<b>只读展示</b>。'
        '实时抓取需要 Playwright 启动真实浏览器、并由人工扫码登录 —— '
        '无头云端容器做不到这两件事，所以爬虫保留在本地版运行。'
        '完整工作流见「方法与合规」页。</div>', unsafe_allow_html=True)
    st.write("")

    S = K["sentiment"]
    kpis([
        ("笔记数", f'{K["posts"]:,}', f'覆盖 {len(d["features"])} 个垂类'),
        ("评论数", f'{K["comments"]:,}', f'平均每篇 {K["avg_comments_per_note"]} 条'),
        ("评论用户", f'{K["commenters"]:,}', "去重后的评论者"),
        ("评论总点赞", f'{K["comment_likes"]:,}', f'条均 {K["avg_comment_likes"]} 赞'),
        ("笔记互动总量", f'{K["engagement"]:,}', "赞+藏+论+转"),
        ("二级评论占比", f'{K["reply_ratio"]}%', "反映讨论深度"),
        ("正面率", f'{S["pos_pct"]}%', f'负面 {S["neg_pct"]}% · 中性 {S["neu_pct"]}%'),
        ("情感净值", f'{"+" if S["net"] > 0 else ""}{S["net"]}', "正面率 − 负面率"),
    ])

    st.write("")
    c1, c2 = st.columns([1.35, 1])
    with c1:
        st.markdown('<div class="card"><h3>这四个数字说明什么</h3><p>'
                    '① 中性占比高是评论区常态 —— 大量评论是短问句与信息型留言，不代表"没情绪"；'
                    '② 点赞与收藏高度相关，但点赞与评论几乎无关，说明平台偏"收藏型"；'
                    '③ 二级评论占 43%，讨论深度不低；'
                    '④ 情感净值 +12，整体氛围正向。'
                    '</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card"><h3>数据来源</h3><p>'
                    'coralr-1/Xiaohongshu-AIGC-Comments-and-Posts-Dataset（GitHub，2025-01）。'
                    '两个 CSV 均以 git blob SHA 逐字节校验，编码为 GB18030（非 UTF-8）。'
                    '展示前已对昵称做脱敏处理。</p></div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><h3>时间跨度</h3><p>'
                f'评论 {K["time_range"][0]} ~ {K["time_range"][1]}，'
                '横跨 8 个 AIGC 话题方向（广告营销 / 汽车 / 时尚 / 美食 / 文学 / '
                '印刷设计 / 运动健身 / 科技数码）。</p></div>',
                unsafe_allow_html=True)


def page_insights() -> None:
    d = dash()
    if not d:
        st.error("缺少数据")
        return
    st.markdown("### 全库洞察")
    st.caption("基于 65,097 条评论与 1,582 篇笔记的聚合结果")

    # 情感 + 垂类净值
    c1, c2 = st.columns([1, 1.2])
    with c1:
        S = d["kpi"]["sentiment"]
        fig = go.Figure(go.Pie(
            labels=["正面", "中性", "负面"],
            values=[S["positive"], S["neutral"], S["negative"]],
            hole=.62, marker=dict(colors=[POS, NEU, NEG],
                                  line=dict(color="#fff", width=3)),
            textinfo="label+percent", textfont=dict(size=12)))
        st.plotly_chart(base_layout(fig, 320, "整体情感构成"),
                        use_container_width=True)
    with c2:
        fs = sorted(d["features"], key=lambda x: x["net"])
        fig = go.Figure(go.Bar(
            x=[x["net"] for x in fs], y=[x["name"] for x in fs], orientation="h",
            marker=dict(color=[RED if x["net"] >= 0 else NEG for x in fs]),
            text=[f'{x["net"]}' for x in fs], textposition="outside"))
        st.plotly_chart(base_layout(fig, 320, "各垂类情感净值（正面率−负面率）"),
                        use_container_width=True)

    # 趋势
    M = d["monthly"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[m["month"] for m in M], y=[m["comments"] for m in M],
                             name="评论量", fill="tozeroy",
                             line=dict(color=RED, width=2),
                             fillcolor="rgba(255,36,66,.14)"))
    fig.add_trace(go.Bar(x=[m["month"] for m in M], y=[m["posts"] for m in M],
                         name="笔记发布数", marker_color="rgba(27,31,38,.12)",
                         yaxis="y2"))
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False,
                                  title="笔记数"))
    st.plotly_chart(base_layout(fig, 360, "月度活跃度"),
                    use_container_width=True)

    # 时段热力 + 地域
    c1, c2 = st.columns([1.25, 1])
    with c1:
        heat = d["heat"]["comments"]
        fig = go.Figure(go.Heatmap(
            z=heat, x=[f"{h}:00" for h in range(24)],
            y=["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
            colorscale=[[0, "#F4F6FA"], [.35, "#FFD3DA"], [.7, "#FF8FA3"],
                        [1, "#D6193A"]],
            showscale=True, hoverongaps=False))
        st.plotly_chart(base_layout(fig, 330, "评论发生时段（周 × 小时）"),
                        use_container_width=True)
    with c2:
        G = d["geo"][:12]
        fig = go.Figure(go.Bar(
            x=[g["comments"] for g in G], y=[g["name"] for g in G],
            orientation="h", marker=dict(color=RED, opacity=.85),
            text=[f'{g["comments"]:,}' for g in G], textposition="outside"))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(base_layout(fig, 330, "评论者 IP 属地 Top 12"),
                        use_container_width=True)

    # 热词
    st.markdown("#### 评论热词")
    words = [w for w in d["words"] if not w["emoji"]][:28]
    fig = go.Figure(go.Bar(
        x=[w["value"] for w in words], y=[w["name"] for w in words],
        orientation="h",
        marker=dict(color=[POS if w["net"] > 20 else (NEU if w["net"] >= 0 else NEG)
                           for w in words]),
        text=[f'{w["value"]:,} · 净值 {w["net"]:+.0f}' for w in words],
        textposition="outside"))
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(base_layout(fig, 620, ""), use_container_width=True)
    st.caption("颜色：红=情感净值高，灰=中性，蓝=偏负面。已过滤站内表情词。")

    # 笔记榜 + 相关性
    c1, c2 = st.columns([1.3, 1])
    with c1:
        st.markdown("#### 笔记互动榜 Top 10")
        rows = "".join(
            f'<div class="cmt"><div class="body">{p["title"][:56]}</div>'
            f'<div class="foot">{p["feature"]} · {p["nickname"]} · '
            f'<span class="likes">♥ {p["liked"]:,}</span> · '
            f'收藏 {p["collected"]:,} · 评论 {p["comments"]:,} · {p["date"]}</div></div>'
            for p in d["top_posts"][:10])
        st.markdown(rows, unsafe_allow_html=True)
    with c2:
        st.markdown("#### 指标相关性（皮尔逊）")
        for k, v in sorted(d["corr"].items(), key=lambda x: -abs(x[1])):
            a = abs(v)
            lv = "强" if a >= .6 else ("中" if a >= .35 else ("弱" if a >= .15 else "几乎无关"))
            color = POS if v > 0 else NEG
            st.markdown(
                f'<div style="margin-bottom:9px">'
                f'<div style="display:flex;justify-content:space-between;font-size:12.5px">'
                f'<span>{k}</span><b style="color:{color}">{v:+.4f} · {lv}</b></div>'
                f'<div style="height:6px;background:#F2F4F8;border-radius:6px;margin-top:4px">'
                f'<div style="width:{a*100:.0f}%;height:100%;background:{color};'
                f'border-radius:6px"></div></div></div>', unsafe_allow_html=True)
        st.caption("相关性 ≠ 因果。点赞与收藏强相关，说明「点赞即收藏」是典型行为路径。")


def page_kinds() -> None:
    st.markdown("### 评论区要按「意图」分，不是按「情感」分")
    st.markdown(
        '<div class="card"><h3>为什么</h3><p>'
        '只看情感会误读。大量评论不是"表达情绪"，而是"索取资源"'
        '（想要 / 求分享 / 关注我）。这类评论会把情感分布整体拉成中性，'
        '让人误以为"评论区没观点"。把意图拆出来，一篇笔记的评论区性质立刻清楚。'
        '</p></div>', unsafe_allow_html=True)

    idx = note_index()
    if not idx:
        st.warning("暂无单篇数据")
        return

    st.markdown("#### 三篇真实笔记对比")
    head = ("| 笔记 | 评论数 | 情感净值 | 求资源 | 实质讨论 | 评论区性质 |\n"
            "|---|---|---|---|---|---|\n")
    body = ""
    for it in sorted(idx, key=lambda x: -x["ask_pct"]):
        kind = ("引流型" if it["ask_pct"] >= 50 else
                "混合偏引流" if it["ask_pct"] >= 25 else
                "讨论型" if it["discuss_pct"] >= 20 else "轻互动")
        body += (f'| {it["title"][:30]} | {it["comments"]:,} | '
                 f'{it["net"]:+.1f} | {it["ask_pct"]}% | {it["discuss_pct"]}% | {kind} |\n')
    st.markdown(head + body)

    st.markdown("#### 逐篇：意图分布与判词")
    for it in sorted(idx, key=lambda x: -x["ask_pct"]):
        nd = note_data(it["key"])
        if not nd:
            continue
        with st.expander(f'{it["title"][:44]}　·　{it["comments"]:,} 条评论',
                         expanded=it is idx[0]):
            st.markdown(f'<div class="verdict">📌 {verdict_html(nd["kinds"])}</div>',
                        unsafe_allow_html=True)
            st.write("")
            kinds = sorted([k for k in nd["kinds"] if k["n"]], key=lambda x: -x["n"])
            c1, c2 = st.columns([1, 1])
            with c1:
                fig = go.Figure(go.Bar(
                    x=[k["n"] for k in kinds], y=[k["name"] for k in kinds],
                    orientation="h",
                    marker=dict(color=[k["color"] for k in kinds]),
                    text=[f'{k["n"]:,} ({k["pct"]}%)' for k in kinds],
                    textposition="outside"))
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(base_layout(fig, 300, "评论意图分布"),
                                use_container_width=True)
            with c2:
                ak = [nd["avg_by_kind"][k["key"]] for k in kinds
                      if k["key"] in nd["avg_by_kind"]]
                fig = go.Figure(go.Bar(
                    x=[a["avg_likes"] for a in ak], y=[a["name"] for a in ak],
                    orientation="h",
                    marker=dict(color=RED, opacity=.85),
                    text=[f'{a["avg_likes"]}' for a in ak], textposition="outside"))
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(base_layout(fig, 300, "哪类评论更容易被点赞"),
                                use_container_width=True)

    st.markdown(
        '<div class="okbox"><b>别想当然：</b>「哪类评论更易获赞」在两篇笔记里结论<b>完全相反</b>。'
        '引流帖里短回应（0.21）反而高于实质讨论（0.08）—— 高赞靠"早"和"梗"；'
        '讨论帖里实质讨论（203.96）碾压情感回应（1.92）—— 认真写的确实更被认可。'
        '所以这些结论必须由数据算出来，不能写死成模板话术。</div>',
        unsafe_allow_html=True)


def page_note() -> None:
    idx = note_index()
    if not idx:
        st.warning("暂无单篇数据")
        return
    st.markdown("### 单篇笔记报告")
    st.caption("选一篇笔记，查看它的指标、情感、构成与评论原文")

    labels = {f'{it["title"][:40]}（{it["comments"]:,} 条评论）': it["key"] for it in idx}
    choice = st.selectbox("选择笔记", list(labels.keys()))
    key = labels[choice]
    nd = note_data(key)
    if not nd:
        st.error("数据缺失")
        return
    N, S_, E = nd["note"], nd["stats"], nd["sentiment"]

    st.markdown(
        f'<div class="card"><h3>{N["title"] or "（无标题）"}</h3>'
        f'<p>{N["author"]} · {"视频" if N["type"] == "video" else "图文"} · '
        f'{N["image_count"]} 张图 · {" ".join("#" + t for t in N["tags"][:6])}</p>'
        f'<p style="color:{T1};font-size:13px;margin-top:10px;white-space:pre-wrap">'
        f'{(N["desc"] or "")[:400]}</p></div>', unsafe_allow_html=True)

    kpis([
        ("评论数", f'{S_["total"]:,}', f'一级 {S_["top"]:,} / 二级 {S_["sub"]:,}'),
        ("参与用户", f'{S_["users"]:,}', f'人均 {S_["per_user"]} 条'),
        ("情感净值", f'{"+" if E["net"] > 0 else ""}{E["net"]}', f'正面 {E["pos_pct"]}%'),
        ("求资源占比",
         f'{next((k["pct"] for k in nd["kinds"] if k["key"] == "ask"), 0)}%',
         "评论构成"),
    ])
    st.write("")
    st.markdown(f'<div class="verdict">📌 {verdict_html(nd["kinds"])}</div>',
                unsafe_allow_html=True)
    st.write("")

    # 图片墙（占位）
    st.markdown(f"#### 正文图片（{N['image_count']} 张）")
    cols = st.columns(6)
    for i in range(min(N["image_count"], 12)):
        with cols[i % 6]:
            st.markdown('<div class="tile">实拍图</div>', unsafe_allow_html=True)
    st.caption("公网 demo 不转载他人拍摄的照片，这里用占位块表示。"
               "本地运行时会把图片下载并内嵌进 HTML 报告。")

    c1, c2 = st.columns(2)
    with c1:
        kinds = sorted([k for k in nd["kinds"] if k["n"]], key=lambda x: -x["n"])
        fig = go.Figure(go.Bar(
            x=[k["n"] for k in kinds], y=[k["name"] for k in kinds],
            orientation="h", marker=dict(color=[k["color"] for k in kinds]),
            text=[f'{k["pct"]}%' for k in kinds], textposition="outside"))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(base_layout(fig, 300, "评论意图分布"), use_container_width=True)
    with c2:
        fig = go.Figure(go.Pie(
            labels=["正面", "中性", "负面"],
            values=[E["positive"], E["neutral"], E["negative"]],
            hole=.62, marker=dict(colors=[POS, NEU, NEG],
                                  line=dict(color="#fff", width=3)),
            textinfo="percent", textfont=dict(size=12)))
        st.plotly_chart(base_layout(fig, 300, "情感构成"), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        wk = S_["by_week"]
        fig = go.Figure(go.Bar(
            x=["周一", "周二", "周三", "周四", "周五", "周六", "周日"], y=wk,
            marker=dict(color=[RED if i >= 5 else "#FFB3BE" for i in range(7)])))
        st.plotly_chart(base_layout(fig, 280, "评论发生在星期几"),
                        use_container_width=True)
    with c2:
        hh = S_["by_hour"]
        fig = go.Figure(go.Bar(x=[f"{i}:00" for i in range(24)], y=hh,
                               marker_color=RED, opacity=.85))
        st.plotly_chart(base_layout(fig, 280, "评论发生在几点"),
                        use_container_width=True)

    st.markdown("#### 高赞评论 Top 10")
    for c in nd["top_comments"][:10]:
        st.markdown(
            f'<div class="cmt"><div class="meta">{c["nickname"]} · {c["ip"]} · '
            f'{c["date"]}</div><div class="body">{c["content"][:200]}</div>'
            f'<div class="foot"><span class="likes">♥ {c["likes"]:,}</span></div></div>',
            unsafe_allow_html=True)

    with st.expander(f'浏览评论原文（已脱敏，共展示 {len(nd["sample"])} 条）'):
        kw = st.text_input("搜索评论内容", key=f"q_{key}")
        rows = [c for c in nd["sample"]
                if not kw or kw.lower() in c["content"].lower()]
        st.caption(f"命中 {len(rows)} 条")
        for c in rows[:60]:
            st.markdown(
                f'<div class="cmt"><div class="meta">{c["nickname"]} · {c["ip"]} · '
                f'{c["date"]}</div><div class="body">{c["content"][:220]}</div></div>',
                unsafe_allow_html=True)


def page_method() -> None:
    st.markdown("### 方法与合规")

    st.markdown("#### 完整工作流")
    st.markdown(
        "```\n"
        "① 采集    Playwright 驱动真实浏览器 → 监听浏览器自己发出的接口响应\n"
        "          ↘ 同时抓到「带有效签名的图片 URL」\n"
        "② 落盘    comments.jsonl（断点续爬 + 幂等去重） + note.json + images/\n"
        "③ 分析    词典情感引擎 → 指标聚合 → 热词提取 → 互动意图分类\n"
        "④ 交付    自包含单文件 HTML 报告（图片 base64 内嵌，可离线打开）\n"
        "```")

    st.markdown("#### 四个必须知道的平台特性（实测）")
    st.markdown(
        "| # | 特性 | 影响 |\n|---|---|---|\n"
        "| 1 | 分享链接**必须带 `xsec_token`** | 裸 note_id 会 302 到 404 页 |\n"
        "| 2 | 图床 URL 带**时效签名** | 老 URL 全部 403，必须当场下载 |\n"
        "| 3 | 接口需要前端 JS 生成的签名头 | 纯 requests 走不通，用浏览器复用真实会话 |\n"
        "| 4 | 笔记详情走 **SSR meta 标签** | 不再有 `/feed` 请求，得从 `og:` 标签取 |\n")

    with st.expander("为什么公网版不能实时爬取"):
        st.markdown(
            "- **需要真实浏览器**：接口签名由页面 JS 生成，无头容器里装不了也无法逆向；\n"
            "- **需要人工扫码登录**：登录墙必须由人在可见窗口里扫码，云端没有这个条件；\n"
            "- **文件系统是临时的**：登录态保不住，每次都要求登录；\n"
            "- **合规**：把抓取能力做成公开服务，容易被滥用成批量采集，不合适。\n\n"
            "所以爬虫保留在本地版：`python server.py` → 浏览器里粘贴链接 → 扫码 → 出报告。")

    ev = load_json(str(DATA / "eval_summary.json"))
    st.markdown("#### 情感模型的人工校验")
    if ev:
        rows = []
        for k, v in ev.items():
            name = "留出集（最终结论）" if k == "test_sample" else "开发集（调参用）"
            rows.append(f'| {name} | {v["accuracy"]*100:.1f}% | {v["baseline"]*100:.1f}% | '
                        f'+{(v["accuracy"]-v["baseline"])*100:.1f}pt | {v["n"]} |')
        st.markdown("| 数据集 | 准确率 | 多数类基线 | 提升 | 样本量 |\n"
                    "|---|---|---|---|---|\n" + "\n".join(rows))
        st.caption("词典法不能只靠「看着还行」。人工逐条标注 60 条，"
                   "调参只在开发集做，最终结论取留出集。")
    else:
        st.info("暂无评估数据")

    st.markdown(
        '<div class="notice"><b>已知短板：</b>负面召回偏低（66.7%）。'
        '讽刺、反语，以及"我养了条狗…有一天咬我"这类<b>不出现情绪词的负面叙事</b>会漏判 —— '
        '纯词典法覆盖不了，要提升必须引入上下文模型。</div>', unsafe_allow_html=True)

    st.markdown("#### 合规边界")
    st.markdown(
        "- 仅用于**个人学习研究**，采集对象为平台**公开**内容\n"
        "- 遵守平台《用户服务协议》《隐私政策》及 robots 协议\n"
        "- **不得**用于商业转售、数据倒卖、批量引流或骚扰用户\n"
        "- 内置限速，**不要关闭**；高频请求会被风控\n"
        "- 采集结果含个人信息，**不要公开传播**；对外展示应脱敏/聚合（本站已脱敏昵称、不转载图片）\n"
        "- **生产环境请使用小红书开放平台 / 蒲公英等官方接口**")

    st.markdown("#### 技术栈")
    st.markdown(
        "`Python 3.9+`（分析链路只用标准库） · `Playwright`（浏览器采集） · "
        "`jieba`（可选，热词分词） · `Streamlit` + `Plotly`（本站） · "
        "单文件 HTML + 内联 ECharts（本地报告与看板）")


# ---------------------------------------------------------------------------
# 导航
# ---------------------------------------------------------------------------
PAGES = {
    "总览": ("house", page_overview),
    "全库洞察": ("bar-chart", page_insights),
    "评论构成": ("diagram-3", page_kinds),
    "单篇报告": ("file-text", page_note),
    "方法与合规": ("shield-check", page_method),
}


def sidebar_nav() -> str:
    st.sidebar.markdown(
        f'<div style="padding:6px 4px 14px">'
        f'<div style="font-size:17px;font-weight:800;color:{T1}">📕 小红书数据分析</div>'
        f'<div style="font-size:12px;color:{T3};margin-top:4px">'
        f'65,097 条评论 · 8 个垂类</div></div>', unsafe_allow_html=True)
    try:
        from streamlit_option_menu import option_menu
        # 必须在 with st.sidebar 里调用，否则会渲染到主内容区把页面标题盖住。
        # option_menu 用的是「当前容器」，不加这个上下文它默认落在主区。
        with st.sidebar:
            return option_menu(
                menu_title=None, options=list(PAGES.keys()),
                icons=[v[0] for v in PAGES.values()],
                default_index=0,
                styles={
                    "container": {"padding": "6px 4px", "background-color": "#FFFFFF",
                                  "border-radius": "12px",
                                  "border": f"1px solid {LINE}"},
                    "icon": {"color": RED, "font-size": "15px"},
                    "nav-link": {"font-size": "14.5px", "color": T2, "font-weight": "600",
                                 "margin": "3px 0", "padding": "9px 14px",
                                 "border-radius": "10px",
                                 "--hover-color": RED_SOFT,
                                 "border": "1px solid transparent"},
                    "nav-link-selected": {
                        "background": f"linear-gradient(90deg, {RED_SOFT}, #FFFFFF)",
                        "border": f"1px solid #FFC2CC", "color": "#C7243E",
                        "font-weight": "800", "border-left": f"4px solid {RED}"},
                })
    except Exception:
        # 没装 streamlit-option-menu 也能跑（本地调试常见）
        st.sidebar.caption("（未安装 streamlit-option-menu，已回退到单选）")
        return st.sidebar.radio("导航", list(PAGES.keys()), label_visibility="collapsed")


def main() -> None:
    page = sidebar_nav()
    st.sidebar.markdown("---")
    st.sidebar.caption("数据：公开数据集 · 昵称已脱敏 · 不转载他人图片")
    st.sidebar.caption("本地版支持「粘贴笔记链接 → 自动采集 → 出报告」")
    PAGES.get(page, ("", page_overview))[1]()


if __name__ == "__main__":
    main()
