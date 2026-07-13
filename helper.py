from datetime import datetime
import random
def to_paisa(rupees):
    p= int(round(float(rupees)*100))
    return p

def to_rupees(paisa):
    if paisa is None:
        paisa =0
    r=paisa/100
    return r

def fmt_money(paisa):
    return f"Rs. {to_rupees(paisa):,.2f}"

def gen_ref_no():
    return f"TXN-{datetime.now().strftime("%Y%m%d")}-{random.randint(100,9999)}"


""" 
       P x r x (1+r)ⁿ
EMI = ───────────────────
         (1+r)ⁿ - 1

"""

def calc_emi(principal_paisa, annual_rate, months):
    if annual_rate == 0:
        return int(round(principal_paisa / months))    

    r = annual_rate / 12 / 100
    factor = (1 + r) ** months
    emi = principal_paisa * r * factor / (factor - 1)
    return int(round(emi))


