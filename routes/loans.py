from flask import Blueprint,render_template,request,redirect,url_for,flash,abort
from flask_login import login_required,current_user
from db import query,execute,get_db
from auth import role_required , check_account_access
from helper import calc_emi ,to_paisa ,fmt_money ,gen_ref_no
from datetime import datetime , timedelta

bp = Blueprint("loans",__name__,url_prefix='/loans')

def _check_loan_access(loan):
    if current_user.role == "SUPER_ADMIN":
        return
    if current_user.role == "MANAGER" and loan["branch_id"] != current_user.branch_id:
        abort(403)
    if current_user.role == "CUSTOMER" and loan["customer_id"] != current_user.customer_id:
        abort(403)

@bp.route("/apply",methods=["GET","POST"])
@login_required
@role_required("CUSTOMER")
def apply_loans():
    if request.method=='POST':
        loan_type= request.form["loan_type"]
        amt_rs=request.form["amount"]
        tenure_month=int(request.form["tenure_month"])

        if loan_type =="PERSONAL":
            interest_rate=12.0
        elif loan_type=="CAR":
            interest_rate=14.5
        elif loan_type=="HOME":
            interest_rate=10.0
        else:  # business
            interest_rate=15.0

        amount=to_paisa(amt_rs)
        
        if amount<=0:
            flash("Amount must be atleast 0.01","danger")
            return redirect(url_for("loans.apply_loans"))
        if tenure_month <=0:
            flash("Tenure Month should be atleast 1")
            return redirect(url_for("loans.apply_loans"))
        
        branch = query("SELECT branch_id from customers where customer_id =?",(current_user.customer_id,),one=True)
        branch_id =branch["branch_id"]

        rows=execute("""INSERT INTO loans (customer_id,branch_id,loan_type,loan_amount,interest_rate,tenure_month) VALUES (?,?,?,?,?,?)""",
                   (current_user.customer_id,branch_id,loan_type,amount,interest_rate,tenure_month))
        flash("Application Submitted (^-^)","success")
        return redirect(url_for("loans.list_loans"))
      

    else:
        return render_template("loans/apply.html")
    
@bp.route("/",methods=["GET"])
@login_required
def list_loans():
    if current_user.role=="SUPER_ADMIN":
        rows=query("""SELECT l.* , c.full_name from loans l
                   JOIN customers c ON c.customer_id = l.customer_id 
                   ORDER BY l.applied_at DESC """)
        
    elif current_user.role=="MANAGER":
        rows=query("""SELECT l.*,c.full_name from loans l 
                   JOIN customers c ON c.customer_id = l.customer_id 
                   WHERE l.branch_id = ?""",(current_user.branch_id,))
    else:
        rows=query("""SELECT l.* ,c.full_name from loans l
                   JOIN customers c ON c.customer_id=l.customer_id
                   where l.customer_id =?""",(current_user.customer_id,))
        

    return render_template("loans/list.html", loans=rows, fmt_money=fmt_money)

@bp.route("/<int:loan_id>",methods=["GET"])
@login_required
def loan_detail(loan_id):
    loan=query("""SELECT l.* ,c.full_name FROM loans l
               JOIN customers c ON c.customer_id=l.customer_id
               WHERE l.loan_id=?""",(loan_id,),one=True)
    
    if loan is None :
        flash("No loan exists with this id :(" ,"danger")
        return redirect(url_for("loans.list_loans"))
    
    if current_user.role=="MANAGER" and loan["branch_id"]!=current_user.branch_id:
        flash("You are not allowed to see others branch loans details","danger")
        return redirect(url_for("loans.list_loans"))
    elif current_user.role=="CUSTOMER" and loan["customer_id"]!=current_user.customer_id:
        flash("You are not allowed to see others loan details","danger")
        return redirect(url_for("loans.list_loans"))
    
    emi=query("""SELECT * from loan_payments WHERE loan_id =? 
              ORDER BY installment""",(loan_id,))
    
    if loan["loan_status"] == "ACTIVE":
        pay_accounts = query("""SELECT account_id, acc_number, balance FROM accounts
                                WHERE customer_id = ? AND acc_status = 'ACTIVE'
                                ORDER BY acc_number""", (loan["customer_id"],))
    else:
        pay_accounts = []
    return render_template("loans/detail.html",loan=loan,payments=emi,pay_accounts=pay_accounts,fmt_money=fmt_money)

