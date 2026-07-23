from flask import Blueprint , render_template ,jsonify
from flask_login import login_required ,current_user
from db import query 
from auth import role_required

bp = Blueprint("fraud",__name__,url_prefix="/fraud")

def fraud_rows():
    base = """SELECT f.* ,a.acc_number,c.full_name
    from fraud_log f JOIN accounts a ON a.account_id =f.account_id
    JOIN customers c ON c.customer_id = a.customer_id"""

    if current_user.role == "MANAGER":
        return query(base + " WHERE a.branch_id = ? ORDER BY f.detected_at desc",(current_user.branch_id,))
    else :
        return query(base + " ORDER BY f.detected_at DESC LIMIT 500")



@bp.route ("/reports")
@login_required
@role_required("SUPER_ADMIN","MANAGER")

def reports():
    rows = fraud_rows()
    return render_template("fraud/reports.html",rows=rows)

@bp.route("/reports/api")
@login_required
@role_required("SUPER_ADMIN","MANAGER")

def reports_api():
    rows =fraud_rows()
    data=[dict(r) for r in rows]
    return jsonify(data)

