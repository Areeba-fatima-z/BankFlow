BANK_NAME = "BankFlow"
SECRET_KEY= "bank-flow-dev-key"
DB_PATH = "bankflow.db"

from dotenv import load_dotenv
import os

load_dotenv()  

#Email variables 
SMTP_EMAIL = os.environ.get("SMTP_EMAIL")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
LARGE_TXN_THRESHOLD = 20000000 

#fraud detection variables
EXCESSIVE_WITHDRAWALS=3
EXCESSIVE_WITHDRAWALS_TIME = 10
DAILY_LIMIT = 50000000    # IN PAISA RS 500,000
TRANSFER_THRESHOLD = 20000000 # IN PAISA RS.200,000

#interest rate on savings account
SAVING_INTEREST_RATE =5.0 #per annum



