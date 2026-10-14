"""Property Rental and Lease Management System - Flask + MySQL (mysql-connector-python)."""
import os
from datetime import date
from flask import Flask, render_template_string, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-key")
DB = dict(host=os.getenv("DB_HOST", "localhost"), user=os.getenv("DB_USER", "root"),
          password=os.getenv("DB_PASSWORD", ""), database=os.getenv("DB_NAME", "property_rental"))

def run(sql, args=(), write=False):
    """Run a parameterized query (never string-concatenated SQL). Returns rows or lastrowid."""
    conn = mysql.connector.connect(**DB)
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, args)
        if write:
            conn.commit()
            return cur.lastrowid
        return cur.fetchall()
    except Error:
        conn.rollback()
        raise
    finally:
        conn.close()

# field: (column, label, input type, required)   ; "fk:<sql>" gives a dropdown from a query
MODULES = {
 "owner": dict(title="Owners", pk="owner_id", fields=[("name","Name","text",1),("phone","Phone","text",1),("email","Email","email",0),("address","Address","text",0)],
   sql="SELECT * FROM owner ORDER BY owner_id", refs=[("property","owner_id")]),
 "property": dict(title="Properties", pk="property_id", fields=[("owner_id","Owner","fk:SELECT owner_id id, name label FROM owner",1),("address","Address","text",1),
   ("type","Type","sel:Apartment,House,Shop,Office",1),("rent_amount","Monthly rent (INR)","num",1)],
   sql="""SELECT p.property_id, o.name AS owner, p.address, p.type, p.rent_amount,
          IF(EXISTS(SELECT 1 FROM lease l WHERE l.property_id=p.property_id AND CURDATE() BETWEEN l.start_date AND l.end_date),'Occupied','Vacant') AS status
          FROM property p JOIN owner o ON o.owner_id=p.owner_id ORDER BY p.property_id""",
   refs=[("lease","property_id"),("maintenance","property_id")]),
 "tenant": dict(title="Tenants", pk="tenant_id", fields=[("name","Name","text",1),("phone","Phone","text",1),("email","Email","email",0),("id_proof","ID proof","text",0)],
   sql="SELECT * FROM tenant ORDER BY tenant_id", refs=[("lease","tenant_id"),("maintenance","tenant_id")]),
 "lease": dict(title="Leases", pk="lease_id", fields=[("property_id","Property","fk:SELECT property_id id, address label FROM property",1),
   ("tenant_id","Tenant","fk:SELECT tenant_id id, name label FROM tenant",1),("start_date","Start date","date",1),("end_date","End date","date",1),("deposit","Deposit (INR)","num",1)],
   sql="""SELECT l.lease_id, p.address AS property, t.name AS tenant, l.start_date, l.end_date, l.deposit,
          IF(CURDATE() BETWEEN l.start_date AND l.end_date,
             IF(EXISTS(SELECT 1 FROM payment x WHERE x.lease_id=l.lease_id AND MONTH(x.payment_date)=MONTH(CURDATE()) AND YEAR(x.payment_date)=YEAR(CURDATE())),'Paid','Due'),'Not active') AS rent_status
          FROM lease l JOIN property p ON p.property_id=l.property_id JOIN tenant t ON t.tenant_id=l.tenant_id ORDER BY l.lease_id""",
   refs=[("payment","lease_id")]),
 "payment": dict(title="Payments", pk="payment_id", fields=[("lease_id","Lease","fk:SELECT l.lease_id id, CONCAT('Lease ',l.lease_id,' - ',t.name) label FROM lease l JOIN tenant t ON t.tenant_id=l.tenant_id",1),
   ("amount","Amount (INR)","num",1),("payment_date","Payment date","date",1),("mode","Mode","sel:Cash,UPI,Bank Transfer,Cheque",1)],
   sql="SELECT pay.*, t.name AS tenant FROM payment pay JOIN lease l ON l.lease_id=pay.lease_id JOIN tenant t ON t.tenant_id=l.tenant_id ORDER BY pay.payment_id", refs=[]),
 "maintenance": dict(title="Maintenance", pk="request_id", fields=[("property_id","Property","fk:SELECT property_id id, address label FROM property",1),
   ("tenant_id","Tenant","fk:SELECT tenant_id id, name label FROM tenant",1),("issue_desc","Issue","text",1),("status","Status","sel:Open,In Progress,Resolved",1)],
   sql="""SELECT m.request_id, p.address AS property, t.name AS tenant, m.issue_desc, m.status FROM maintenance m
          JOIN property p ON p.property_id=m.property_id JOIN tenant t ON t.tenant_id=m.tenant_id ORDER BY m.request_id""", refs=[]),
}
LABEL = {"property": "a property", "lease": "a lease", "payment": "a payment", "maintenance": "a maintenance request"}

