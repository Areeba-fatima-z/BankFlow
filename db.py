from flask import g
import config
import sqlite3

def get_db():
    if 'db' not in g:
        g.db=sqlite3.connect(config.DB_PATH)
        g.db.row_factory=sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

"""
g.pop("db", None) kyun, g.db kyun nahi?
Hint: agar connection bana hi nahi tha (koi query nahi chali) to g.db exist nahi karta → AttributeError. pop default None deta hai.
"""
def close_db(exc=None):
    conn=g.pop('db',None)
    if conn is not None:
        conn.close()

def query(sql,params=(),one=False):
    """
    SELECT ke liye.
    one=True  -> ek Row ya None
    one=False -> list of Rows (khaali list ho sakti hai)
    """
    rows=get_db().execute(sql,params).fetchall()
    if one:
        return rows[0]  if rows else None
    return rows
    
def execute(sql ,params=()):
    """
    Single-shot INSERT / UPDATE / DELETE — auto commit.
    Returns: lastrowid

    Multi-step writes (transfer, loan approve) me ye MAT use karna.
       Ye har call pe commit karta hai — beech me commit ho gaya to
       rollback bekaar ho jayega aur paisa gayab ho sakta hai.
    """
    db=get_db()
    cur=db.execute(sql,params)
    db.commit()
    return cur.lastrowid


def  log_action(action,table,record_id,old=None,new=None,user_id=None):
    """
     commit NAHI karta — > caller decide karega.
       Isse transfer ke beech me safely bulaya ja sakta hai.
    """
    get_db().execute("""
        INSERT INTO audit_log (table_name, log_action, record_id,
                               old_value, new_value, changed_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (table, action, record_id, old, new, user_id))

