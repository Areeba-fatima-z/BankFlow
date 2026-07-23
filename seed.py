import sqlite3
import random
from datetime import datetime,timedelta
from werkzeug.security import generate_password_hash
import config
from helper import to_paisa,calc_emi,gen_ref_no
from db import query
random.seed(42)

conn=sqlite3.connect(config.DB_PATH)
conn.row_factory=sqlite3.Row
conn.execute("PRAGMA foreign_keys =ON")


def ins(sql,params):
    return conn.execute(sql,params).lastrowid

def days_ago(n,hours=10):
    d=datetime.now()-timedelta(days=n)
    return d.replace (hour=hours ,minute =random.randint(0,59)).strftime("%Y-%m-%d %H:%M:%S")

br_main= ins("INSERT INTO branches (branch_code,branch_name,city) VALUES (?,?,?)",("BR1","Main Branch","Islamabad"))
br_lhr= ins("INSERT INTO branches (branch_code,branch_name,city) VALUES (?,?,?)",("BR2","Lahore Branch","Lahore"))

cust_data=[(br_main,"Areeba","34101-1234567-8","0340-4444444","Rachna Town, Faisalabad","bahar.imaan@gmail.com","VERIFIED"),
           (br_main,"Fatima","34101-1243597-6","0345-3333333","Madina Town, Faisalabad","f240507@cfd.nu.edu.pk","VERIFIED"),
           (br_lhr,"Hassan", "34101-1437567-9","0300-2222222","Model Town, Lahore","hassan@example.com","PENDING"),
           (br_lhr,"Ali",   "34101-1859438-7","0345-7666200","DHA Phase 5, Lahore","ali@example.com","VERIFIED"),
           (br_main,"Shahan","34101-1324657-1","0300-2345617","Faisal Town, Islamabad","f240619@cfd.nu.edu.pk","VERIFIED"),
           (br_lhr,"Ayesha","34101-7652341-4", "0300-3333776","Johar Town, Lahore","240565@cfd.nu.edu.pk","VERIFIED"),
           (br_lhr,"Hafsa","34101-1263567-2",  "0340-5555553","Lake City, Lahore","hafsa@example.com","PENDING"),
           (br_main,"Maryam","34101-1279567-8","0340-1122111","Bahria Town, Islamabad","maryam@example.com","VERIFIED"),
           (br_lhr,"Ahmed","34101-1238723-5",  "0300-1111111","Gulberg II, Lahore","ahmed@example.com","VERIFIED"),
           (br_main,"Sameer","34101-1362547-7","0300-1122232","Park View City, Islamabad","sameer@example.com","PENDING")]

cust_ids=[]
for b,name,cnic,phone,add,email,status in cust_data:
    cid = ins("""INSERT INTO customers (branch_id,full_name,cnic,phone,cust_address,reg_status,email)
                 VALUES (?,?,?,?,?,?,?)""",(b,name,cnic,phone,add,status,email))
    cust_ids.append(cid)    

u_admin=ins("""INSERT INTO users (username,password_hash,user_role,branch_id,customer_id) VALUES (?,?,?,?,?)""",
            ("Admin",generate_password_hash("admin123"),"SUPER_ADMIN",None,None))

u_mgr_main=ins("""INSERT INTO users (username,password_hash,user_role,branch_id,customer_id) VALUES (?,?,?,?,?)""",
            ("Main manager",generate_password_hash("manager1"),"MANAGER",br_main,None))

u_mgr_lhr=ins("""INSERT INTO users (username,password_hash,user_role,branch_id,customer_id) VALUES (?,?,?,?,?)""",
            ("Lahore manager",generate_password_hash("manager2"),"MANAGER",br_lhr,None))

cust_users={}
_used_usernames=set()
for (b,name,cnic,phone,add,email,status), cid in zip(cust_data, cust_ids):
    if status != "VERIFIED":
        continue          

    first = name.strip().split()[0]
    username = first
    n = 2
    while username in _used_usernames:
        username = first + str(n)
        n += 1
    _used_usernames.add(username)
    password = first + "123"

    uid = ins("INSERT INTO users (username, password_hash, user_role, customer_id) VALUES (?,?,?,?)",
              (username, generate_password_hash(password), "CUSTOMER", cid))
    cust_users[cid] = uid

acc=[(cust_ids[0],br_main,"SAVINGS","ACTIVE"),
     (cust_ids[1],br_main,"CURRENT","ACTIVE"),
     (cust_ids[1],br_main,"SAVINGS","ACTIVE"),
     (cust_ids[3],br_lhr,"SAVINGS","ACTIVE"),
     (cust_ids[4],br_main,"CURRENT","ACTIVE"),
     (cust_ids[5],br_lhr,"CURRENT","ACTIVE"),
     (cust_ids[7],br_main,"CURRENT","FROZEN"),
     (cust_ids[7],br_main,"SAVINGS","ACTIVE"),
     (cust_ids[8],br_lhr,"CURRENT","ACTIVE"),
     (cust_ids[8],br_lhr,"SAVINGS","FROZEN"),
     ]