PAGE = """<!doctype html><title>Property Rental Manager</title><meta name=viewport content="width=device-width,initial-scale=1">
<style>body{font:15px system-ui;margin:0;background:#f4f7fb;color:#12294a}nav{background:#12294a;padding:10px 16px}nav a{color:#fff;margin-right:14px;text-decoration:none}
main{max-width:1000px;margin:auto;padding:16px}table{border-collapse:collapse;width:100%;background:#fff;display:block;overflow-x:auto}td,th{border:1px solid #cfd8e3;padding:6px 10px;text-align:left}
th{background:#0e5297;color:#fff}.card{background:#fff;padding:12px 16px;border-radius:8px;display:inline-block;margin:4px 8px 4px 0;box-shadow:0 1px 4px #0002}.card b{font-size:22px;display:block}
.ok{background:#d9f5e5;padding:8px;border-radius:6px}.err{background:#fde0e0;padding:8px;border-radius:6px}form.add{background:#fff;padding:12px;border-radius:8px;margin:12px 0}
label{display:block;margin:6px 0 2px}input,select{padding:6px;width:260px;max-width:100%}button{background:#0e5297;color:#fff;border:0;padding:7px 14px;border-radius:5px;cursor:pointer}button.del{background:#c0392b;padding:3px 8px}</style>
<nav><a href="/">Dashboard</a>{% for k,m in modules.items() %}<a href="/{{k}}">{{m.title}}</a>{% endfor %}</nav><main>
{% for c,msg in get_flashed_messages(with_categories=true) %}<p class="{{c}}">{{msg}}</p>{% endfor %}{{ body|safe }}</main>"""

def page(body):
    return render_template_string(PAGE, body=body, modules=MODULES)

@app.route("/")
def dashboard():
    n = lambda t: run(f"SELECT COUNT(*) c FROM {t}")[0]["c"]
    occ = run("""SELECT p.type, COUNT(*) AS total_units,
                 SUM(EXISTS(SELECT 1 FROM lease l WHERE l.property_id=p.property_id AND CURDATE() BETWEEN l.start_date AND l.end_date)) AS occupied_units
                 FROM property p GROUP BY p.type""")
    rev = run("SELECT COALESCE(SUM(amount),0) r FROM payment WHERE MONTH(payment_date)=MONTH(CURDATE()) AND YEAR(payment_date)=YEAR(CURDATE())")[0]["r"]
    over = run("""SELECT l.lease_id, t.name AS tenant, p.address, p.rent_amount FROM lease l
                  JOIN tenant t ON t.tenant_id=l.tenant_id JOIN property p ON p.property_id=l.property_id
                  WHERE CURDATE() BETWEEN l.start_date AND l.end_date AND l.lease_id NOT IN
                  (SELECT pay.lease_id FROM payment pay WHERE MONTH(pay.payment_date)=MONTH(CURDATE()) AND YEAR(pay.payment_date)=YEAR(CURDATE()))""")
    return page(render_template_string("""<h2>Dashboard</h2>
    {% for k,v in cards %}<div class=card>{{k}}<b>{{v}}</b></div>{% endfor %}
    <h3>Occupancy by property type</h3>{{ tbl(occ)|safe }}<h3>Overdue rent this month</h3>{{ tbl(over)|safe }}""",
    cards=[("Properties", n("property")), ("Tenants", n("tenant")), ("Leases", n("lease")), ("Maintenance requests", n("maintenance")),
           ("Revenue this month (INR)", f"{rev:,.2f}")], occ=occ, over=over, tbl=table_html))

def table_html(rows, mod=None):
    if not rows:
        return "<p>No records.</p>"
    cols = list(rows[0].keys())
    h = "".join(f"<th>{c}</th>" for c in cols) + ("<th></th>" if mod else "")
    out = ""
    for r in rows:
        out += "<tr>" + "".join(f"<td>{r[c]}</td>" for c in cols)
        if mod:
            pk = r[MODULES[mod]["pk"]]
            out += (f'<td style="white-space:nowrap"><a href="/{mod}/edit/{pk}"><button type=button>Edit</button></a> '
                    f'<form method=post action="/{mod}/delete/{pk}" style="display:inline" onsubmit="return confirm(\'Remove this record?\')"><button class=del>Remove</button></form></td>')
        out += "</tr>"
    return f"<table><tr>{h}</tr>{out}</table>"

