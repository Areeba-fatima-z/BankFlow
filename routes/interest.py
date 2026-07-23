from flask import Blueprint , render_template,redirect,url_for,flash
from flask_login import login_required,current_user
from db import query
from auth import role_required
from helper import fmt_money
from services.interest import run_interest_job


bp=Blueprint("interest",__name__,url_prefix="/interest")

@bp.route("/run",methods=["POST"])
@login_required
@role_required("SUPER_ADMIN")
def run_now():
    result = run_interest_job()
    flash (f"Interest job ({result['period']}) : {result['credited']}:credited, {result['skipped']} already done","success")
    return redirect(url_for("interest.history"))



@bp.route("/history")
@login_required
def history():
    base = """SELECT ih.* , a.acc_number , c.full_name
    from interest_history ih 
    JOIN accounts a ON a.account_id = ih.account_id
    JOIN customers c ON c.customer_id = a.customer_id"""

    if current_user.role == "CUSTOMER":
        rows =query(base+" WHERE a.customer_id = ? ORDER BY ih.calculated_at DESC",
                    (current_user.customer_id,))

    elif current_user.role =="MANAGER":
        rows=query(base + " WHERE a.branch_id = ? ORDER BY ih.calculated_at DESC",
                   (current_user.branch_id,))

    else:
        rows = query (base + " ORDER BY ih.calculated_at DESC")


    return render_template("interest/history.html",rows=rows,fmt_money=fmt_money)