acc_ids=[]
for i in range (len(acc)):
    cid,bid,atype,status = acc[i]
    if bid==br_main:
        code="BR1"
    else:
        code="BR2"
    acc_num=f"PK-{code}-{i+1:06d}"
    aid = ins("""INSERT INTO accounts (customer_id, branch_id, acc_number, acc_type, balance, acc_status, opened_at)VALUES (?,?,?,?,?,?,?)""",
              (cid, bid, acc_num, atype, 0, status, days_ago(random.randint(80,140))))
    acc_ids.append(aid)

balances = {}
for aid in acc_ids:
    balances[aid] = 0
txn_count =0

for aid in acc_ids:
    amt=to_paisa (random.choice([50000,75000,60000,55000,100000,150000,200000,120000,250000,175000,125000]))
    balances[aid]+=amt
    conn.execute("""INSERT INTO transactions (account_id,txn_type,amount,balance_after,ref_no,txn_desc,created_by,txn_date)VALUES (?,?,?,?,?,?,?,?)""",
    (aid,"DEPOSIT",amt,balances[aid],gen_ref_no(),"Opening Deposit",u_mgr_main,days_ago(random.randint(10,70))))
    txn_count+=1

for day in range (60,0,-3):
    for aid in random.sample(acc_ids,k=random.randint(1,3)):
        kind =random.choice(["DEPOSIT","WITHDRAWAL"])
        amt=to_paisa(random.choice([1000,2500,5000,6000,7500,1500,10000,15000]))
        if kind=="WITHDRAWAL":
            if balances[aid]<amt:
                continue
            balances[aid]-=amt
        else:
            balances[aid]+=amt
        conn.execute("""INSERT INTO transactions (account_id,txn_type,amount,balance_after,ref_no,txn_desc,created_by,txn_date)
                     VALUES (?,?,?,?,?,?,?,?)""",(aid,kind,amt,balances[aid],gen_ref_no(),kind.lower(),u_mgr_main,days_ago(day)))
        txn_count+=1

ref=gen_ref_no()
frm=acc_ids[0]
to=acc_ids[4]
amt=to_paisa(5000)
balances[frm]-=amt
day=days_ago(5)
conn.execute("""INSERT INTO transactions (account_id,txn_type,amount,balance_after,ref_no,related_account,txn_desc,created_by,txn_date)VALUES(?,?,?,?,?,?,?,?,?)""",
             (frm,"TRANSFER_OUT",amt,balances[frm],ref,to,"Transfer to Ali",cust_users[cust_ids[0]],day))

balances[to]+=amt

conn.execute("""INSERT INTO transactions (account_id,txn_type,amount,balance_after,ref_no,related_account,txn_desc,created_by,txn_date)VALUES(?,?,?,?,?,?,?,?,?)""",
             (to,"TRANSFER_IN",amt,balances[to],ref,frm,"Transfer from Areeba",cust_users[cust_ids[0]],day))

for aid ,bal in balances.items():
    conn.execute("UPDATE accounts SET balance = ? WHERE account_id =?",(bal,aid))

def make_loan(cid,bid,ltype,amount_rs,rate,months,status,months_ago,paid_count=0):
    amt=to_paisa(amount_rs)
    emi=calc_emi(amt,rate,months)  if status not in ("APPLIED","REJECTED")else None
    applied=days_ago(months_ago*30)
    decided=days_ago(months_ago*30-2) if status not in ("APPLIED",)else None
    by=u_mgr_main if decided else None
    lid=ins("""INSERT INTO loans (customer_id,branch_id,loan_type,loan_amount,interest_rate,tenure_month,emi_amount,loan_status,applied_at,decided_at,decided_by)VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (cid,bid,ltype,amt,rate,months,emi,status,applied,decided,by))
    if emi is None:
        return lid
    start = datetime.now()-timedelta(days=months_ago*30-5)
    for i in range(1,months+1):
        due =(start+timedelta(days=30*i)).strftime("%Y-%m-%d")
        if i <=paid_count:
            pstatus,paid,paid_at ="PAID",emi,due + " 11:00:00"
        elif due<datetime.now().strftime("%Y-%m-%d"):
            pstatus,paid,paid_at="OVERDUE",0,None
        else:
            pstatus,paid,paid_at="PENDING",0,None
        conn.execute("""INSERT INTO loan_payments(loan_id,installment,due_date,amount_due,amount_paid,paid_at,payment_status)VALUES(?,?,?,?,?,?,?)""",
                     (lid,i,due,emi,paid,paid_at,pstatus))
    return lid

make_loan(cust_ids[0],br_main,"PERSONAL",100000,12.0,12,"ACTIVE",5, paid_count=4)
make_loan(cust_ids[1],br_main,"CAR",800000,14.5,36,"ACTIVE", 6, paid_count=3)
make_loan(cust_ids[2],br_main,"HOME",2500000,10.0,60,"ACTIVE", 4, paid_count=4)
make_loan(cust_ids[3],br_lhr,"BUSINESS",500000,15.0,24,"ACTIVE",1, paid_count=0)
make_loan(cust_ids[4],br_lhr,"PERSONAL",50000,0.0,12,"APPLIED",0)
make_loan(cust_ids[3],br_lhr,"CAR",600000,14.0,24,"REJECTED",2)

conn.commit()
conn.close()