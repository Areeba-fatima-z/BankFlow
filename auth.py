from flask import Blueprint, render_template,request,redirect,url_for,flash,abort
from flask_login import LoginManager , UserMixin , login_user , logout_user , login_required , current_user
from werkzeug.security import check_password_hash
from functools import wraps
from db import query 


login_manager=LoginManager()


class User(UserMixin):
    def __init__ (self,row):
        self.id =row["user_id"]
        self.username=row["username"]
        self.role=row["user_role"]
        self.branch_id=row["branch_id"]
        self.customer_id=row["customer_id"]

@login_manager.user_loader
def load_user(user_id):
    row=query("SELECT * FROM users WHERE user_id=?",(user_id,),one=True)
    return User(row) if row else None


bp=Blueprint("auth",__name__)

@bp.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        username=request.form["username"]
        password=request.form["password"]
        row =query("SELECT * FROM users WHERE username=?",(username,),one=True)
        if row and check_password_hash(row["password_hash"],password):
            login_user(User(row))
            return redirect(url_for("dashboard"))
        
        flash("Wrong Username or Password :( ","danger")

    return render_template("login.html")

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


def role_required(*roles):
    def decorater(f):
        @wraps(f)
        def wrapper (*args,**kwargs):
            if current_user.role not in roles:
                abort(403)
            return f(*args,**kwargs)
        return wrapper
    return decorater


def check_account_access(account):
    if current_user.role=="SUPER_ADMIN":
        return
    if current_user.role=="MANAGER":
        if account["branch_id"]!=current_user.branch_id:
            abort(403)
    elif current_user.role =="CUSTOMER":
        if account["customer_id"]!=current_user.customer_id:
            abort(403)


