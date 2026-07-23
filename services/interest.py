from db import query,get_db
from helper import fmt_money,gen_ref_no
import config 
from datetime import datetime

def run_interest_job():

    accounts = query("""SELECT * from accounts 
    WHERE acc_type ='SAVINGS' and acc_status ='ACTIVE' 
    """)
   
    period = datetime.now().strftime("%Y-%m")     
    credited = 0
    skipped = 0
    for account in accounts:

        existing = query("""SELECT interest_id from interest_history
        WHERE account_id = ? and int_period = ? """,(account['account_id'],period))

        if existing:
            skipped +=1 
            continue

        interest=round (account["balance"] * (config.SAVING_INTEREST_RATE / 12 /100))

        if interest <= 0:
            skipped +=1
            continue

        conn=get_db()
        new_balance=account['balance']+interest
        balance = account['balance']
        try:

            conn.execute("""UPDATE accounts SET balance = ? 
            WHERE account_id = ? """,(new_balance,account["account_id"]))

            conn.execute ("""INSERT INTO transactions (account_id,txn_type,amount,balance_after,ref_no,txn_desc,created_by)
             VALUES (?,?,?,?,?,?,?) """,(account['account_id'],'DEPOSIT',interest,new_balance,gen_ref_no(),f"Interest amount {fmt_money(interest)} credited at {period}",None))

            conn.execute ("""INSERT INTO interest_history(account_id , balance_before,balance_after,rate_applied,interest_amount,int_period) 
            VALUES (?,?,?,?,?,?) """,(account['account_id'],balance,new_balance,config.SAVING_INTEREST_RATE,interest,period))

            conn.commit()
            credited+=1
        except Exception as e:
            conn.rollback()
            print(f"[INTEREST JOB FAILED] account {account['account_id']}: {e}")


    return {"period": period, "credited": credited, "skipped": skipped}


