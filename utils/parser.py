import re

def parse_amount(amount_str: str) -> int:
    s = amount_str.lower().replace(" ", "").replace("đ", "").replace(",", "")
    units = {"tỷ": 1000000000, "tr": 1000000, "triệu": 1000000, "k": 1000}
    for unit, multiplier in units.items():
        if unit in s:
            try:
                return int(float(s.replace(unit, "")) * multiplier)
            except: continue
    s = s.replace(".", "")
    try: return int(float(s))
    except: return 0

def format_currency(amount: int) -> str:
    return "{:,.0f}đ".format(amount).replace(",", ".")

def extract_debt_command(text: str):
    usernames = re.findall(r"@(\w+)", text)
    if not usernames: return None
    pattern_amount = r"([+-])\s*(\d+(?:[.,]\d+)?(?:k|tr|đ|tỷ|triệu|ty|t)?)"
    match_amount = re.search(pattern_amount, text, re.IGNORECASE)
    if match_amount:
        type_sign = match_amount.group(1)
        amount_raw = match_amount.group(2)
        reason = text[match_amount.end():].strip()
        for u in usernames: reason = reason.replace(f"@{u}", "").strip()
        if not reason: reason = "Không có lý do"
        amount = parse_amount(amount_raw)
        if amount > 0: return usernames, amount, reason, type_sign
    return None
