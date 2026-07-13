-----------------
-- TABLES - 8
-----------------

DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS loan_payments;
DROP TABLE IF EXISTS loans;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS branches;

CREATE TABLE branches(
    branch_id INTEGER PRIMARY KEY,
    branch_code TEXT UNIQUE NOT NULL,
    branch_name TEXT NOT NULL,
    city TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE customers(
    customer_id INTEGER PRIMARY KEY,
    branch_id INTEGER NOT NULL,
    full_name TEXT NOT NULL,
    cnic TEXT UNIQUE NOT NULL,
    phone TEXT,
    cust_address TEXT,
    reg_status TEXT NOT NULL DEFAULT 'PENDING' CHECK(reg_status IN('PENDING','VERIFIED','REJECTED')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
);

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    user_role TEXT NOT NULL CHECK (user_role IN ('SUPER_ADMIN','MANAGER','CUSTOMER')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    branch_id INTEGER,
    customer_id INTEGER,
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE accounts (
    account_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    branch_id INTEGER NOT NULL,
    acc_number TEXT UNIQUE NOT NULL,
    acc_type TEXT NOT NULL CHECK(acc_type IN('SAVINGS','CURRENT')),
    balance INTEGER NOT NULL DEFAULT 0 CHECK (balance>=0),
    acc_status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (acc_status IN ('ACTIVE','FROZEN','CLOSED')),
    opened_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE transactions (
    txn_id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,
    txn_type TEXT NOT NULL CHECK(txn_type IN('DEPOSIT','WITHDRAWAL','TRANSFER_IN','TRANSFER_OUT')),
    amount INTEGER NOT NULL CHECK(amount>0),
    balance_after INTEGER NOT NULL CHECK(balance_after>=0),
    ref_no TEXT NOT NULL,
    related_account INTEGER,
    txn_desc TEXT,
    created_by INTEGER NOT NULL,
    txn_date TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (related_account) REFERENCES accounts (account_id),
    FOREIGN KEY (created_by)  REFERENCES users(user_id)

);

CREATE TABLE loans(
    loan_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    branch_id INTEGER NOT NULL,
    loan_type TEXT NOT NULL CHECK (loan_type IN ('PERSONAL','CAR','HOME','BUSINESS')),
    loan_amount INTEGER NOT NULL CHECK(loan_amount > 0),
    interest_rate REAL NOT NULL CHECK(interest_rate >=0),
    tenure_month INTEGER NOT NULL CHECK(tenure_month >0),
    emi_amount INTEGER CHECK(emi_amount>0),
    loan_status TEXT NOT NULL DEFAULT 'APPLIED' CHECK (loan_status IN('APPLIED','APPROVED','REJECTED','ACTIVE','CLOSED','DEFAULTED')),
    applied_at TEXT NOT NULL DEFAULT (datetime('now')),
    decided_at TEXT,
    decided_by INTEGER,
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id),
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
    FOREIGN KEY (decided_by)  REFERENCES users(user_id)
);

CREATE TABLE loan_payments (
    payment_id INTEGER PRIMARY KEY,
    loan_id INTEGER NOT NULL,
    installment INTEGER NOT NULL,
    due_date TEXT NOT NULL,
    amount_due INTEGER NOT NULL CHECK(amount_due > 0),
    amount_paid INTEGER NOT NULL DEFAULT 0 CHECK(amount_paid >= 0),
    paid_at TEXT ,
    payment_status TEXT NOT NULL DEFAULT 'PENDING' CHECK(payment_status IN ('PENDING','PAID','OVERDUE')),
    UNIQUE (loan_id,installment),
    FOREIGN KEY (loan_id) REFERENCES loans(loan_id)
);

CREATE TABLE audit_log(
    log_id INTEGER PRIMARY KEY,
    table_name TEXT NOT NULL,
    log_action TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    old_value TEXT ,
    new_value TEXT ,
    changed_by INTEGER,
    changed_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (changed_by) REFERENCES users(user_id)
);


---------------------------
-- TRIGGERS
--------------------------- 
 

 CREATE TRIGGER trg_acc 
 AFTER UPDATE OF balance ON accounts
 FOR EACH ROW 
 WHEN old.balance <> new.balance
 BEGIN
    INSERT INTO audit_log (table_name , log_action, record_id , old_value, new_value ) VALUES ('accounts','Account Balance Changed',new.account_id,old.balance,new.balance);
END;

CREATE TRIGGER trg_acc_status
AFTER UPDATE OF acc_status ON accounts
FOR EACH ROW
WHEN old.acc_status<>new.acc_status
BEGIN
 INSERT INTO audit_log (table_name , log_action, record_id , old_value, new_value ) VALUES ('accounts','Account Status Changed',new.account_id,old.acc_status,new.acc_status);
END;

CREATE TRIGGER trg_loan_status
AFTER UPDATE OF loan_status ON loans
FOR EACH ROW
WHEN old.loan_status<>new.loan_status
BEGIN 
INSERT INTO audit_log (table_name , log_action, record_id , old_value, new_value ) VALUES ('loans','Loan Status Changed',new.loan_id,old.loan_status,new.loan_status);
END;

CREATE TRIGGER trg_acc_created
AFTER INSERT ON accounts
FOR EACH ROW
BEGIN
INSERT INTO audit_log(table_name,log_action,record_id) VALUES ('accounts','Account Created',new.account_id);
END;
