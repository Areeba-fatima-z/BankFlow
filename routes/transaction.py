from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from db import query, execute, get_db
from auth import role_required, check_account_access
from helper import to_paisa, fmt_money, gen_ref_no
from services.email import notify_transaction

bp = Blueprint("transactions", __name__, url_prefix="/txn")

@bp.route("/deposit", methods=["GET", "POST"])
@login_required
@role_required("SUPER_ADMIN", "MANAGER")     
def deposit():
    if request.method == "POST":
        account_id = request.form["account_id"]
        amount_rs  = request.form["amount"]
 
        amount = to_paisa(amount_rs )

        account = query("SELECT * FROM accounts WHERE account_id =?", (account_id,), one=True)
        if account is None:
            flash("Account not found :( ")
            return redirect(url_for("transactions.deposit"))
        
        check_account_access(account) 
 
        if account["acc_status"] != "ACTIVE":
            flash("Account is not active :( ","danger")
            return redirect(url_for("transactions.deposit"))
 
        new_balance = account["balance"] + amount
        execute("UPDATE accounts SET balance =? where account_id=?", (new_balance, account_id))
        execute(""" INSERT INTO transactions (account_id,txn_type,amount,balance_after,ref_no,txn_desc,created_by) VALUES (?,?,?,?,?,?,? ) """,
                (account_id,'DEPOSIT',amount,new_balance,gen_ref_no(),"Counter Deposit",current_user.id))
        
        info = query("""SELECT c.full_name, c.email FROM accounts a
                JOIN customers c ON c.customer_id = a.customer_id
                WHERE a.account_id = ?""", (account_id,), one=True)
        notify_transaction(info["email"], info["full_name"], "DEPOSIT", amount, new_balance, account["acc_number"])

        flash(f"Deposited {fmt_money(amount)} (^-^) ","info")
        return redirect(url_for("transactions.deposit"))
 

    accounts = _accounts_for_dropdown()
    return render_template("transactions/deposit.html", accounts=accounts)

