from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from db import query
from auth import check_account_access, role_required
from helper import fmt_money
from datetime import datetime, timedelta
import csv, io

bp = Blueprint("reports", __name__, url_prefix="/reports")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _days_ago(n):
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


def _report_accounts():
   
    base = """SELECT a.account_id, a.acc_number, a.balance, c.full_name
              FROM accounts a
              JOIN customers c ON c.customer_id = a.customer_id"""
    if current_user.role == "CUSTOMER":
        return query(base + " WHERE a.customer_id = ? ORDER BY a.acc_number",
                     (current_user.customer_id,))
    elif current_user.role == "MANAGER":
        return query(base + " WHERE a.branch_id = ? ORDER BY a.acc_number",
                     (current_user.branch_id,))
    else:
        return query(base + " ORDER BY a.acc_number")


def _csv_response(header, rows, filename):

    output = io.StringIO()              
    writer = csv.writer(output)
    writer.writerow(header)
    writer.writerows(rows)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _statement_data():
  
    account_id = request.args.get("account_id")
    from_date = request.args.get("from_date") or _days_ago(30)
    to_date = request.args.get("to_date") or _today()

    if not account_id:
        return None, from_date, to_date, 0, []

    account = query("SELECT * FROM accounts WHERE account_id = ?", (account_id,), one=True)
    if account is None:
        return None, from_date, to_date, 0, []

    check_account_access(account)      
    op = query("""SELECT balance_after FROM transactions
                  WHERE account_id = ? AND date(txn_date) < ?
                  ORDER BY txn_date DESC, txn_id DESC LIMIT 1""",
               (account_id, from_date), one=True)
    opening = op["balance_after"] if op else 0

    txns = query("""SELECT * FROM transactions
                    WHERE account_id = ? AND date(txn_date) BETWEEN ? AND ?
                    ORDER BY txn_date, txn_id""",
                 (account_id, from_date, to_date))

    return account, from_date, to_date, opening, txns


@bp.route("/statement")
@login_required                        
def statement():
    account, from_date, to_date, opening, txns = _statement_data()

    total_in = sum(t["amount"] for t in txns if t["txn_type"] in ("DEPOSIT", "TRANSFER_IN"))
    total_out = sum(t["amount"] for t in txns if t["txn_type"] in ("WITHDRAWAL", "TRANSFER_OUT"))
    closing = txns[-1]["balance_after"] if txns else opening

    return render_template("reports/statement.html",
                           accounts=_report_accounts(), account=account,
                           txns=txns, from_date=from_date, to_date=to_date,
                           opening=opening, closing=closing,
                           total_in=total_in, total_out=total_out,
                           fmt_money=fmt_money)


@bp.route("/statement/pdf")
@login_required
def statement_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    account, from_date, to_date, opening, txns = _statement_data()
    if account is None:
        flash("Select an account first")
        return redirect(url_for("reports.statement"))

    closing = txns[-1]["balance_after"] if txns else opening

    buf = io.BytesIO()       
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    el = []

    el.append(Paragraph("BankFlow Account Statement", styles["Title"]))
    el.append(Spacer(1, 8))
    el.append(Paragraph(f"<b>Account:</b> {account['acc_number']} ({account['acc_type']})", styles["Normal"]))
    el.append(Paragraph(f"<b>Period:</b> {from_date} to {to_date}", styles["Normal"]))
    el.append(Paragraph(f"<b>Opening balance:</b> {fmt_money(opening)}", styles["Normal"]))
    el.append(Paragraph(f"<b>Closing balance:</b> {fmt_money(closing)}", styles["Normal"]))
    el.append(Spacer(1, 12))

    data = [["Date", "Type", "Description", "Ref", "Amount", "Balance"]]
    for t in txns:
        data.append([t["txn_date"][:10], t["txn_type"].replace("_", " ").title(),
                     (t["txn_desc"] or "")[:32], t["ref_no"][:12],
                     fmt_money(t["amount"]), fmt_money(t["balance_after"])])
    if not txns:
        data.append(["-", "-", "No transactions in this period", "-", "-", "-"])

    table = Table(data, colWidths=[20*mm, 24*mm, 52*mm, 24*mm, 26*mm, 26*mm])
    table.setStyle(TableStyle([

        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d5c63")),   
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f8")]),
    ]))
    el.append(table)
    el.append(Spacer(1, 10))
    el.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} "
                        f"by {current_user.username}", styles["Italic"]))

    doc.build(el)
    buf.seek(0)                         

    return Response(buf.getvalue(), mimetype="application/pdf",
                    headers={"Content-Disposition":
                             f"attachment; filename=statement_{account['acc_number']}.pdf"})

