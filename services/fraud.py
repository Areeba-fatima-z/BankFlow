from db import query ,execute
from helper import fmt_money
import config

def log_fraud(account_id,rule,amount,details):
    try:
        execute ("""INSERT INTO fraud_log (account_id,rule_triggered,amount,details)
        VALUES(?,?,?,?)""",(account_id,rule,amount,details))

    except Exception as e:
        print(f"[FRAUD LOG FAILED] {e}")


def check_overdraft_attempt (account ,amount):
    details = f"Attempted to move {fmt_money(amount)} against balance {fmt_money(account['balance'])} on {account['acc_number']}"
    log_fraud (account['account_id'],'OVERDRAFT_ATTEMPT',amount,details)


def check_excessive_withdrawals(account_id):
    row = query (f"""SELECT COUNT(*) AS n from transactions
    WHERE account_id = ? and txn_type = 'WITHDRAWAL' and txn_date >= datetime('now','-{config.EXCESSIVE_WITHDRAWALS_TIME} minutes')""",(account_id ,),one =True)


    if row['n'] >= config.EXCESSIVE_WITHDRAWALS:
        details=f"{row['n']}  withdrawals within {config.EXCESSIVE_WITHDRAWALS_TIME} minutes"
        log_fraud (account_id , "EXCESSIVE_WITHDRAWALS",None ,details)


def check_daily_limit(account_id,acc_number):

    row = query("""SELECT COALESCE(SUM (amount),0)AS total FROM transactions
    WHERE account_id = ? AND txn_type IN ('WITHDRAWAL','TRANSFER_OUT') AND date(txn_date) = date ('now')""",(account_id,),one=True)

    if row["total"]>config.DAILY_LIMIT:
        details = f"Cumulative today : {fmt_money(row['total'])} on{acc_number},  Exceeds daily limit {fmt_money(config.DAILY_LIMIT)}"

        log_fraud(account_id , 'DAILY_LIMIT_EXCEEDED',row['total'],details)


def check_large_transfer(account_id ,amount,acc_number):

    if amount > config.TRANSFER_THRESHOLD :
        details = f"Transfer of {fmt_money(amount)} from {acc_number}  exceedes {fmt_money(config.TRANSFER_THRESHOLD)}"

        log_fraud (account_id , 'LARGE_TRANSFER', amount , details)