@bp.route("/withdraw", methods=["GET", "POST"])
@login_required
@role_required("SUPER_ADMIN", "MANAGER")
def withdraw():
    if request.method == "POST":
        account_id = request.form["account_id"]
        amount     = to_paisa(request.form["amount"])
 
        account = query("SELECT * FROM accounts WHERE account_id = ?", (account_id,), one=True)
        if account is None:
            flash("Account not found","danger")
            return redirect(url_for("transactions.withdraw"))
 
        check_account_access(account)
 
        if account["acc_status"] != "ACTIVE":
            flash("Account is not active","danger")
            return redirect(url_for("transactions.withdraw"))
 
        if account["balance"] < amount:
            flash("Insufficient balance :( ","danger")
            return redirect(url_for("transactions.withdraw"))
 
        new_balance = account["balance"] - amount
 
        execute("UPDATE accounts SET balance = ? WHERE account_id = ?", (new_balance, account_id))
        execute("""INSERT INTO transactions
                   (account_id, txn_type, amount, balance_after, ref_no, txn_desc, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (account_id, "WITHDRAWAL", amount, new_balance, gen_ref_no(),
                 "Counter withdrawal", current_user.id))

        info = query("""SELECT c.full_name, c.email FROM accounts a
                JOIN customers c ON c.customer_id = a.customer_id
                WHERE a.account_id = ?""", (account_id,), one=True)
        
        notify_transaction(info["email"], info["full_name"], "WITHDRAWAL", amount, new_balance, account["acc_number"])

        flash(f"Withdrew {fmt_money(amount)} (^-^)","info")
        return redirect(url_for("transactions.withdraw"))
 
    accounts = _accounts_for_dropdown()
    return render_template("transactions/withdraw.html", accounts=accounts)
 
 
def _accounts_for_dropdown():

    if current_user.role == "SUPER_ADMIN":
        return query("""SELECT a.account_id, a.acc_number, a.balance, c.full_name
                        FROM accounts a JOIN customers c ON c.customer_id = a.customer_id
                        WHERE a.acc_status = 'ACTIVE' ORDER BY a.acc_number""")
    else: 
        return query("""SELECT a.account_id, a.acc_number, a.balance, c.full_name
                        FROM accounts a JOIN customers c ON c.customer_id = a.customer_id
                        WHERE a.acc_status = 'ACTIVE' AND a.branch_id = ?
                        ORDER BY a.acc_number""", (current_user.branch_id,))
 

@bp.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    if request.method == "POST":
        from_id = request.form["from_account"]
        to_id   = request.form["to_account"]
        amount  = to_paisa(request.form["amount"])
 
        if from_id == to_id:
            flash("You cannot send money to yourself, that's not how this works :) ","danger")
            return redirect(url_for("transactions.transfer"))
 
        frm = query("SELECT * FROM accounts WHERE account_id = ?", (from_id,), one=True)
        to  = query("SELECT * FROM accounts WHERE account_id = ?", (to_id,), one=True)
 
        if frm is None or to is None:
            flash("Nah this account does not exist in this universe fr")
            return redirect(url_for("transactions.transfer"))
 

        check_account_access(frm)
 
        if frm["acc_status"] != "ACTIVE" or to["acc_status"] != "ACTIVE":
            flash("Both accounts must be active :( ","danger")
            return redirect(url_for("transactions.transfer"))
 
        if frm["balance"] < amount:
            flash("Insufficient balance. It's okay, don't be sad :( ","danger")
            return redirect(url_for("transactions.transfer"))
 
        conn = get_db()
        ref = gen_ref_no()         
        try:
            new_from = frm["balance"] - amount
            new_to   = to["balance"] + amount
 
            conn.execute("UPDATE accounts SET balance = ? WHERE account_id = ?",
                         (new_from, from_id))
            conn.execute("UPDATE accounts SET balance = ? WHERE account_id = ?",
                         (new_to, to_id))
            conn.execute("""INSERT INTO transactions
                (account_id, txn_type, amount, balance_after, ref_no, related_account, txn_desc, created_by)
                VALUES (?,?,?,?,?,?,?,?)""",
                (from_id, "TRANSFER_OUT", amount, new_from, ref, to_id,
                 f"Transfer to {to['acc_number']}", current_user.id))
            conn.execute("""INSERT INTO transactions
                (account_id, txn_type, amount, balance_after, ref_no, related_account, txn_desc, created_by)
                VALUES (?,?,?,?,?,?,?,?)""",
                (to_id, "TRANSFER_IN", amount, new_to, ref, from_id,
                 f"Transfer from {frm['acc_number']}", current_user.id))
 
            conn.commit()   


                
            flash(f"Transferred {fmt_money(amount)} successfully (^-^)","success")
        except Exception as e:
            conn.rollback() 
            flash(f"Transfer failed, Expecetd banking experience in Pakistan :) ","danger")

        try:
            info_from = query("""SELECT c.full_name, c.email FROM accounts a
                         JOIN customers c ON c.customer_id = a.customer_id
                         WHERE a.account_id = ?""", (from_id,), one=True)
            notify_transaction(info_from["email"], info_from["full_name"], "TRANSFER_OUT",
                       amount, new_from, frm["acc_number"])

            info_to = query("""SELECT c.full_name, c.email FROM accounts a
                       JOIN customers c ON c.customer_id = a.customer_id
                       WHERE a.account_id = ?""", (to_id,), one=True)
            notify_transaction(info_to["email"], info_to["full_name"], "TRANSFER_IN",
                       amount, new_to, to["acc_number"])
        except Exception:
            pass 
        return redirect(url_for("transactions.transfer"))
 
    if current_user.role == "CUSTOMER":
        from_accounts = query("""SELECT account_id, acc_number, balance FROM accounts
                                 WHERE customer_id = ? AND acc_status = 'ACTIVE'""",
                              (current_user.customer_id,))
    else:
        from_accounts = _accounts_for_dropdown()
 
    all_accounts = query("""SELECT a.account_id, a.acc_number, c.full_name
                            FROM accounts a JOIN customers c ON c.customer_id = a.customer_id
                            WHERE a.acc_status = 'ACTIVE' ORDER BY a.acc_number""")
 
    return render_template("transactions/transfer.html",
                           from_accounts=from_accounts, all_accounts=all_accounts)
 

 
 
 
