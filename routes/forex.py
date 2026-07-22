from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from db import query, execute
from auth import check_account_access
from helper import fmt_money
from services.forex import get_rates, SUPPORTED, BASE

bp = Blueprint("forex", __name__, url_prefix="/forex")


def forex_accounts():
    base = """SELECT a.account_id, a.acc_number, a.balance, c.full_name
              FROM accounts a
              JOIN customers c ON c.customer_id = a.customer_id
              WHERE a.acc_status = 'ACTIVE'"""
    if current_user.role == "CUSTOMER":
        return query(base + " AND a.customer_id = ? ORDER BY a.acc_number",(current_user.customer_id,))
    elif current_user.role == "MANAGER":
        return query(base + " AND a.branch_id = ? ORDER BY a.acc_number",(current_user.branch_id,))
    else:
        return query(base + " ORDER BY a.acc_number")


@bp.route("/convert", methods=["GET", "POST"])
@login_required
def convert():
    try:
        rates, rate_date, source = get_rates()
    except Exception as e:
        flash(f"Could not load exchange rates: {e}")
        return render_template("forex/convert.html", accounts=forex_accounts(),rates=None, supported=SUPPORTED, base=BASE, result=None)

    result = None
    if request.method == "POST":
        account_id = request.form["account_id"]
        to_currency = request.form["to_currency"]

        account = query("SELECT * FROM accounts WHERE account_id = ?", (account_id,), one=True)
        if account is None:
            flash("Account not found")
            return redirect(url_for("forex.convert"))

        check_account_access(account)          

        if to_currency not in SUPPORTED:
            flash("Unsupported currency")
            return redirect(url_for("forex.convert"))

        rate = rates[to_currency]
        pkr_rupees = account["balance"] / 100          
        converted = pkr_rupees * rate

        execute("""INSERT INTO conversion_history
                   (account_id, to_currency, from_amount, to_amount, rate, converted_by)VALUES (?, ?, ?, ?, ?, ?)""",
                (account_id, to_currency, account["balance"], converted, rate, current_user.id))

        result = {
            "acc_number": account["acc_number"], "from_amount": account["balance"],"to_currency": to_currency,"converted": converted,"rate": rate}

        

    return render_template("forex/convert.html", accounts=forex_accounts(),rates=rates, rate_date=rate_date, source=source,
                           supported=SUPPORTED, base=BASE, result=result,fmt_money=fmt_money)



@bp.route("/history")
@login_required
def history():

    base = """SELECT ch.*, a.acc_number, c.full_name
              FROM conversion_history ch
              JOIN accounts a  ON a.account_id = ch.account_id
              JOIN customers c ON c.customer_id = a.customer_id"""
    if current_user.role == "CUSTOMER":
        rows = query(base + " WHERE a.customer_id = ? ORDER BY ch.converted_at DESC",(current_user.customer_id,))
    elif current_user.role == "MANAGER":
        rows = query(base + " WHERE a.branch_id = ? ORDER BY ch.converted_at DESC", (current_user.branch_id,))
    else:
        rows = query(base + " ORDER BY ch.converted_at DESC LIMIT 200")

    return render_template("forex/history.html", rows=rows, fmt_money=fmt_money)