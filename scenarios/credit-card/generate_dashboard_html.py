# -*- coding: utf-8 -*-
"""Render a single-file HTML dashboard from dashboard-data.json."""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
ARCHIVE = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "bills"
DATA = json.loads((ARCHIVE / "dashboard-data.json").read_text(encoding="utf-8"))
# Keep the page lighter: drop nothing critical, but transactions stay.
OUT = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else REPO / "docs" / "dashboard.html"
OUT.parent.mkdir(parents=True, exist_ok=True)

payload = json.dumps(DATA, ensure_ascii=False)
page_title = DATA["meta"].get("page_title") or DATA["meta"]["title"]

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>__PAGE_TITLE__</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
<style>
  :root {
    --lobby: #8F9E98;
    --ink: #12241C;
    --passbook: #184536;
    --stamp: #C4452D;
    --money: #0D5C44;
    --mute: #5A6B64;
    --line: #C3CFC8;
    --panel: #F4F7F5;
    --paper: #E4ECE8;
    --chip: #D7E3DC;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    background: var(--lobby);
    color: var(--ink);
    font-family: "Microsoft YaHei UI", "PingFang SC", "Noto Sans SC", sans-serif;
    font-size: 14px;
    line-height: 1.5;
  }
  .wrap { max-width: 1440px; margin: 0 auto; padding: 28px 28px 64px; }
  .mast {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 16px;
    align-items: end;
    padding-bottom: 18px;
    border-bottom: 3px solid var(--passbook);
  }
  .brand {
    font-family: "Songti SC", "STSong", "SimSun", serif;
    font-size: 13px;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--passbook);
  }
  h1 {
    font-family: "Songti SC", "STSong", "SimSun", serif;
    font-weight: 700;
    font-size: 42px;
    line-height: 1.1;
    margin: 6px 0 0;
    letter-spacing: 0.04em;
  }
  .meta { color: var(--mute); font-size: 13px; text-align: right; }
  .meta b { color: var(--ink); font-weight: 600; }
  .kpis {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 10px;
    margin: 22px 0 18px;
  }
  .kpi {
    background: var(--panel);
    border: 1px solid var(--line);
    padding: 14px 14px 12px;
  }
  .kpi .lab { font-size: 11px; letter-spacing: 0.12em; color: var(--mute); }
  .kpi .num {
    font-family: "Cascadia Mono", "Consolas", "SF Mono", monospace;
    font-size: 26px;
    font-weight: 600;
    color: var(--passbook);
    margin-top: 6px;
    letter-spacing: -0.03em;
  }
  .kpi.accent { background: var(--passbook); color: #F3F7F4; border-color: var(--passbook); }
  .kpi.accent .lab { color: #B7C9C0; }
  .kpi.accent .num { color: #F7FBF8; }
  .tape {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(148px, 1fr));
    gap: 0;
    background: var(--panel);
    border: 1px dashed var(--passbook);
    margin: 8px 0 22px;
  }
  .cell {
    padding: 14px 12px 16px;
    border-right: 1px dashed #B7C4BE;
    min-height: 168px;
  }
  .cell:last-child { border-right: 0; }
  .cell .m {
    font-family: "Songti SC", "STSong", "SimSun", serif;
    font-size: 20px;
  }
  .cell .due { font-size: 11px; color: var(--mute); }
  .cell .amt {
    font-family: "Cascadia Mono", Consolas, monospace;
    font-size: 18px;
    margin: 10px 0 6px;
    color: var(--money);
  }
  .bar {
    height: 6px;
    background: var(--chip);
    margin: 8px 0;
  }
  .bar > i { display: block; height: 100%; background: var(--passbook); }
  .stamp {
    display: inline-block;
    font-size: 11px;
    border: 1.5px solid var(--stamp);
    color: var(--stamp);
    padding: 1px 6px;
    letter-spacing: 0.12em;
    transform: rotate(-6deg);
  }
  .grid2 { display: grid; grid-template-columns: 1.4fr 1fr; gap: 14px; margin-bottom: 14px; }
  .grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; margin-bottom: 14px; }
  .card {
    background: var(--panel);
    border: 1px solid var(--line);
    padding: 16px 16px 10px;
  }
  .card h2 {
    margin: 0 0 10px;
    font-size: 15px;
    letter-spacing: 0.08em;
    font-weight: 700;
  }
  .chart { width: 100%; height: 320px; }
  .chart.tall { height: 380px; }
  .mer-scroll {
    max-height: 380px;
    overflow-y: auto;
    overflow-x: hidden;
  }
  .mer-scroll::-webkit-scrollbar { width: 8px; }
  .mer-scroll::-webkit-scrollbar-thumb { background: #8AA198; }
  .mer-scroll::-webkit-scrollbar-track { background: var(--chip); }
  .notes { display: grid; gap: 8px; }
  .note {
    padding: 10px 12px;
    background: var(--paper);
    border-left: 3px solid var(--passbook);
    font-size: 13px;
  }
  .note b { color: var(--passbook); }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 8px 8px; border-bottom: 1px solid var(--line); text-align: left; }
  th { font-size: 11px; letter-spacing: 0.08em; color: var(--mute); font-weight: 600; }
  td.num, th.num { text-align: right; font-family: "Cascadia Mono", Consolas, monospace; }
  .toolbar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
  input, select {
    border: 1px solid var(--line);
    background: #fff;
    padding: 7px 10px;
    font: inherit;
    color: var(--ink);
  }
  input:focus, select:focus { outline: 2px solid var(--passbook); outline-offset: 1px; }
  .foot { margin-top: 22px; color: var(--passbook); font-size: 12px; }
  tr.zeroed td { color: #7A8B84; }
  tr.zeroed td:last-child { text-decoration: line-through; }
  .audit {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
    align-items: baseline;
    margin-bottom: 10px;
    padding: 10px 12px;
    background: var(--paper);
    border-left: 3px solid var(--passbook);
  }
  .audit b { color: var(--passbook); }
  .audit.warn { border-left-color: var(--stamp); }
  .audit.warn b { color: var(--stamp); }
  button.btn {
    border: 1px solid var(--line);
    background: #fff;
    padding: 7px 10px;
    font: inherit;
    color: var(--ink);
    cursor: pointer;
  }
  button.btn:hover, button.btn:focus { border-color: var(--passbook); outline: none; }
  tr.mrow { cursor: pointer; }
  tr.mrow:hover td { background: #E7EFEA; }
  tr.mrow.open td { background: #E4ECE8; }
  tr.detail > td { padding: 0 0 10px; background: #fff; }
  table.sub { width: 100%; background: #fff; }
  table.sub th, table.sub td { font-size: 12px; }
  .subwrap { padding: 4px 8px 8px 36px; }
  .share {
    display: inline-block;
    width: 64px;
    height: 6px;
    background: var(--chip);
    vertical-align: middle;
    margin-right: 8px;
  }
  .share > i { display: block; height: 100%; background: var(--passbook); }
  @media (max-width: 1100px) {
    .kpis, .tape, .grid2, .grid3 { grid-template-columns: 1fr 1fr; }
  }
  @media (max-width: 720px) {
    .mast, .kpis, .tape, .grid2, .grid3 { grid-template-columns: 1fr; }
    h1 { font-size: 30px; }
    .meta { text-align: left; }
  }
  @media (prefers-reduced-motion: reduce) {
    * { animation: none !important; transition: none !important; }
  }
</style>
</head>
<body>
<div class="wrap">
  <header class="mast">
    <div>
      <div class="brand" id="brand"></div>
      <h1 id="title"></h1>
    </div>
    <div class="meta">
      持卡人 <b id="who"></b><br />
      卡号末四位 <b id="last4"></b> · <span id="billNote"></span><br />
      <span id="range"></span><br />
      <span id="srcLine"></span>
    </div>
  </header>

  <section class="kpis" id="kpis"></section>
  <section class="tape" id="tape"></section>

  <section class="card" style="margin-bottom:14px" id="rankCard">
    <h2>支付排序 · 同一商户加总</h2>
    <div class="audit" id="audit"></div>
    <div class="toolbar">
      <select id="fMonth"><option value="">全部月份</option></select>
      <select id="fStatus">
        <option value="all">全部消费（含已退成 0）</option>
        <option value="alive">只看真实消费 &gt; 0</option>
        <option value="zero">只看已全额退</option>
      </select>
      <select id="fSort">
        <option value="real">按真实消费</option>
        <option value="count">按笔数</option>
        <option value="gross">按原额</option>
        <option value="name">按商户名</option>
      </select>
      <input id="fQ" type="search" placeholder="搜索商户 / 账单摘要" style="min-width:240px" />
      <button type="button" class="btn" id="expandAll">展开全部</button>
    </div>
    <div style="overflow:auto">
      <table id="rankTable"></table>
    </div>
  </section>

  <section class="grid2">
    <div class="card">
      <h2>月度应还 / 真实消费 / 已还上期</h2>
      <div class="chart" id="trend"></div>
    </div>
    <div class="card">
      <h2>读数</h2>
      <div class="notes" id="notes"></div>
    </div>
  </section>

  <section class="grid2">
    <div class="card">
      <h2>真实消费结构（退款已对回原消费）</h2>
      <div class="chart tall" id="cats"></div>
    </div>
    <div class="card">
      <h2>金额前 15 名（完整名单在上方）</h2>
      <div class="mer-scroll">
        <div class="chart" id="merchants"></div>
      </div>
    </div>
  </section>

  <section class="card" style="margin-bottom:14px">
      <h2>分月分类热力</h2>
    <div class="chart" id="heat" style="height:420px"></div>
  </section>

  <section class="grid2">
    <div class="card">
      <h2>分月账务核对</h2>
      <div style="overflow:auto">
        <table id="monthTable"></table>
      </div>
    </div>
    <div class="card">
      <h2>大额入账 ≥ 300 元</h2>
      <div style="overflow:auto; max-height:420px">
        <table id="largeTable"></table>
      </div>
    </div>
  </section>

  <p class="foot" id="foot"></p>
</div>
<script>
const DATA = __DATA__;
const yen = n => (n < 0 ? "-" : "") + "¥" + Math.abs(n).toLocaleString("zh-CN", {minimumFractionDigits: 2, maximumFractionDigits: 2});
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const months = DATA.months;
const nMonth = months.length;
document.title = DATA.meta.page_title || DATA.meta.title;
document.getElementById("brand").textContent = DATA.meta.brand || "CMBC CREDIT · LEDGER BOARD";
document.getElementById("title").textContent = DATA.meta.title;
document.getElementById("who").textContent = DATA.meta.cardholder;
document.getElementById("last4").textContent = DATA.meta.card_last4 || "";
document.getElementById("billNote").textContent = DATA.meta.bill_note || "账单日每月 14 日";
document.getElementById("range").textContent = DATA.meta.range;
document.getElementById("srcLine").textContent = DATA.meta.source || "";

const kpis = [
  [nMonth + "个月真实消费", DATA.kpis.real_spend],
  ["月均真实消费", DATA.kpis.avg_month],
  ["已抵消退款", DATA.kpis.paired_refunds],
  ["全额退成 0", DATA.kpis.zeroed_count + " 笔"],
  ["循环利息", DATA.kpis.interest],
  ["毛消费（未抵退）", DATA.kpis.gross_spend],
];
document.getElementById("kpis").innerHTML = kpis.map((k,i) =>
  `<div class="kpi${i===0?" accent":""}"><div class="lab">${k[0]}</div><div class="num">${typeof k[1]==="number" ? yen(k[1]) : k[1]}</div></div>`
).join("");

const maxReal = Math.max(...months.map(m => m.real_spend));
document.getElementById("tape").innerHTML = months.map(m => {
  const full = m.cover_pct >= 99.5;
  return `<div class="cell">
    <div class="m">${m.label}</div>
    <div class="due">账单日 ${m.summary.statement_date}<br/>还款日 ${m.summary.due_date}</div>
    <div class="amt">${yen(m.real_spend)}</div>
    <div class="bar"><i style="width:${(m.real_spend/maxReal*100).toFixed(1)}%"></i></div>
    <div class="due">应还 ${yen(m.summary.new_balance)} · 退成 0：${m.zeroed_count} 笔</div>
    ${full ? `<div class="stamp" style="margin-top:8px">近全额还</div>` : ""}
  </div>`;
}).join("");

const peak = months.reduce((a,b) => a.real_spend > b.real_spend ? a : b);
const low = months.reduce((a,b) => a.real_spend < b.real_spend ? a : b);
const topMer = DATA.top_merchants[0];
document.getElementById("notes").innerHTML = [
  `<div class="note"><b>真实消费按「原单 − 对应退款」计算。</b>${DATA.match.unmatched_refunds ? DATA.match.paired_count + " 笔退款对上原消费，未配上 " + yen(DATA.match.unmatched_refunds) + "。" : DATA.match.refund_count + " 笔退款全部对上原消费，其中 " + DATA.match.zeroed_count + " 笔变成 0，" + DATA.match.partial_count + " 笔部分退。"}例如刷 200 再退 200，这一笔真实消费就是 0，不再计入分类和商户。</div>`,
  `<div class="note"><b>${nMonth} 个月真实消费 ${yen(DATA.kpis.real_spend)}</b>，月均 ${yen(DATA.kpis.avg_month)}。最高 ${peak.label} ${yen(peak.real_spend)}，最低 ${low.label} ${yen(low.real_spend)}。</div>`,
  `<div class="note"><b>抵消后退货不再虚增。</b>已配对退款 ${yen(DATA.kpis.paired_refunds)}。金额最高的是 ${topMer.name}，真实消费 ${yen(topMer.amount)}。</div>`,
  `<div class="note"><b>循环利息 ${yen(DATA.kpis.interest)}。</b>${DATA.kpis.paid_full_months} 个月的还款盖住了上期应还。分期利息记在当月消费里。</div>`,
  `<div class="note"><b>固定开支仍在。</b>水电燃气、电信、税费、分期按未退掉的金额计入。卡尾号 ${DATA.meta.card_last4}。</div>`
].join("");

function table(el, headers, rows, rowClass) {
  const last = headers.length - 1;
  el.innerHTML = `<thead><tr>${headers.map((h,i)=>`<th class="${i===last?"num":""}">${h}</th>`).join("")}</tr></thead><tbody>${
    rows.map((r, ri) => `<tr class="${rowClass ? rowClass(ri) : ""}">${r.map((c,i)=>`<td class="${i>=last-1?"num":""}">${c}</td>`).join("")}</tr>`).join("")
  }</tbody>`;
}
table(document.getElementById("monthTable"),
  ["月份","账单日","真实消费","应还","已还上期","退成 0"],
  months.map(m => [m.label, m.summary.statement_date, yen(m.real_spend), yen(m.summary.new_balance), yen(m.summary.payment), m.zeroed_count + " 笔"])
);
table(document.getElementById("largeTable"),
  ["账期","交易日","分类","摘要","真实金额"],
  DATA.large.map(t => [t.month.slice(5)+"月", t.sold, t.category, t.display || t.description, yen(t.real_amount)])
);

function channelOf(desc) {
  const text = desc || "";
  if (text.startsWith("支付宝")) return "支付宝";
  if (text.startsWith("财付通")) return "财付通";
  if (text.startsWith("拼多多")) return "拼多多";
  if (text.startsWith("微信")) return "微信支付";
  if (text.startsWith("京东支付")) return "京东";
  return "账单直扣";
}
function merchantOf(t) {
  const raw = t.display || t.description || "";
  return raw.replace(/^(支付宝|财付通|拼多多支付|微信支付|京东支付)-/, "") || raw;
}
const ALL_CHARGES = DATA.transactions.filter(t => t.amount > 0);
function round2(n) { return Math.round(n * 100) / 100; }
function sumReal(list) { return round2(list.reduce((s, t) => s + (t.real_amount || 0), 0)); }
function groupCharges(list) {
  const map = new Map();
  for (const t of list) {
    const name = merchantOf(t);
    let g = map.get(name);
    if (!g) {
      g = { name, txns: [], count: 0, gross: 0, refunded: 0, real: 0, channels: new Set() };
      map.set(name, g);
    }
    g.txns.push(t);
    g.count += 1;
    g.gross = round2(g.gross + t.amount);
    g.refunded = round2(g.refunded + (t.refunded || 0));
    g.real = round2(g.real + (t.real_amount || 0));
    g.channels.add(channelOf(t.description));
  }
  for (const g of map.values()) {
    g.txns.sort((a, b) => (a.month + a.sold).localeCompare(b.month + b.sold));
    g.channel = [...g.channels].join(" / ");
  }
  return [...map.values()];
}
const ALL_REAL = sumReal(ALL_CHARGES);
const fMonth = document.getElementById("fMonth");
[...new Set(ALL_CHARGES.map(t => t.month))].sort().forEach(m => {
  const o = document.createElement("option"); o.value = m; o.textContent = m; fMonth.appendChild(o);
});
let openNames = new Set();
let expandAll = false;
let currentNames = [];
function renderRank() {
  const q = document.getElementById("fQ").value.trim();
  const st = document.getElementById("fStatus").value;
  const sort = document.getElementById("fSort").value;
  const list = ALL_CHARGES.filter(t => {
    if (st === "alive" && !(t.real_amount > 0.009)) return false;
    if (st === "zero" && t.match_status !== "已全额退") return false;
    if (fMonth.value && t.month !== fMonth.value) return false;
    if (!q) return true;
    const name = merchantOf(t);
    return name.includes(q) || t.description.includes(q) || (t.display || "").includes(q) || t.category.includes(q);
  });
  const groups = groupCharges(list);
  groups.sort((a, b) => {
    if (sort === "count") return b.count - a.count || b.real - a.real || a.name.localeCompare(b.name, "zh");
    if (sort === "gross") return b.gross - a.gross || b.real - a.real || a.name.localeCompare(b.name, "zh");
    if (sort === "name") return a.name.localeCompare(b.name, "zh");
    return b.real - a.real || b.count - a.count || a.name.localeCompare(b.name, "zh");
  });
  currentNames = groups.map(g => g.name);
  const shownReal = sumReal(list);
  const baseOk = Math.abs(ALL_REAL - DATA.kpis.real_spend) < 0.02 && ALL_CHARGES.length > 0;
  const fullView = list.length === ALL_CHARGES.length;
  const audit = document.getElementById("audit");
  audit.className = "audit" + (baseOk ? "" : " warn");
  const head = baseOk
    ? `全部 <b>${ALL_CHARGES.length}</b> 笔消费都已归入商户，真实消费 <b>${yen(ALL_REAL)}</b>，与上方合计一致。`
    : `归集 <b>${ALL_CHARGES.length}</b> 笔、${yen(ALL_REAL)}，与上方真实消费 ${yen(DATA.kpis.real_spend)} 对不上。`;
  const tail = fullView
    ? `当前 <b>${groups.length}</b> 个商户、<b>${list.length}</b> 笔，一笔未漏。支付宝与财付通里的同一商户已加在一起。`
    : `当前筛选 <b>${groups.length}</b> 个商户、<b>${list.length}</b> 笔，合计 ${yen(shownReal)}。清除筛选可回到全部 ${ALL_CHARGES.length} 笔。`;
  audit.innerHTML = `<span>${head}</span><span>${tail}</span>`;
  const maxReal = Math.max(0.01, ...groups.map(g => g.real));
  const body = groups.map((g, i) => {
    const opened = expandAll || openNames.has(g.name);
    const kids = g.txns.map(t => `<tr class="${t.match_status === "已全额退" ? "zeroed" : ""}">
      <td>${esc(t.month)}</td><td>${esc(t.sold)}</td><td>${esc(t.posted)}</td><td>${esc(t.match_status)}</td>
      <td>${esc(t.category)}</td><td>${esc(t.description)}</td>
      <td class="num">${yen(t.amount)}</td><td class="num">${yen(t.refunded || 0)}</td><td class="num">${yen(t.real_amount || 0)}</td>
    </tr>`).join("");
    const detail = opened ? `<tr class="detail"><td colspan="7"><div class="subwrap">
      <div class="due" style="margin-bottom:6px">${esc(g.name)} · ${g.count} 笔 · 真实 ${yen(g.real)}</div>
      <table class="sub"><thead><tr>
        <th>账期</th><th>交易日</th><th>记账日</th><th>状态</th><th>分类</th><th>账单摘要</th>
        <th class="num">原额</th><th class="num">已退</th><th class="num">真实</th>
      </tr></thead><tbody>${kids}</tbody></table>
    </div></td></tr>` : "";
    return `<tr class="mrow${opened ? " open" : ""}" data-name="${esc(g.name)}">
      <td>${i + 1}</td>
      <td><span class="chev">${opened ? "▾" : "▸"}</span>${esc(g.name)}</td>
      <td>${esc(g.channel)}</td>
      <td class="num">${g.count}</td>
      <td class="num">${yen(g.gross)}</td>
      <td class="num">${yen(g.refunded)}</td>
      <td class="num"><span class="share"><i style="width:${Math.max(2, g.real / maxReal * 100).toFixed(1)}%"></i></span>${yen(g.real)}</td>
    </tr>${detail}`;
  }).join("");
  const foot = `<tr>
    <td></td><td>合计</td><td></td>
    <td class="num">${list.length}</td>
    <td class="num">${yen(round2(list.reduce((s, t) => s + t.amount, 0)))}</td>
    <td class="num">${yen(round2(list.reduce((s, t) => s + (t.refunded || 0), 0)))}</td>
    <td class="num">${yen(shownReal)}</td>
  </tr>`;
  document.getElementById("rankTable").innerHTML = `<thead><tr>
    <th>排名</th><th>商户</th><th>渠道</th><th class="num">笔数</th>
    <th class="num">原额</th><th class="num">已退</th><th class="num">真实消费</th>
  </tr></thead><tbody>${body}${foot}</tbody>`;
  document.getElementById("expandAll").textContent = expandAll ? "收起全部" : "展开全部";
}
document.getElementById("rankTable").addEventListener("click", ev => {
  const tr = ev.target.closest("tr.mrow");
  if (!tr) return;
  const name = tr.dataset.name;
  if (expandAll) {
    expandAll = false;
    openNames = new Set(currentNames);
    openNames.delete(name);
  } else if (openNames.has(name)) {
    openNames.delete(name);
  } else {
    openNames.add(name);
  }
  renderRank();
});
document.getElementById("expandAll").addEventListener("click", () => {
  expandAll = !expandAll;
  if (!expandAll) openNames.clear();
  renderRank();
});
["input", "change"].forEach(ev => {
  fMonth.addEventListener(ev, renderRank);
  document.getElementById("fQ").addEventListener(ev, renderRank);
  document.getElementById("fStatus").addEventListener(ev, renderRank);
  document.getElementById("fSort").addEventListener(ev, renderRank);
});
renderRank();
document.getElementById("foot").textContent =
  `金额单位：人民币元。真实消费 = 原消费 − 对上的退款。退款 ${DATA.match.refund_count} 笔已配回原消费，不另计一笔。` +
  `支付排序按商户加总，去掉渠道前缀后名称相同的算同一家，全部 ${ALL_CHARGES.length} 笔消费都在表里。` +
  `本期应还仍取自账单。原始邮件在「${DATA.meta.archive || "bills"}」。`;

function bootCharts() {
  if (!window.echarts) return;
  const labels = months.map(m => m.label);
  const trend = echarts.init(document.getElementById("trend"));
  trend.setOption({
    color: ["#184536", "#C4452D", "#6B8F7A"],
    tooltip: { trigger: "axis" },
    legend: { data: ["本期应还", "真实消费", "已还上期"], bottom: 0 },
    grid: { left: 48, right: 16, top: 24, bottom: 48 },
    xAxis: { type: "category", data: labels, axisLine: { lineStyle: { color: "#8AA198" } } },
    yAxis: { type: "value", splitLine: { lineStyle: { color: "#D5DFDA" } } },
    series: [
      { name: "本期应还", type: "line", smooth: true, data: months.map(m => m.summary.new_balance) },
      { name: "真实消费", type: "bar", data: months.map(m => m.real_spend) },
      { name: "已还上期", type: "line", smooth: true, data: months.map(m => m.summary.payment) }
    ]
  });
  const catNames = Object.keys(DATA.categories);
  const cats = echarts.init(document.getElementById("cats"));
  cats.setOption({
    color: ["#184536","#2E6B52","#C4452D","#8AA198","#0D5C44","#B07A2A","#4D6E62","#6B4A3A"],
    tooltip: { trigger: "item" },
    series: [{
      type: "pie", radius: ["36%", "64%"],
      label: { formatter: "{b}\n{c}" },
      data: catNames.map(n => ({ name: n, value: DATA.categories[n] }))
    }]
  });
  const merEl = document.getElementById("merchants");
  const top = groupCharges(ALL_CHARGES).filter(g => g.real > 0.009).sort((a, b) => a.real - b.real).slice(-15);
  merEl.style.height = Math.max(380, top.length * 28 + 24) + "px";
  const mer = echarts.init(merEl);
  mer.setOption({
    color: ["#184536"],
    tooltip: { trigger: "axis" },
    grid: { left: 168, right: 88, top: 8, bottom: 16 },
    xAxis: { type: "value", splitLine: { lineStyle: { color: "#D5DFDA" } } },
    yAxis: { type: "category", data: top.map(t => t.name.replace("平台商户","").replace("网络科技","").replace("有限公司","").replace("有限公","")) },
    series: [{ type: "bar", data: top.map(t => t.real), barMaxWidth: 16, label: { show: true, position: "right", formatter: p => yen(p.value) } }]
  });
  const heat = echarts.init(document.getElementById("heat"));
  const heatCats = Object.keys(DATA.categories);
  const heatData = [];
  heatCats.forEach((c, yi) => {
    months.forEach((m, xi) => {
      heatData.push([xi, yi, +(DATA.cat_month[c]?.[m.month] || 0).toFixed(2)]);
    });
  });
  heat.setOption({
    tooltip: { formatter: p => `${heatCats[p.value[1]]} · ${labels[p.value[0]]}：${yen(p.value[2])}` },
    grid: { left: 88, right: 24, top: 10, bottom: 40 },
    xAxis: { type: "category", data: labels },
    yAxis: { type: "category", data: heatCats },
    visualMap: { min: 0, max: Math.max(1, ...heatData.map(d => d[2])), orient: "horizontal", left: "center", bottom: 0, inRange: { color: ["#E8F0EB", "#184536"] } },
    series: [{ type: "heatmap", data: heatData, label: { show: false } }]
  });
  window.addEventListener("resize", () => { trend.resize(); cats.resize(); mer.resize(); heat.resize(); });
}
bootCharts();
</script>
</body>
</html>
"""

OUT.write_text(HTML.replace("__DATA__", payload).replace("__PAGE_TITLE__", page_title), encoding="utf-8")
print("WROTE", OUT, "bytes", OUT.stat().st_size)