@bp.route("/<int:loan_id>/approve",methods =["POST"])
@login_required
@role_required("SUPER_ADMIN","MANAGER")
def approve_loan(loan_id):
      loan =query("""SELECT * from loans where loan_id=?""",(loan_id,),one=True)
    
      if loan is None :
        flash("No loan exists with this id :(" ,"danger")
        return redirect(url_for("loans.list_loans"))
      if current_user.role=="MANAGER" and loan["branch_id"]!=current_user.branch_id:
        flash("You are not allowed to see others branch loans details","danger")
        return redirect(url_for("loans.list_loans"))
    

      if loan["loan_status"] !='APPLIED':
          flash(f"Loan already {loan['loan_status']}")
          return redirect(url_for("loans.list_loans",loan_id=loan_id))
      
      emi = calc_emi(loan["loan_amount"],loan["interest_rate"],loan["tenure_month"])

      conn=get_db()

      try:
          conn.execute("""Update loans set emi_amount =? ,loan_status='ACTIVE',
                       decided_at=datetime('now'),decided_by=?
                       WHERE loan_id=?""",(emi,current_user.id,loan_id))
          
          for i in range (1,int(loan["tenure_month"]+1)):
              
              due_date=(datetime.now()+timedelta(days=30*i)).strftime("%Y-%m-%d")

              conn.execute("INSERT INTO loan_payments (loan_id,installment,due_date,amount_due) Values(?,?,?,?)",(loan_id,i,due_date,emi))
              
          conn.commit()

          flash(f"Loan approved : EMI {fmt_money(emi)} x {loan['tenure_month']} months")

      except Exception as e:
          conn.rollback()
          flash(f"Approval failed,nothing changed: {e}")


      return redirect(url_for("loans.loan_detail",loan_id=loan_id))


@bp.route("/<int:loan_id>/reject",methods=["POST"])
@login_required
@role_required("SUPER_ADMIN","MANAGER")
def reject_loan(loan_id):
    loan=query("""SELECT *from loans WHERE loan_id =?""",(loan_id,),one=True)

    if loan is None :
        flash("No loan exists with this id :(" ,"danger")
        return redirect(url_for("loans.list_loans"))
    if current_user.role=="MANAGER" and loan["branch_id"]!=current_user.branch_id:

        flash("You are not allowed to see others branch loans details","danger")
        return redirect(url_for("loans.list_loans"))
    

    if loan["loan_status"] !='APPLIED':
          flash(f"Loan already {loan['loan_status']}")
          return redirect(url_for("loans.list_loans",loan_id=loan_id))
    
    execute("""UPDATE loans SET loan_status = 'REJECTED',decided_at=datetime('now'),decided_by=?
            WHERE loan_id=?""",(current_user.id,loan_id))
    flash("Loan Rejected :(","info")

    return redirect(url_for("loans.list_loans"))


@bp.route("/<int:loan_id>/pay/<int:payment_id>", methods=["POST"])
@login_required

def pay_installment(loan_id, payment_id):
    account_id = request.form["account_id"]

    payment = query("""SELECT * FROM loan_payments
                       WHERE payment_id = ? AND loan_id = ?""",
                    (payment_id, loan_id), one=True)
    if payment is None:
        flash("Installment not found")
        return redirect(url_for("loans.list_loans"))

    loan = query("SELECT * FROM loans WHERE loan_id = ?", (loan_id,), one=True)
    if loan is None:
        flash("Loan not found")
        return redirect(url_for("loans.list_loans"))

    _check_loan_access(loan)

    if payment["payment_status"] == "PAID":
        flash("This installment is already paid")
        return redirect(url_for("loans.loan_detail", loan_id=loan_id))

    if loan["loan_status"] != "ACTIVE":
        flash(f"Loan is {loan['loan_status']} — cannot pay")
        return redirect(url_for("loans.loan_detail", loan_id=loan_id))

    account = query("SELECT * FROM accounts WHERE account_id = ?", (account_id,), one=True)
    if account is None:
        flash("Account not found")
        return redirect(url_for("loans.loan_detail", loan_id=loan_id))

    check_account_access(account)         

    if account["acc_status"] != "ACTIVE":
        flash("Account is not active")
        return redirect(url_for("loans.loan_detail", loan_id=loan_id))

    amount = payment["amount_due"]
    if account["balance"] < amount:
        flash(f"Insufficient balance — need {fmt_money(amount)}")
        return redirect(url_for("loans.loan_detail", loan_id=loan_id))

    conn = get_db()
    ref = gen_ref_no()
    try:
        new_balance = account["balance"] - amount

        conn.execute("UPDATE accounts SET balance = ? WHERE account_id = ?",
                     (new_balance, account_id))
        conn.execute("""INSERT INTO transactions
                        (account_id, txn_type, amount, balance_after, ref_no,
                         txn_desc, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                     (account_id, "WITHDRAWAL", amount, new_balance, ref,
                      f"EMI payment - Loan #{loan_id} installment {payment['installment']}",
                      current_user.id))

        conn.execute("""UPDATE loan_payments
                        SET amount_paid = ?, paid_at = datetime('now'),
                            payment_status = 'PAID'
                        WHERE payment_id = ?""",
                     (amount, payment_id))

        remaining = conn.execute("""SELECT COUNT(*) FROM loan_payments
                                    WHERE loan_id = ? AND payment_status != 'PAID'""",
                                 (loan_id,)).fetchone()[0]
        if remaining == 0:
            conn.execute("UPDATE loans SET loan_status = 'CLOSED' WHERE loan_id = ?",
                         (loan_id,))

        conn.commit()         
        if remaining == 0:
            flash(f"EMI {fmt_money(amount)} paid loan fully repaid and closed! (^-^) ","success")
        else:
            flash(f"EMI {fmt_money(amount)} paid  {remaining} installments remaining","success")
    except Exception as e:
        conn.rollback()       
        flash(f"Payment failed, nothing changed: {e}")

    return redirect(url_for("loans.loan_detail", loan_id=loan_id))