def _daily_cash_data():
    from_date = request.args.get("from_date") or _days_ago(7)
    to_date = request.args.get("to_date") or _today()

    sql = """SELECT date(t.txn_date) AS day,
                    COUNT(*) AS txn_count,
                    SUM(CASE WHEN t.txn_type = 'DEPOSIT'      THEN t.amount ELSE 0 END) AS deposits,
                    SUM(CASE WHEN t.txn_type = 'WITHDRAWAL'   THEN t.amount ELSE 0 END) AS withdrawals,
                    SUM(CASE WHEN t.txn_type = 'TRANSFER_IN'  THEN t.amount ELSE 0 END) AS transfers_in,
                    SUM(CASE WHEN t.txn_type = 'TRANSFER_OUT' THEN t.amount ELSE 0 END) AS transfers_out
             FROM transactions t
             JOIN accounts a ON a.account_id = t.account_id
             WHERE date(t.txn_date) BETWEEN ? AND ?"""
    if current_user.role == "MANAGER":
        sql += " AND a.branch_id = ?"
        params = (from_date, to_date, current_user.branch_id)
    else:
        params = (from_date, to_date)
    sql += " GROUP BY date(t.txn_date) ORDER BY day DESC"

    return query(sql, params), from_date, to_date


@bp.route("/daily-cash")
@login_required
@role_required("SUPER_ADMIN", "MANAGER")      
def daily_cash():
    rows, from_date, to_date = _daily_cash_data()
    total_dep = sum(r["deposits"] for r in rows)
    total_wd = sum(r["withdrawals"] for r in rows)
    return render_template("reports/daily_cash.html", rows=rows,
                           from_date=from_date, to_date=to_date,
                           total_dep=total_dep, total_wd=total_wd,
                           fmt_money=fmt_money)


@bp.route("/daily-cash/csv")
@login_required
@role_required("SUPER_ADMIN", "MANAGER")      
def daily_cash_csv():
    rows, _, _ = _daily_cash_data()
    data = [[r["day"], r["txn_count"], fmt_money(r["deposits"]), fmt_money(r["withdrawals"]),
             fmt_money(r["transfers_in"]), fmt_money(r["transfers_out"]),
             fmt_money(r["deposits"] - r["withdrawals"])] for r in rows]
    return _csv_response(["Date", "Transactions", "Deposits", "Withdrawals",
                          "Transfers In", "Transfers Out", "Net Cash"],
                         data, "daily_cash.csv")

def _overdue_data():
    sql = """SELECT lp.installment, lp.due_date, lp.amount_due, lp.payment_status,
                    l.loan_id, l.loan_type, l.loan_amount, l.emi_amount,
                    c.full_name, c.phone, c.cnic, b.branch_name,
                    CAST(julianday('now') - julianday(lp.due_date) AS INTEGER) AS days_overdue
             FROM loan_payments lp
             JOIN loans l     ON l.loan_id = lp.loan_id
             JOIN customers c ON c.customer_id = l.customer_id
             JOIN branches b  ON b.branch_id = l.branch_id
             WHERE lp.payment_status != 'PAID'
               AND date(lp.due_date) < date('now')"""

    if current_user.role == "MANAGER":
        sql += " AND l.branch_id = ?"
        params = (current_user.branch_id,)
    else:
        params = ()
    sql += " ORDER BY days_overdue DESC"
    return query(sql, params)


@bp.route("/overdue")
@login_required
@role_required("SUPER_ADMIN", "MANAGER")
def overdue():
    rows = _overdue_data()
    total = sum(r["amount_due"] for r in rows)
    return render_template("reports/overdue.html", rows=rows, total=total,
                           fmt_money=fmt_money)


@bp.route("/overdue/csv")
@login_required
@role_required("SUPER_ADMIN", "MANAGER")
def overdue_csv():
    rows = _overdue_data()
    data = [[r["loan_id"], r["full_name"], r["cnic"], r["phone"], r["branch_name"],
             r["loan_type"], r["installment"], r["due_date"],
             fmt_money(r["amount_due"]), r["days_overdue"]] for r in rows]
    return _csv_response(["Loan ID", "Customer", "CNIC", "Phone", "Branch", "Type",
                          "Installment", "Due Date", "Amount Due", "Days Overdue"],
                         data, "overdue_loans.csv")


def _audit_data():
    table_name = request.args.get("table_name") or ""
    from_date = request.args.get("from_date") or _days_ago(7)
    to_date = request.args.get("to_date") or _today()

    sql = """SELECT al.*, u.username
             FROM audit_log al
             LEFT JOIN users u ON u.user_id = al.changed_by
             WHERE date(al.changed_at) BETWEEN ? AND ?"""
    if table_name:
        sql += " AND al.table_name = ?"
        params = (from_date, to_date, table_name)
    else:
        params = (from_date, to_date)
    sql += " ORDER BY al.changed_at DESC LIMIT 500"    

    return query(sql, params), table_name, from_date, to_date


@bp.route("/audit")
@login_required
@role_required("SUPER_ADMIN")         
def audit():
    rows, table_name, from_date, to_date = _audit_data()
    return render_template("reports/audit.html", rows=rows, table_name=table_name,
                           from_date=from_date, to_date=to_date)


@bp.route("/audit/csv")
@login_required
@role_required("SUPER_ADMIN")
def audit_csv():
    rows, _, _, _ = _audit_data()
    data = [[r["log_id"], r["changed_at"], r["table_name"], r["log_action"],
             r["record_id"], r["old_value"] or "", r["new_value"] or "",
             r["username"] or "System (trigger)"] for r in rows]
    return _csv_response(["Log ID", "Timestamp", "Table", "Action", "Record ID",
                          "Old Value", "New Value", "Changed By"],
                         data, "audit_trail.csv")