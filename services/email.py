import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config

LARGE_TXN_THRESHOLD = config.LARGE_TXN_THRESHOLD  


def send_email(to_email, subject, body):
    
    if not to_email:
        print(f"[EMAIL SKIPPED] No email on file Subject: {subject}")
        return False

    if not config.SMTP_EMAIL or not config.SMTP_PASSWORD:

        print(f"[EMAIL - no SMTP configured] To: {to_email} | Subject: {subject}\n{body}\n")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = config.SMTP_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as server:
            server.starttls()                                  
            server.login(config.SMTP_EMAIL, config.SMTP_PASSWORD)
            server.send_message(msg)

        print(f"[EMAIL SENT] To: {to_email} | Subject: {subject}")
        return True

    except Exception as e:
       
        print(f"[EMAIL FAILED - fallback log] To: {to_email} | Subject: {subject}\n{body}\nError: {e}\n")
        return False


def notify_account_created(customer_email, customer_name, acc_number, acc_type):
    subject = "BankFlow : New Account Opened"
    body = (f"Dear {customer_name},\n\n"
            f"Your new {acc_type} account has been opened successfully.\n"
            f"Account Number: {acc_number}\n\n"
            f"Thank you for banking with BankFlow.")
    send_email(customer_email, subject, body)


def notify_transaction(customer_email, customer_name, txn_type, amount_paise,
                       balance_after_paise, acc_number):
    amount_rs = amount_paise / 100
    balance_rs = balance_after_paise / 100

    subject = f"BankFlow : {txn_type.title()} Confirmation"
    body = (f"Dear {customer_name},\n\n"
            f"A {txn_type.lower()} of Rs. {amount_rs:,.2f} was made on account {acc_number}.\n"
            f"Available balance: Rs. {balance_rs:,.2f}\n\n"
            f"If you did not authorize this transaction, please contact your branch immediately.")
    send_email(customer_email, subject, body)


    if amount_paise > LARGE_TXN_THRESHOLD:
        alert_subject = "BankFlow : Large Transaction Alert"
        alert_body = (f"Dear {customer_name},\n\n"
                      f"A large transaction of Rs. {amount_rs:,.2f} was detected on account "
                      f"{acc_number}.\n\nIf this wasn't you, contact your branch immediately.")
        send_email(customer_email, alert_subject, alert_body)