def form_html(mod, row=None):
    """Add form (row=None) or edit form pre-filled from an existing row."""
    action = f"/{mod}/add" if row is None else f"/{mod}/edit/{row[MODULES[mod]['pk']]}"
    h = f'<form class=add method=post action="{action}"><b>{"+ New" if row is None else "Edit record #" + str(row[MODULES[mod]["pk"]])}</b>'
    for col, label, kind, req in MODULES[mod]["fields"]:
        r = "required" if req else ""
        cur = "" if row is None or row[col] is None else str(row[col])
        h += f"<label>{label}{' *' if req else ''}</label>"
        if kind.startswith("fk:"):
            opts = "".join(f'<option value="{o["id"]}" {"selected" if str(o["id"])==cur else ""}>{o["id"]} - {o["label"]}</option>' for o in run(kind[3:]))
            h += f'<select name={col} {r}>{opts}</select>'
        elif kind.startswith("sel:"):
            h += f'<select name={col}>' + "".join(f'<option {"selected" if o==cur else ""}>{o}</option>' for o in kind[4:].split(",")) + "</select>"
        else:
            t = {"num": 'number step=0.01 min=0.01', "date": "date"}.get(kind, kind)
            h += f'<input type={t} name={col} value="{cur}" {r}>'
    return h + f'<br><br><button>{"Save" if row is None else "Update"}</button></form>'

@app.route("/<mod>")
def listing(mod):
    if mod not in MODULES:
        return redirect(url_for("dashboard"))
    q = request.args.get("q", "").strip().lower()
    rows = run(MODULES[mod]["sql"])
    if q:                                                   # simple search across every displayed column
        rows = [r for r in rows if any(q in str(v).lower() for v in r.values())]
    search = f'<form method=get style="margin:8px 0"><input name=q value="{q}" placeholder="Search {MODULES[mod]["title"].lower()}..."> <button>Search</button></form>'
    return page(f"<h2>{MODULES[mod]['title']}</h2>{search}{form_html(mod)}{table_html(rows, mod)}")

def parse_form(mod):
    """Validate submitted form. Returns (values_dict, error_message)."""
    vals = []
    for col, label, kind, req in MODULES[mod]["fields"]:
        v = request.form.get(col, "").strip()
        if req and not v:                                   # required-field validation
            return None, f"{label}: This field is required."
        if kind == "num" and v and float(v) <= 0:           # positive amounts only
            return None, f"{label} must be a positive value."
        vals.append(v or None)
    d = dict(zip([f[0] for f in MODULES[mod]["fields"]], vals))
    if mod == "lease" and date.fromisoformat(d["end_date"]) <= date.fromisoformat(d["start_date"]):
        return None, "End date must be after the start date."
    return d, None

@app.route("/<mod>/add", methods=["POST"])
def add(mod):
    if mod not in MODULES:
        return redirect(url_for("dashboard"))
    d, err = parse_form(mod)
    if err:
        flash(err, "err"); return redirect(url_for("listing", mod=mod))
    try:
        run(f"INSERT INTO {mod} ({','.join(d)}) VALUES ({','.join(['%s']*len(d))})", list(d.values()), write=True)
        flash("Record added successfully.", "ok")
    except Error as e:                                      # database constraints are the second line of defence
        flash(f"Database rejected the record: {e.msg}", "err")
    return redirect(url_for("listing", mod=mod))

@app.route("/<mod>/edit/<int:rid>", methods=["GET", "POST"])
def edit(mod, rid):
    if mod not in MODULES:
        return redirect(url_for("dashboard"))
    m = MODULES[mod]
    if request.method == "POST":
        d, err = parse_form(mod)
        if err:
            flash(err, "err"); return redirect(url_for("edit", mod=mod, rid=rid))
        try:
            run(f"UPDATE {mod} SET {','.join(c + '=%s' for c in d)} WHERE {m['pk']}=%s", list(d.values()) + [rid], write=True)
            flash("Record updated successfully.", "ok")
        except Error as e:
            flash(f"Database rejected the update: {e.msg}", "err")
        return redirect(url_for("listing", mod=mod))
    rows = run(f"SELECT * FROM {mod} WHERE {m['pk']}=%s", (rid,))
    if not rows:
        flash("Record not found.", "err"); return redirect(url_for("listing", mod=mod))
    return page(f"<h2>Edit - {m['title']}</h2>{form_html(mod, rows[0])}<p><a href='/{mod}'>Cancel</a></p>")

@app.route("/<mod>/delete/<int:rid>", methods=["POST"])
def delete(mod, rid):
    if mod not in MODULES:
        return redirect(url_for("dashboard"))
    for child, fk in MODULES[mod]["refs"]:                  # check references before issuing DELETE
        if run(f"SELECT COUNT(*) c FROM {child} WHERE {fk}=%s", (rid,))[0]["c"]:
            flash(f"Can't remove this record - it is referenced by {LABEL[child]}. Remove that first.", "err")
            return redirect(url_for("listing", mod=mod))
    try:
        run(f"DELETE FROM {mod} WHERE {MODULES[mod]['pk']}=%s", (rid,), write=True)
        flash("Record removed.", "ok")
    except Error as e:
        flash(f"Could not remove record: {e.msg}", "err")
    return redirect(url_for("listing", mod=mod))

if __name__ == "__main__":
    app.run(debug=True)
