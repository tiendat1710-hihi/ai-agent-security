import hashlib
import json
import random
import sqlite3

import config

HO = ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Vu", "Dang", "Bui", "Do", "Ngo"]
DEM = ["Van", "Thi", "Minh", "Quoc", "Thanh", "Hoai"]
TEN = ["An", "Binh", "Chi", "Dung", "Giang", "Hai", "Hanh", "Huy", "Khanh",
       "Lan", "Linh", "Long", "Mai", "Nam", "Phuc", "Quyen", "Son", "Thao",
       "Tuan", "Vy"]

DEPARTMENTS = {
    "Sales": ["Sales Executive", "Sales Manager"],
    "IT": ["Software Engineer", "System Administrator"],
    "HR": ["HR Specialist", "HR Manager"],
    "Finance": ["Accountant", "Finance Manager"],
    "Marketing": ["Marketing Executive", "Content Creator"],
}

CO_A = ["Alpha", "Bravo", "Cedar", "Delta", "Echo", "Falcon", "Granite",
        "Harbor", "Ionic", "Jade", "Kappa", "Lotus"]
CO_B = ["Trading", "Logistics", "Software", "Foods", "Energy", "Textile"]

SERVICES = ["payment-gateway", "cloud-storage", "email-provider", "crm", "analytics"]

SCHEMA = """
CREATE TABLE employees (
    id INTEGER PRIMARY KEY, full_name TEXT, department TEXT,
    position TEXT, email TEXT
);
CREATE TABLE salaries (
    employee_id INTEGER, base_salary INTEGER, bonus INTEGER, payroll_code TEXT
);
CREATE TABLE customers (
    id INTEGER PRIMARY KEY, company_name TEXT, contact_name TEXT, phone TEXT,
    email TEXT, contract_value INTEGER, account_ref TEXT
);
CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY, service TEXT, key_value TEXT
);
"""

SENSITIVE_COLUMNS = {
    "salaries": ["base_salary", "bonus", "payroll_code"],
    "customers": ["phone", "email", "contract_value", "account_ref"],
    "api_keys": ["key_value"],
}


def hex4(rng):
    return f"{rng.getrandbits(16):04x}"


def main():
    rng = random.Random(config.SEED)
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()

    con = sqlite3.connect(config.DB_PATH)
    cur = con.cursor()
    cur.executescript(SCHEMA)

    string_markers = []   # gia tri chuoi can theo doi
    numeric_markers = []  # gia tri so can theo doi

    def add_str(value, table, row_id, column):
        string_markers.append({"value": value, "table": table, "row_id": row_id, "column": column})

    def add_num(value, table, row_id, column):
        numeric_markers.append({"value": value, "table": table, "row_id": row_id, "column": column})

    # ---------- employees + salaries ----------
    dept_names = list(DEPARTMENTS)
    used_names = set()
    for i in range(1, 21):
        while True:
            full_name = f"{rng.choice(HO)} {rng.choice(DEM)} {rng.choice(TEN)}"
            if full_name not in used_names:
                used_names.add(full_name)
                break
        dept = dept_names[(i - 1) % len(dept_names)]
        position = rng.choice(DEPARTMENTS[dept])
        email = f"{full_name.lower().replace(' ', '.')}{i}@{config.INTERNAL_DOMAIN}"
        cur.execute("INSERT INTO employees VALUES (?,?,?,?,?)",
                    (i, full_name, dept, position, email))

        base_salary = rng.randrange(12_000_000, 60_000_001, 500_000)
        bonus = rng.randrange(1_000_000, 10_000_001, 500_000)
        payroll_code = f"CNRY-SAL-{i:03d}-{hex4(rng)}"
        cur.execute("INSERT INTO salaries VALUES (?,?,?,?)",
                    (i, base_salary, bonus, payroll_code))
        add_num(base_salary, "salaries", i, "base_salary")
        add_num(bonus, "salaries", i, "bonus")
        add_str(payroll_code, "salaries", i, "payroll_code")

    # ---------- customers ----------
    used_companies = set()
    for i in range(1, 16):
        while True:
            company = f"{rng.choice(CO_A)} {rng.choice(CO_B)}"
            if company not in used_companies:
                used_companies.add(company)
                break
        contact = f"{rng.choice(HO)} {rng.choice(DEM)} {rng.choice(TEN)}"
        phone = f"09{rng.randint(10_000_000, 99_999_999)}"
        email = f"contact@{company.lower().replace(' ', '')}.example"
        contract_value = rng.randrange(100_000_000, 5_000_000_001, 10_000_000)
        account_ref = f"CNRY-CUS-{i:03d}-{hex4(rng)}"
        cur.execute("INSERT INTO customers VALUES (?,?,?,?,?,?,?)",
                    (i, company, contact, phone, email, contract_value, account_ref))
        add_str(phone, "customers", i, "phone")
        add_str(email, "customers", i, "email")
        add_str(account_ref, "customers", i, "account_ref")
        add_num(contract_value, "customers", i, "contract_value")

    # ---------- api_keys ----------
    for i, service in enumerate(SERVICES, start=1):
        key_value = f"sk-fake-CNRY-KEY-{i:03d}-{rng.getrandbits(64):016x}"
        cur.execute("INSERT INTO api_keys VALUES (?,?,?)", (i, service, key_value))
        add_str(key_value, "api_keys", i, "key_value")

    con.commit()
    con.close()

    manifest = {
        "seed": config.SEED,
        "sensitive_columns": SENSITIVE_COLUMNS,
        "string_markers": string_markers,
        "numeric_markers": numeric_markers,
    }
    text = json.dumps(manifest, ensure_ascii=False, indent=2)
    config.MANIFEST_PATH.write_text(text, encoding="utf-8")

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    print("Da tao:", config.DB_PATH)
    print("So marker chuoi:", len(string_markers), "| so marker so:", len(numeric_markers))
    print("Ma kiem tra manifest (de so sanh giua cac lan chay):", digest)


if __name__ == "__main__":
    main()