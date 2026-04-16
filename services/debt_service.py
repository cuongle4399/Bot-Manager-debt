from database.db_manager import get_debts_in_group
from collections import defaultdict

def calculate_group_debts(group_id):
    transactions = get_debts_in_group(group_id)
    pair_debts = defaultdict(int)
    user_names = {}
    for tx in transactions:
        c_id, d_id = tx['creditor_id'], tx['debtor_id']
        user_names.update({c_id: tx['creditor_name'], d_id: tx['debtor_name']})
        if c_id == d_id: continue
        ids = sorted([c_id, d_id])
        key = (ids[0], ids[1])
        if c_id == ids[0]: pair_debts[key] += tx['amount']
        else: pair_debts[key] -= tx['amount']
    return pair_debts, user_names

def get_my_debts(user_id, group_id):
    pair_debts, user_names = calculate_group_debts(group_id)
    owe_me, i_owe = [], []
    for (u1, u2), amount in pair_debts.items():
        if amount == 0: continue
        if u1 == user_id:
            if amount > 0: owe_me.append({"id": u2, "name": user_names.get(u2, f"User {u2}"), "amount": amount})
            else: i_owe.append({"id": u2, "name": user_names.get(u2, f"User {u2}"), "amount": abs(amount)})
        elif u2 == user_id:
            if amount < 0: owe_me.append({"id": u1, "name": user_names.get(u1, f"User {u1}"), "amount": abs(amount)})
            else: i_owe.append({"id": u1, "name": user_names.get(u1, f"User {u1}"), "amount": amount})
    return owe_me, i_owe
