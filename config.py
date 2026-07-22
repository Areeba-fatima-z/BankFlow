BANK_NAME = "BankFlow"
SECRET_KEY= "bank-flow-dev-key"
DB_PATH = "bankflow.db"

from dotenv import load_dotenv
import os

load_dotenv()  

SMTP_EMAIL = os.environ.get("SMTP_EMAIL")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
LARGE_TXN_THRESHOLD = 5000000 
