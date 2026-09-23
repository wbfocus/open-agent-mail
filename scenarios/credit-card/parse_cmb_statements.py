# -*- coding: utf-8 -*-
"""Parse China Merchants Bank credit-card e-statements (.eml)."""
from __future__ import annotations

import email
import html as html_lib
import re
from pathlib import Path

SECTIONS = {"还款", "分期", "费用", "退款", "消费", "取现", "利息"}
DATE_RE = re.compile(r"^\d{4}$")
AMOUNT_RE = re.compile(r"^-?[\d,]+\.\d{2}$")


def money(raw: str) -> float:
    text = html_lib.unescape(raw).replace("¥", "").replace(",", "").replace("\xa0", "").strip()
    return float(text)


def is_mmdd(token: str) -> bool:
    if not DATE_RE.fullmatch(token):
        return False
    month, day = int(token[:2]), int(token[2:])
    return 1 <= month <= 12 and 1 <= day <= 31


def extract_html(eml_path: Path) -> str:
    msg = email.message_from_bytes(eml_path.read_bytes())
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            raw = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace")
    raise RuntimeError(f"no html in {eml_path}")


def field(html: str, element_id: str) -> str:
    match = re.search(rf"id=['\"]{element_id}['\"][^>]*>(.*?)</", html, re.I | re.S)
    if not match:
        return ""
    text = re.sub(r"<[^>]+>", "", match.group(1))
    return re.sub(r"\s+", " ", html_lib.unescape(text).replace("\xa0", " ")).strip()


def font_texts(html: str) -> list[str]:
    texts: list[str] = []
    for match in re.finditer(r"<FONT[^>]*>(.*?)</FONT>", html, re.I | re.S):
        text = re.sub(r"<[^>]+>", "", match.group(1))
        text = re.sub(r"\s+", " ", html_lib.unescape(text).replace("\xa0", " ")).strip()
        if text:
            texts.append(text)
    return texts


def parse_summary(html: str) -> dict:
    plain = re.sub(r"<[^>]+>", " ", html)
    plain = re.sub(r"\s+", " ", html_lib.unescape(plain))
    holder = re.search(r"尊敬的\s*(.+?)\s*[，,]", plain)
    cycle = field(html, "statementCycle")
    cycle_m = re.search(r"(\d{4})/(\d{2})/\d{2}-(\d{4})/(\d{2})/\d{2}", cycle)
    bill_m = re.search(r"(\d{2})月账单", plain)
    if cycle_m:
        month = f"{cycle_m.group(3)}-{cycle_m.group(4)}"
    elif bill_m:
        month = None
    else:
        month = None
    return {
        "cardholder": holder.group(1).strip() if holder else field(html, "shortName"),
        "short_name": field(html, "shortName"),
        "statement_cycle": cycle,
        "statement_date": cycle.split("-")[-1] if "-" in cycle else None,
        "due_date": field(html, "paymentDueDate").replace("-", "/"),
        "credit_limit": money(field(html, "creditLimit")) if field(html, "creditLimit") else None,
        "new_balance": money(field(html, "D1rmbLcurrBal")) if field(html, "D1rmbLcurrBal") else None,
        "min_payment": money(field(html, "D1rmbLdueAmt")) if field(html, "D1rmbLdueAmt") else None,
        "balance_bf": money(field(html, "D1rmbLbegBal")) if field(html, "D1rmbLbegBal") else None,
        "payment": money(field(html, "D1rmbLpaymentAmt")) if field(html, "D1rmbLpaymentAmt") else None,
        "new_charges": money(field(html, "D1rmbLdebits")) if field(html, "D1rmbLdebits") else None,
        "adjustment": money(field(html, "D1rmbLcreditAmt")) if field(html, "D1rmbLcreditAmt") else None,
        "interest": money(field(html, "D1rmbLinterest")) if field(html, "D1rmbLinterest") else 0.0,
        "month": month,
        "account": "个人消费卡" if "个人消费卡" in plain else None,
    }


def mmdd(token: str) -> str:
    return f"{token[:2]}/{token[2:]}"


def parse_transactions(html: str) -> tuple[list[dict], list[str]]:
    texts = font_texts(html)
    start = None
    for index, token in enumerate(texts):
        if token in SECTIONS and index + 1 < len(texts) and is_mmdd(texts[index + 1]):
            start = index
            break
    if start is None:
        return [], ["no transaction section"]

    txns: list[dict] = []
    problems: list[str] = []
    section = None
    index = start
    while index < len(texts):
        token = texts[index]
        if token in SECTIONS:
            section = token
            index += 1
            continue
        if not is_mmdd(token):
            break
        sold = token
        index += 1
        if index < len(texts) and is_mmdd(texts[index]):
            posted = texts[index]
            index += 1
        else:
            posted = sold
        if index >= len(texts):
            problems.append(f"truncated after {sold}")
            break
        desc = texts[index]
        index += 1
        if index >= len(texts) or not re.search(r"-?[\d,]+\.\d{2}", texts[index]):
            problems.append(f"missing amount after {desc}")
            break
        amount = money(texts[index])
        index += 1
        card = ""
        if index < len(texts) and DATE_RE.fullmatch(texts[index]) and not is_mmdd(texts[index]):
            card = texts[index]
            index += 1
        elif index < len(texts) and DATE_RE.fullmatch(texts[index]):
            card = texts[index]
            index += 1
        if index < len(texts) and re.fullmatch(r"[A-Z]{2}", texts[index]):
            index += 1
        if index < len(texts) and AMOUNT_RE.fullmatch(texts[index].replace("¥", "").strip()):
            index += 1
        txns.append(
            {
                "sold": mmdd(sold),
                "posted": mmdd(posted),
                "description": desc,
                "amount": amount,
                "card_last4": card,
                "section": section or "",
            }
        )
    return txns, problems
