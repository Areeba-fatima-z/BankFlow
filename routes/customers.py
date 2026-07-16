from flask import Blueprint,render_template,request,redirect,url_for,flash
from flask_login import login_required ,current_user
from db import query,execute
from auth import role_required


bp=Blueprint("customers",__name__,url_prefix="/customers")

@bp.route("/")
@login_required
@role_required("SUPER_ADMIN","MANAGER")
def list_customers():
    if current_user.role =="MANAGER":
        rows = query("""SELECT c.* , b.branch_name FROM customers c
                     JOIN branches b ON b.branch_id =c.branch_id
                     WHERE c.branch_id=?
                     ORDER BY c.created_at DESC""",
                     (current_user.branch_id,))
        

    else:
        rows = query("""SELECT c.* ,b.branch_name FROM customers c
                     JOIN branches b ON b.branch_id =c.branch_id
                     ORDER BY c.created_at DESC""")
    return render_template("customers/list.html",customers=rows)

@bp.route("/add",methods=["GET","POST"])
@login_required
@role_required("SUPER_ADMIN","MANAGER")
def add_customer():
    if request.method=="POST":
        full_name=request.form["full_name"].strip()
        cnic=request.form["cnic"].strip()
        phone=request.form["phone"].strip()
        address=request.form["address"].strip()
        if not all(s.isalpha() or s.isspace() for s in full_name):
            flash("Type a real name","danger")
            return redirect(url_for("customers.add_customer"))
        if len(phone) != 12 or phone[4]!='-':
            flash("A real 11-digit phone number would be appreciated with hyphen(-) after 4 digits    :)   ","danger")
            return redirect(url_for("customers.add_customer"))
        if len(cnic) != 15:
            flash("CNIC should be 13 digits, use hyphens(-) like the real formate. Don't freestyle it","danger")
            return redirect(url_for("customers.add_customer"))
        if cnic[5] != '-' or cnic[13] != '-':
            flash("Where are the hyphens(-) in cnic. The format exists for a reason.","danger")
            return redirect(url_for("customers.add_customer"))
        if current_user.role=="MANAGER":
            branch_id = current_user.branch_id
        else:
            branch_id = request.form["branch_id"]
        

        try:
            execute("""INSERT INTO customers (branch_id,full_name,cnic,phone,cust_address) VALUES (?,?,?,?,?)""",
                     (branch_id,full_name,cnic,phone,address))
            flash("Customer Added (^-^) -- Status is Pending until customer is verified","success")
            return redirect(url_for("customers.list_customers"))
        
        except Exception as e:
            flash(f"Couldn't add the customer. Those don't look like your details.","danger")
            
    branches=[]
    if current_user.role=="SUPER_ADMIN":
        branches=query("SELECT * FROM branches")

    return render_template("customers/form.html",branches=branches)
    

@bp.route("/<int:cid>/verify",methods=["POST"])
@login_required
@role_required("SUPER_ADMIN","MANAGER")
def verify_customer(cid):

    new_status=request.form["status"]
    customer=query("SELECT * FROM customers WHERE customer_id =?",(cid,),one=True)

    if customer is None:
        flash("Customer not Found :( ")
        return redirect(url_for("customers.list_customers"))  

    if current_user.role=="MANAGER" and customer["branch_id"] !=current_user.branch_id:
        flash("Can't see data of another branch :( ","danger") 
        return redirect(url_for("customers.list_customers"))
    
    execute("UPDATE customers SET reg_status = ? WHERE customer_id =?",(new_status,cid))

    flash(f"Customer Marked {new_status} (^-^)","success")
    return redirect(url_for("customers.list_customers"))

