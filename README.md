BankFlow  Banking & Financial Management System

BankFlow is a role-based banking and financial management system built with Flask and SQLite. It handles the core operations of a small bank customer onboarding, account management, transactions, loans with EMI schedules, and a full audit trail — with three levels of access control and exportable reports (PDF & CSV).

Built as an internship project with a focus on clean, hand-written SQL (no ORM), atomic transactions, and permanent, audit-friendly records.

Features
Role-based access control — three roles (Super Admin, Bank Manager, Customer), each seeing only what they're permitted to.
Customer management — add customers with input validation (name / phone / CNIC format), list, and verify KYC.
Account management — open, freeze, and close accounts. No deletes — records are permanent, and closing requires a zero balance.
Transactions — deposits, withdrawals, and account-to-account transfers. Transfers are atomic: if any step fails, the whole operation rolls back.
Loans — apply, approve (with an auto-generated EMI schedule), pay, and reject. Loans auto-close on the final EMI.
Reports & exports — account statements (on-screen + PDF), daily cash summary, overdue loans, and an audit trail, with CSV export.
Audit log — sensitive changes are recorded and viewable by Super Admin only.
Tech Stack
Layer	Technology
Backend	Python, Flask
Auth	Flask-Login (@login_required, current_user)
Database	SQLite (raw SQL, no ORM)
Templating	Jinja2
Frontend	Bootstrap 5 (via CDN), custom teal/gold theme with CSS variables
PDF export	ReportLab
CSV export	Python csv module
User Roles
Role	Access
Super Admin	Full access — all branches, all customers, all reports, and the audit trail.
Bank Manager	Scoped to their own branch — branch accounts, transactions, daily cash, and overdue loans.
Customer	Scoped to their own accounts and statements only.

Access is enforced at the route level with @login_required and a @role_required(...) decorator, and reinforced inside SQL queries via role-based WHERE clauses.

Modules
Customer — onboarding, listing, KYC verification.
Account — open / freeze / close, linked to customers and branches.
Transaction — deposit, withdraw, transfer (atomic with rollback).
Loan — apply, approve, EMI schedule, pay, reject, auto-close.
Audit Log — change history for accountability.
Reports
Report	On-screen	PDF	CSV
Account Statement	✅	✅	—
Daily Cash Summary	✅	—	✅
Overdue Loans	✅	—	✅
Audit Trail	✅	—	✅
Project Structure
bankflow/
├── app.py              # Application entry point
├── config.py           # Configuration
├── db.py               # SQLite connection + query(sql, params) helper
├── helpers.py          # Shared utilities (formatting, access checks, dates)
├── schema.sql          # Database schema
├── blueprints/         # Route blueprints (auth, customers, accounts,
│                       #   transactions, loans, reports)
├── templates/          # Jinja templates (base.html layout, login.html, ...)
└── static/             # CSS and assets

Structure may vary slightly depending on how blueprints and templates are organized.

Getting Started
Prerequisites
Python 3.8+
pip
Installation
Clone the repository
bash
   git clone https://github.com/Areeba-fatima-z/bankflow.git
   cd bankflow
(Recommended) Create and activate a virtual environment
bash
   python -m venv venv
   source venv/bin/activate        # On Windows: venv\Scripts\activate
Install dependencies
bash
   pip install -r requirements.txt

If you don't have a requirements.txt yet, install the core packages directly:

bash
   pip install flask flask-login reportlab
Initialize the database
bash
   sqlite3 bankflow.db < schema.sql
Run the application
bash
   flask run

Then open http://127.0.0.1:5000 in your browser.

Design Decisions
Raw SQL, no ORM — queries are written by hand for full control and clarity, using parameterized queries (? placeholders) to prevent SQL injection.
No deletes for customers or accounts — banking records are kept permanently. Accounts can only be closed, and only when the balance is zero.
Atomic transfers — money movement uses a transaction with rollback, so a partial transfer can never leave the books unbalanced.
Defense in depth — access is checked both at the route (decorators) and in the data layer (role-scoped SQL).
Roadmap
 BEFORE INSERT trigger to block accounts for non-VERIFIED customers (currently enforced in Python only).
Author

Areeba Fatima — @Areeba-fatima-z Built during a web development internship.

License

This project is for educational and internship purposes.
