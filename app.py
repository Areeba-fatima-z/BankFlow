#sqlite3 bankflow.db < schema.sql
#python3 seed.py
# to reset all data
from flask import Flask ,render_template,redirect,url_for
from flask_login import login_required ,current_user

import config
from db import close_db
from auth import login_manager,bp as auth_bp

app=Flask(__name__)
app.config["SECRET_KEY"]=config.SECRET_KEY


login_manager.init_app(app)
login_manager.login_view="auth.login"

app.teardown_appcontext(close_db)

app.register_blueprint(auth_bp)

from routes import customers
app.register_blueprint(customers.bp)
from routes import account
app.register_blueprint(account.bp)
from routes import transaction
app.register_blueprint(transaction.bp)
from routes import loans
app.register_blueprint(loans.bp)
from routes import reports         
app.register_blueprint(reports.bp) 
from routes import forex             
app.register_blueprint(forex.bp)

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("auth.login"))


@app.route("/dashboard")
@login_required
def dashboard():
    role=current_user.role
    if role == "SUPER_ADMIN":
        return render_template("dashboard/superadmin.html")
    elif role == "MANAGER":
        return render_template("dashboard/manager.html")
    else:
        return render_template("dashboard/customer.html")


if __name__=="__main__":
    app.run(debug=True)