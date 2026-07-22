from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from db import query, execute
from auth import role_required, check_account_access
from helper import fmt_money
from services.email import notify_account_created

bp=Blueprint("accounts",__name__,url_prefix="/accounts")

@bp.route("/")
@login_required
def list_accounts():
    role = current_user.role
 
    if role == "SUPER_ADMIN":
        rows=query("""SELECT a.*,c.full_name,b.branch_name FROM accounts a
              JOIN customers c ON a.customer_id=c.customer_id
              JOIN branches b on b.branch_id =a.branch_id
              ORDER BY a.opened_at DESC""")
 
    elif role == "MANAGER":
        rows = query("""SELECT a.*,c.full_name FROM accounts a
              JOIN customers c ON a.customer_id=c.customer_id
              WHERE a.branch_id=?
              ORDER BY a.opened_at DESC""", ( current_user.branch_id ,))
 
    else:  
        rows = query("""SELECT a.* ,c.full_name FROM accounts a
                     JOIN customers c ON a.customer_id = c.customer_id
                     WHERE a.customer_id = ?""", (current_user.customer_id,))
 
    return render_template("accounts/list.html", accounts=rows, fmt_money=fmt_money)

@bp.route("/open", methods=["GET", "POST"])
@login_required
@role_required("SUPER_ADMIN", "MANAGER")    
def open_account():
    if request.method == "POST":
        customer_id = request.form["customer_id"]
        acc_type    = request.form["acc_type"]
 
        if current_user.role == "MANAGER":
            branch_id = current_user.branch_id
        else:
            branch_id = request.form["branch_id"]
        branch = query("SELECT branch_code FROM branches WHERE branch_id = ?", (branch_id,), one=True)
        code = branch["branch_code"]
        n = query("SELECT count(*) as n from accounts ", one=True)["n"]
        acc_num = f"PK-{code}-{n+1:06d}"
       
        try:
          customer = query("SELECT full_name, email FROM customers WHERE customer_id = ?",
                     (customer_id,), one=True)

          execute(""" INSERT INTO accounts (customer_id,branch_id,acc_number,acc_type,balance) VALUES (?,?,?,?,?) """,
            (customer_id, branch_id, acc_num, acc_type, 0))

   
          notify_account_created(customer["email"], customer["full_name"], acc_num, acc_type)

          flash("Account opened. Enjoy your journey with BankFlow (^-^)", "success")
          return redirect(url_for("accounts.list_accounts"))
        except Exception:
          flash(f"Couldn't open the account. Something's definitely off.", "danger")
 
    if current_user.role == "MANAGER":
        customers = query(""" SELECT * FROM customers
                              WHERE reg_status = 'VERIFIED' AND branch_id = ? """,
                          ( current_user.branch_id ,))
        branches = []
    else:
        customers = query(" SELECT * FROM customers WHERE reg_status = 'VERIFIED' ")
        branches = query(" SELECT * FROM branches ")
 
    return render_template("accounts/form.html", customers=customers, branches=branches)

@bp.route("/<int:acc_id>/freeze", methods=["POST"])
@login_required
@role_required("SUPER_ADMIN", "MANAGER")
def freeze_account(acc_id):
    account = query(" SELECT * FROM accounts WHERE account_id = ? ", ( acc_id ,), one=True)
    if account is None:
        flash("404: Account not found. You sure it exists?","danger")
        return redirect(url_for("accounts.list_accounts"))
 
    check_account_access(account)
 
    if account["acc_status"] == "ACTIVE":
        new_status = "FROZEN"
    elif account["acc_status"] == "FROZEN":
        new_status = "ACTIVE"
    else:
        flash("Too late.... This account is already closed. No take-backs.","danger")
        return redirect(url_for("accounts.list_accounts"))
 
    execute("UPDATE accounts SET acc_status = ? WHERE account_id=?", (new_status, acc_id))
 
    flash(f"Account is now {new_status} ")
    return redirect(url_for("accounts.list_accounts"))
 
@bp.route("/<int:acc_id>/close", methods=["POST"])
@login_required
@role_required("SUPER_ADMIN", "MANAGER")
def close_account(acc_id):
    account = query("SELECT * FROM accounts WHERE account_id = ?", (acc_id,), one=True)
    if account is None:
        flash("404: Account not found. You sure it exists?","danger")
        return redirect(url_for("accounts.list_accounts"))

    check_account_access(account)

    if account["acc_status"] == "CLOSED":
        flash("Account is already closed")
        return redirect(url_for("accounts.list_accounts"))

    if account["balance"] != 0:
        flash(f"Can't close the account. There's still {fmt_money(account['balance'])} in it. You really gonna leave that behind?","danger")
        return redirect(url_for("accounts.list_accounts"))

    execute("UPDATE accounts SET acc_status = 'CLOSED' WHERE account_id = ?", (acc_id,))
    flash("Account closed. Hope you won't miss it.","warning")
    return redirect(url_for("accounts.list_accounts"))