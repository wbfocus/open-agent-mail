# -*- coding: utf-8 -*-
"""Build a statement dashboard from the user's own .eml files."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from parse_cmb_statements import extract_html as extract_cmb_html
from parse_cmb_statements import parse_summary as parse_cmb_summary
from parse_cmb_statements import parse_transactions as parse_cmb_transactions
from parse_cmbc_statements import extract_html as extract_cmbc_html
from parse_cmbc_statements import html_to_text
from parse_cmbc_statements import parse_summary as parse_cmbc_summary
from parse_cmbc_statements import parse_transactions as parse_cmbc_transactions

CATEGORY_RULES = [
    (r"国家税务|税务总局|个税|税款", "税费"),
    (r"燃气|供电|电费|水费|公共事业", "水电燃气"),
    (r"物业", "物业"),
    (r"中国电信|中国移动|中国联通|宽带", "通讯"),
    (r"轨道交通|地铁|铁路|12306", "公共交通"),
    (r"嘀嘀|滴滴|顺风车|高德", "出行"),
    (r"拉扎斯|饿了么", "外卖餐饮"),
    (r"北京三快|美团", "外卖餐饮"),
    (r"美年大健康|医院|药房|医药|大健康", "医疗健康"),
    (r"生鲜传奇|鲜岛|淘乡甜|今日卖场|梦图贸易|牧丰|加油站", "生鲜日用"),
    (r"格物致品", "电商购物"),
    (r"拼多多", "电商购物"),
    (r"京东", "电商购物"),
    (r"天猫|淘宝|浙江天猫", "电商购物"),
    (r"所见所得", "娱乐会员"),
    (r"柏来科技", "共享出行"),
]

MERCHANT_ALIASES = [
    (r"格物致品", "抖音"),
    (r"北京三快|美团", "美团"),
    (r"拉扎斯", "饿了么"),
    (r"嘀嘀|滴滴|高德", "打车"),
    (r"中国电信", "中国电信"),
    (r"中国铁路", "中国铁路"),
    (r"雅顿", "伊丽莎白雅顿"),
]

CHANNEL_PREFIX = re.compile(r"^(支付宝|财付通|拼多多支付|微信支付|京东支付)-")


def display_name(desc: str) -> str:
    if desc.startswith("分期还款 本金"):
        return "分期还款 本金"
    if desc.startswith("分期还款 分期利息"):
        return "分期还款 分期利息"
    stripped = CHANNEL_PREFIX.sub("", desc)
    for pattern, name in MERCHANT_ALIASES:
        if re.search(pattern, stripped):
            return name
    return stripped


def categorize_cmbc(desc: str, amount: float) -> str:
    if "自助转入" in desc or "还款" in desc:
        return "还款"
    if amount < 0:
        return "退款"
    for pattern, category in CATEGORY_RULES:
        if re.search(pattern, desc):
            return category
    if re.fullmatch(r"(支付宝|财付通)-[\u4e00-\u9fff]{2,4}", desc.strip()):
        return "个人往来"
    return "其他消费"


def categorize_cmb(section: str, desc: str) -> str:
    if section == "还款":
        return "还款"
    if section == "退款":
        return "退款"
    if section == "分期":
        return "息费" if "利息" in desc else "分期"
    if section in {"费用", "利息"}:
        return "息费"
    if section == "取现":
        return "取现"
    return categorize_cmbc(desc, 1)


def sold_date(txn: dict) -> date:
    year_s, month_s = map(int, txn["month"].split("-"))
    month, day = map(int, txn["sold"].split("/"))
    year = year_s - 1 if month > month_s else year_s
    return date(year, month, day)


def match_refunds(txns: list[dict]) -> dict:
    for txn in txns:
        txn["refunded"] = 0.0
        txn["real_amount"] = round(txn["amount"], 2) if txn["amount"] > 0 else 0.0
        txn["match_status"] = "未退" if txn["amount"] > 0 else txn.get("category", "")
        txn["matched_to"] = None

    charges = [txn for txn in txns if txn["amount"] > 0]
    refunds = sorted((txn for txn in txns if txn["category"] == "退款"), key=sold_date)
    paired = 0
    paired_amt = 0.0
    unmatched_amt = 0.0

    def remaining(charge: dict) -> float:
        return round(charge["amount"] - charge["refunded"], 2)

    for refund in refunds:
        need = abs(refund["amount"])
        refund_day = sold_date(refund)
        refund_desc = refund["description"].strip()
        best = None
        best_score = None
        for charge in charges:
            left = remaining(charge)
            if left < 0.01 or need - left > 0.01:
                continue
            charge_day = sold_date(charge)
            if charge_day > refund_day:
                continue
            days = (refund_day - charge_day).days
            if days > 75:
                continue
            charge_desc = charge["description"].strip()
            score = 100 - days
            if refund_desc not in {"支付宝", "财付通"} and (
                refund_desc == charge_desc
                or refund_desc in charge_desc
                or charge_desc.endswith(refund_desc.replace("支付宝-", "").replace("财付通-", ""))
            ):
                score += 1000
            if (refund_desc.startswith("支付宝") and charge_desc.startswith("支付宝")) or (
                refund_desc.startswith("财付通") and charge_desc.startswith("财付通")
            ):
                score += 40
            if abs(left - need) < 0.01:
                score += 80
            if best_score is None or score > best_score:
                best_score = score
                best = charge
        if best is None:
            refund["match_status"] = "未配对退款"
            refund["real_amount"] = refund["amount"]
            unmatched_amt = round(unmatched_amt + refund["amount"], 2)
            continue
        apply = min(need, remaining(best))
        best["refunded"] = round(best["refunded"] + apply, 2)
        best["real_amount"] = round(best["amount"] - best["refunded"], 2)
        if best["real_amount"] < 0.01:
            best["real_amount"] = 0.0
            best["match_status"] = "已全额退"
        else:
            best["match_status"] = "部分退"
        refund["matched_to"] = f"{best['month']} {best['sold']} {best['description']}"
        refund["match_status"] = "已配对"
        refund["real_amount"] = 0.0
        paired += 1
        paired_amt = round(paired_amt + apply, 2)

    return {
        "paired_count": paired,
        "refund_count": len(refunds),
        "paired_amount": paired_amt,
        "unmatched_refunds": unmatched_amt,
        "zeroed_count": sum(1 for txn in charges if txn["match_status"] == "已全额退"),
        "partial_count": sum(1 for txn in charges if txn["match_status"] == "部分退"),
    }


def detect_bank(path: Path) -> str:
    html = extract_cmbc_html(path)
    if "statementCycle" in html or "cmbchina.com" in html or "招商银行" in html:
        return "cmb"
    return "cmbc"


def load_statement(path: Path) -> tuple[str, dict, list[dict]]:
    bank = detect_bank(path)
    if bank == "cmb":
        html = extract_cmb_html(path)
        summary = parse_cmb_summary(html)
        txns, problems = parse_cmb_transactions(html)
        if problems:
            raise RuntimeError(f"{path.name}: {'; '.join(problems)}")
        month = summary.get("month")
        for txn in txns:
            section = txn.pop("section", "")
            txn["category"] = categorize_cmb(section, txn["description"])
            txn["display"] = display_name(txn["description"])
            txn["month"] = month
        summary["bank_code"] = "cmb"
        return bank, summary, txns

    html = extract_cmbc_html(path)
    text = html_to_text(html)
    summary = parse_cmbc_summary(text)
    month_m = re.search(r"(\d{4})年(\d{2})月", path.name)
    if month_m:
        month = f"{month_m.group(1)}-{month_m.group(2)}"
    elif summary.get("statement_date"):
        year, mon, _day = summary["statement_date"].split("/")
        month = f"{year}-{mon}"
    else:
        raise RuntimeError(f"{path.name}: 无法确定账单月份，请在文件名中保留“2026年01月”")
    txns = parse_cmbc_transactions(text)
    if not txns:
        raise RuntimeError(f"{path.name}: 没有解析到交易")
    for txn in txns:
        txn["category"] = categorize_cmbc(txn["description"], txn["amount"])
        txn["display"] = display_name(txn["description"])
        txn["month"] = month
    summary["bank_code"] = "cmbc"
    summary["month"] = month
    return bank, summary, txns


def build(input_dir: Path, output_html: Path) -> dict:
    files = sorted(path for path in input_dir.glob("*.eml") if path.is_file())
    if not files:
        raise SystemExit(f"在 {input_dir} 里没有找到 .eml 账单。请先把转发到 Agent Mail 的账单下载到这个目录。")

    months = []
    all_txns = []
    banks = set()
    for path in files:
        bank, summary, txns = load_statement(path)
        banks.add(bank)
        month = summary["month"]
        charges = [txn for txn in txns if txn["amount"] > 0]
        refunds = [txn for txn in txns if txn["category"] == "退款"]
        repayments = [txn for txn in txns if txn["category"] == "还款"]
        repay_sum = round(sum(txn["amount"] for txn in repayments), 2)
        net = round(sum(txn["amount"] for txn in charges) + sum(txn["amount"] for txn in refunds), 2)
        if summary.get("payment") is None:
            summary["payment"] = abs(repay_sum)
        if summary.get("new_charges") is None:
            summary["new_charges"] = net
        if summary.get("interest") is None:
            summary["interest"] = 0.0
        months.append(
            {
                "month": month,
                "label": f"{int(month.split('-')[1])}月",
                "file": path.name,
                "summary": summary,
                "txn_count": len(txns),
                "charge_count": len(charges),
                "refund_count": len(refunds),
                "gross_spend": round(sum(txn["amount"] for txn in charges), 2),
                "refunds": round(sum(txn["amount"] for txn in refunds), 2),
                "net_spend": net,
                "repayments": repay_sum,
            }
        )
        all_txns.extend(txns)

    months.sort(key=lambda item: item["month"])
    match_stats = match_refunds(all_txns)
    paid_full = []
    for index, month in enumerate(months):
        month_txns = [txn for txn in all_txns if txn["month"] == month["month"]]
        month["real_spend"] = round(
            sum(
                txn["real_amount"]
                for txn in month_txns
                if txn["category"] not in {"还款", "退款"} or txn["match_status"] == "未配对退款"
            ),
            2,
        )
        month["zeroed_count"] = sum(1 for txn in month_txns if txn["match_status"] == "已全额退")
        prev = months[index - 1]["summary"]["new_balance"] if index else month["summary"].get("balance_bf")
        if month["summary"].get("balance_bf") is None:
            month["summary"]["balance_bf"] = prev
        pay = month["summary"].get("payment")
        prev = month["summary"].get("balance_bf") or 0
        cover = round(pay / prev * 100, 1) if prev and pay is not None else 0
        month["cover_pct"] = cover
        paid_full.append(bool(prev and pay is not None and pay >= prev - 5))

    cats: dict[str, float] = {}
    merchants: dict[str, dict] = {}
    cat_month: dict[str, dict[str, float]] = {}
    for txn in all_txns:
        if txn["category"] in {"还款", "退款"}:
            continue
        real = txn.get("real_amount", txn["amount"])
        shown = txn.get("display") or txn["description"]
        cats[txn["category"]] = round(cats.get(txn["category"], 0) + real, 2)
        bucket = merchants.setdefault(shown, {"name": shown, "amount": 0.0, "count": 0, "category": txn["category"]})
        bucket["amount"] = round(bucket["amount"] + real, 2)
        if txn["amount"] > 0:
            bucket["count"] += 1
        by_month = cat_month.setdefault(txn["category"], {})
        by_month[txn["month"]] = round(by_month.get(txn["month"], 0) + real, 2)

    cards = Counter(txn["card_last4"] for txn in all_txns if txn.get("card_last4"))
    card_last4 = cards.most_common(1)[0][0] if cards else ""
    holder = next((month["summary"].get("cardholder") for month in months if month["summary"].get("cardholder")), "持卡人")
    first, last = months[0]["month"], months[-1]["month"]
    if banks == {"cmb"}:
        title, brand, bank_name, bill_note = (
            "招商银行信用卡账单看板",
            "CMB CREDIT · LEDGER BOARD",
            "招商银行信用卡",
            "账单周期以对账单为准",
        )
    elif banks == {"cmbc"}:
        title, brand, bank_name, bill_note = (
            "民生信用卡账单看板",
            "CMBC CREDIT · LEDGER BOARD",
            "中国民生银行信用卡",
            "账单日以对账单为准",
        )
    else:
        title, brand, bank_name, bill_note = (
            "信用卡账单看板",
            "CREDIT · LEDGER BOARD",
            "信用卡",
            "账单日以对账单为准",
        )
    data = {
        "meta": {
            "title": title,
            "page_title": f"{bank_name} · {first[:4]}年{int(first[5:])}–{int(last[5:])}月账单看板",
            "brand": brand,
            "cardholder": holder,
            "card_last4": card_last4,
            "bank": bank_name,
            "bill_note": bill_note,
            "range": f"{first[:4]}年{int(first[5:])}月–{int(last[5:])}月账单周期",
            "source": f"持卡人转发到自己 Agent Mail 的 {len(months)} 封电子账单",
            "archive": "bills",
        },
        "kpis": {
            "real_spend": round(sum(month["real_spend"] for month in months), 2),
            "net_spend": round(sum(month["net_spend"] for month in months), 2),
            "gross_spend": round(sum(month["gross_spend"] for month in months), 2),
            "refunds": round(sum(month["refunds"] for month in months), 2),
            "paired_refunds": match_stats["paired_amount"],
            "unmatched_refunds": match_stats["unmatched_refunds"],
            "zeroed_count": match_stats["zeroed_count"],
            "new_balance_sum": round(sum(month["summary"].get("new_balance") or 0 for month in months), 2),
            "interest": round(sum(month["summary"].get("interest") or 0 for month in months), 2),
            "avg_month": round(sum(month["real_spend"] for month in months) / len(months), 2),
            "txn_count": len(all_txns),
            "paid_full_months": sum(paid_full),
        },
        "match": match_stats,
        "months": months,
        "categories": dict(sorted(((k, v) for k, v in cats.items() if v > 0.009), key=lambda item: -item[1])),
        "refunds": cats.get("退款", 0),
        "cat_month": cat_month,
        "top_merchants": sorted(merchants.values(), key=lambda item: -item["amount"]),
        "large": sorted(
            [txn for txn in all_txns if txn.get("real_amount", 0) >= 300 and txn["category"] not in {"还款", "退款"}],
            key=lambda txn: -txn["real_amount"],
        )[:20],
        "transactions": [txn for txn in all_txns if txn["category"] != "还款"],
    }
    data_path = input_dir / "dashboard-data.json"
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    output_html.parent.mkdir(parents=True, exist_ok=True)
    import subprocess

    subprocess.check_call(
        [sys.executable, str(Path(__file__).parent / "generate_dashboard_html.py"), str(input_dir), str(output_html)]
    )
    print(json.dumps({"html": str(output_html), "months": len(months), "real_spend": data["kpis"]["real_spend"], "card_last4": card_last4}, ensure_ascii=False))
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="从电子账单 .eml 生成 HTML 看板")
    parser.add_argument("--input", default="bills", help="存放 .eml 的目录")
    parser.add_argument("--output", default="docs/dashboard.html", help="输出的 HTML 路径")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    build((root / args.input).resolve(), (root / args.output).resolve())


if __name__ == "__main__":
    main()
