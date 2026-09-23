# -*- coding: utf-8 -*-
"""Parse CMBC credit-card e-statements (.eml) into structured JSON."""
from __future__ import annotations

import email
import pathlib
import re
from html.parser import HTMLParser


class HtmlText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if tag in ("br", "p", "tr", "div", "h1", "h2", "h3", "li"):
            self.parts.append("\n")
        if tag == "td":
            self.parts.append("\t")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        if tag in ("p", "tr", "div"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = HtmlText()
    parser.feed(html)
    plain = re.sub(r"[ \t\xa0]+", " ", "".join(parser.parts))
    return re.sub(r"\n{2,}", "\n", plain)


def money(s: str) -> float:
    return float(s.replace(",", "").replace("¥", "").replace("RMB", "").strip())


def extract_html(eml_path: pathlib.Path) -> str:
    msg = email.message_from_bytes(eml_path.read_bytes())
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            raw = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "gbk"
            return raw.decode(charset, errors="replace")
    raise RuntimeError(f"no html in {eml_path}")


def parse_summary(text: str) -> dict:
    name_m = re.search(r"尊敬的(.+?)[：:]", text)
    stmt_m = re.search(r"本期账单日[\s\S]{0,80}?(\d{4}/\d{2}/\d{2})", text)
    due_m = re.search(r"本期最后还款日[\s\S]{0,80}?(\d{4}/\d{2}/\d{2})", text)
    new_bal_m = re.search(r"RMB\s*([\d,]+\.\d{2})\s+RMB\s*([\d,]+\.\d{2})", text)
    # fallback for new balance block
    if not new_bal_m:
        new_bal_m = re.search(
            r"本期应还款金额[\s\S]{0,200}?RMB\s*([\d,]+\.\d{2})[\s\S]{0,80}?RMB\s*([\d,]+\.\d{2})",
            text,
        )

    def grab(label: str) -> float | None:
        m = re.search(rf"{label}[\s\S]{0,120}?(-?[\d,]+\.\d{{2}})", text)
        return money(m.group(1)) if m else None

    new_balance = money(new_bal_m.group(1)) if new_bal_m else grab("本期应还款金额")
    min_payment = money(new_bal_m.group(2)) if new_bal_m else grab("本期最低还款额")

    return {
        "cardholder": name_m.group(1).strip() if name_m else None,
        "statement_date": stmt_m.group(1) if stmt_m else None,
        "due_date": due_m.group(1) if due_m else None,
        "new_balance": new_balance,
        "min_payment": min_payment,
        "balance_bf": grab("上期账单金额"),
        "payment": grab("本期已还金额"),
        "new_charges": grab("本期账单金额"),
        "adjustment": grab("本期调整金额"),
        "interest": grab("循环利息"),
    }


DATE_RE = re.compile(r"^\d{2}/\d{2}$")
AMT_RE = re.compile(r"^-?[\d,]+\.\d{2}$")
CARD_RE = re.compile(r"^\d{4}$")


def parse_transactions(text: str) -> list[dict]:
    start = text.find("交易日")
    end = text.find("★")
    if start < 0:
        return []
    block = text[start : end if end > start else None]
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    # drop header labels
    skip = {
        "交易日",
        "SOLD",
        "记账日",
        "POSTED",
        "交易摘要",
        "DESCRIPTION",
        "交易金额",
        "AMOUNT",
        "卡号末四位",
        "CARD No. (last 4 digits)",
        "CARD No. (last 4 digits)",
    }
    tokens = [ln for ln in lines if ln not in skip and "CARD" not in ln]
    txns = []
    i = 0
    while i + 4 < len(tokens):
        sold, posted, desc, amt, card = tokens[i : i + 5]
        if DATE_RE.match(sold) and DATE_RE.match(posted) and AMT_RE.match(amt) and CARD_RE.match(card):
            txns.append(
                {
                    "sold": sold,
                    "posted": posted,
                    "description": re.sub(r"\s+", " ", desc).strip(),
                    "amount": money(amt),
                    "card_last4": card,
                }
            )
            i += 5
            continue
        i += 1
    return txns


CATEGORY_RULES = [
    (r"自助转入|还款", "还款"),
    (r"循环利息|利息|年费|违约金|手续费", "息费"),
    (r"国家税务|税务总局|个税|税款", "税费"),
    (r"燃气|供电|电费|水费|公共事业", "水电燃气"),
    (r"物业", "物业"),
    (r"中国电信|移动|联通|宽带", "通讯"),
    (r"轨道交通|地铁", "公共交通"),
    (r"嘀嘀无限|滴滴", "出行"),
    (r"拉扎斯|饿了么", "外卖餐饮"),
    (r"北京三快|美团", "外卖餐饮"),
    (r"美年大健康|医院|药房|医药", "医疗健康"),
    (r"生鲜传奇|鲜岛|淘乡甜|今日卖场|梦图贸易|牧丰", "生鲜日用"),
    (r"格物致品", "电商购物"),
    (r"拼多多", "电商购物"),
    (r"京东", "电商购物"),
    (r"天猫|淘宝|浙江天猫", "电商购物"),
    (r"所见所得", "娱乐会员"),
]


def categorize(desc: str, amount: float) -> str:
    if amount < 0 and "自助转入" not in desc and "还款" not in desc:
        if desc.strip() in {"支付宝", "财付通"}:
            return "退款"
    for pat, cat in CATEGORY_RULES:
        if re.search(pat, desc):
            return cat
    if desc.startswith("支付宝-") or desc.startswith("财付通-"):
        return "其他消费"
    if desc.strip() in {"支付宝", "财付通"} and amount > 0:
        return "其他消费"
    return "其他消费"


def parse_file(path: pathlib.Path) -> dict:
    month = None
    m = re.search(r"(\d{4})年(\d{2})月", path.name)
    if m:
        month = f"{m.group(1)}-{m.group(2)}"
    html = extract_html(path)
    text = html_to_text(html)
    summary = parse_summary(text)
    txns = parse_transactions(text)
    for t in txns:
        t["category"] = categorize(t["description"], t["amount"])
        t["month"] = month
    charges = [t for t in txns if t["amount"] > 0]
    refunds = [t for t in txns if t["amount"] < 0 and t["category"] == "退款"]
    repayments = [t for t in txns if t["category"] == "还款"]
    spend = round(sum(t["amount"] for t in charges), 2)
    refund_sum = round(sum(t["amount"] for t in refunds), 2)
    repay_sum = round(sum(t["amount"] for t in repayments), 2)
    return {
        "file": path.name,
        "month": month,
        "summary": summary,
        "txn_count": len(txns),
        "charge_count": len(charges),
        "refund_count": len(refunds),
        "gross_spend": spend,
        "refunds": refund_sum,
        "net_spend": round(spend + refund_sum, 2),
        "repayments": repay_sum,
        "transactions": txns,
        "parse_ok": bool(summary.get("new_balance") is not None and txns),
    }


