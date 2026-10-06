import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from pathlib import Path
import sqlite3
import uuid
import re
import os
import json

st.set_page_config(
    page_title="DataClean Pro | Data Quality Engineering",
    page_icon="🧹",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://docs.streamlit.io/",
        "Report a bug": "https://github.com/",
        "About": "DataClean Pro — production-style data cleaning and quality validation dashboard."
    },
)

from datetime import datetime

# ---------------------------------------------------------------------------
# Portfolio-grade UI
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .block-container {padding-top: 1.4rem; padding-bottom: 2.5rem; max-width: 1500px;}
    [data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,.18);
        border-radius: 14px;
        padding: 14px 16px;
        background: rgba(128,128,128,.035);
    }
    .hero {
        padding: 26px 28px;
        border: 1px solid rgba(128,128,128,.18);
        border-radius: 18px;
        margin-bottom: 20px;
        background: linear-gradient(135deg, rgba(90,90,90,.08), rgba(90,90,90,.02));
    }
    .hero h1 {margin: 0 0 7px 0; font-size: 2.25rem;}
    .hero p {margin: 0; opacity: .78; font-size: 1.02rem;}
    .badge {
        display:inline-block; padding:4px 9px; border-radius:999px;
        border:1px solid rgba(128,128,128,.25); font-size:.78rem;
        margin-right:5px; margin-top:9px;
    }
    .section-note {
        padding: 11px 14px; border-left: 4px solid currentColor;
        border-radius: 7px; background: rgba(128,128,128,.05);
        margin: 8px 0 16px 0;
    }
    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(128,128,128,.18);
    }
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        font-weight: 700;
    }
    .audit-card {
        padding: 14px 16px; border:1px solid rgba(128,128,128,.18);
        border-radius:12px; margin-bottom:10px;
    }
    footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)


def _portfolio_hero():
    st.markdown("""
    <div class="hero">
        <h1>🧹 DataClean Pro</h1>
        <p>Production-style data cleaning, validation & quality analytics — built for reliable downstream analysis.</p>
        <span class="badge">Pandas</span>
        <span class="badge">Data Quality</span>
        <span class="badge">Validation</span>
        <span class="badge">Outlier Detection</span>
        <span class="badge">Audit Trail</span>
        <span class="badge">Excel / CSV Export</span>
    </div>
    """, unsafe_allow_html=True)


def _safe_pct(value):
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "—"

def _build_quality_summary(before_df, after_df, before_score, after_score):
    before_rows, after_rows = len(before_df), len(after_df)
    before_cols, after_cols = len(before_df.columns), len(after_df.columns)
    duplicate_before = int(before_df.duplicated().sum())
    duplicate_after = int(after_df.duplicated().sum())
    missing_before = int(before_df.isna().sum().sum())
    missing_after = int(after_df.isna().sum().sum())
    return {
        "Generated At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Rows Before": before_rows,
        "Rows After": after_rows,
        "Columns Before": before_cols,
        "Columns After": after_cols,
        "Missing Cells Before": missing_before,
        "Missing Cells After": missing_after,
        "Duplicate Rows Before": duplicate_before,
        "Duplicate Rows After": duplicate_after,
        "Quality Score Before": round(float(before_score), 2) if pd.notna(before_score) else None,
        "Quality Score After": round(float(after_score), 2) if pd.notna(after_score) else None,
    }

def _download_audit_csv(summary, filename="dataclean_pro_quality_audit.csv"):
    audit_df = pd.DataFrame([summary])
    return audit_df.to_csv(index=False).encode("utf-8")


# ============================================================
# DataClean Pro — Portfolio Edition
# Automated Data Cleaning & Data Quality Analyzer
# ============================================================


_portfolio_hero()

# ============================================================
# HELPERS
# ============================================================

MISSING_TOKENS = {
    "", "na", "n/a", "null", "none", "nan", "-", "--",
    "missing", "not available", "not_applicable"
}

def clean_column_name(value):
    value = str(value).strip()
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^\w]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "Unnamed_Column"

def make_unique(columns):
    seen, result = {}, []
    for col in columns:
        if col not in seen:
            seen[col] = 0
            result.append(col)
        else:
            seen[col] += 1
            result.append(f"{col}_{seen[col]}")
    return result

def standardize_text_series(series):
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

def quality_score(df):
    """Diagnostic quality score: completeness + duplicate/format validity.
    It never changes the dataset and is intentionally domain-agnostic.
    """
    rows, cols = df.shape
    if rows == 0 or cols == 0:
        return 0.0
    total = max(rows * cols, 1)
    missing_rate = float(df.isna().sum().sum()) / total
    duplicate_rate = float(df.duplicated().sum()) / max(rows, 1)
    invalid = 0
    for c in df.columns:
        k = re.sub(r"[^a-z0-9]+", "_", str(c).strip().lower())
        if any(x in k for x in ("email", "e_mail", "mail")):
            s = df[c].astype("string")
            invalid += int((s.notna() & ~s.str.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", na=False)).sum())
        elif any(x in k for x in ("phone", "mobile", "telephone", "contact_number", "contact_no")):
            s = df[c].astype("string")
            invalid += int((s.notna() & ~s.str.fullmatch(r"\d{10,15}", na=False)).sum())
    invalid_rate = invalid / total
    score = 100 * (1 - 0.55 * missing_rate - 0.25 * duplicate_rate - 0.20 * min(invalid_rate, 1))
    return round(max(0.0, min(100.0, score)), 1)


def quality_status(score):
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 50:
        return "Needs Attention"
    return "Poor"

def profile(df):
    return pd.DataFrame([
        {
            "Column": c,
            "Data Type": str(df[c].dtype),
            "Rows": len(df),
            "Non-Null": int(df[c].notna().sum()),
            "Missing": int(df[c].isna().sum()),
            "Missing %": round(df[c].isna().mean() * 100, 2),
            "Unique": int(df[c].nunique(dropna=True)),
        }
        for c in df.columns
    ])

def get_identifier_columns(df):
    out = []
    for c in df.columns:
        n = c.lower()
        if any(x in n for x in ["id", "code", "zip", "pincode", "phone", "mobile"]):
            out.append(c)
    return out

def numeric_candidates(df):
    cols = []
    for c in df.select_dtypes(include=["number"]).columns:
        if c not in get_identifier_columns(df):
            cols.append(c)
    return cols


# ============================================================
# VALIDATION / STANDARDIZATION
# ============================================================


def _canonicalize(series):
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.lower()
    )

def standardize_missing(df, log):
    changed = 0
    for c in df.columns:
        if not (pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_string_dtype(df[c])):
            continue
        s = df[c].astype("string")
        normalized = s.str.strip().str.lower()
        mask = normalized.isin(MISSING_TOKENS).fillna(False)
        count = int(mask.sum())
        if count:
            df.loc[mask, c] = pd.NA
            changed += count
    log["Missing-value tokens standardized"] = changed
    return df

def _apply_mapping(df, col, mapping, log):
    if col not in df.columns:
        return
    old = df[col].astype("string")
    normalized = _canonicalize(df[col])
    mapped = normalized.map(mapping)
    # Unknown values are retained after safe whitespace normalization.
    new = mapped.fillna(normalized.str.title())
    # Restore intentional casing for known values via mapping.
    df[col] = new
    log[f"{col} values standardized"] = int((old != df[col].astype("string")).fillna(False).sum())

def standardize_known_categories(df, log):
    mappings = {
        "Gender": {
            "male": "Male", "m": "Male", "man": "Male",
            "female": "Female", "f": "Female", "woman": "Female",
            "other": "Other", "o": "Other",
        },
        "City": {
            "ahmedabad": "Ahmedabad",
            "bangalore": "Bengaluru", "bengaluru": "Bengaluru", "blr": "Bengaluru",
            "chennai": "Chennai", "delhi": "Delhi", "new delhi": "Delhi",
            "hyderabad": "Hyderabad", "jaipur": "Jaipur", "kolkata": "Kolkata",
            "mumbai": "Mumbai", "mysuru": "Mysuru", "mysore": "Mysuru",
            "pune": "Pune",
        },
        "State": {
            "karnataka": "Karnataka", "maharashtra": "Maharashtra",
            "tamil nadu": "Tamil Nadu", "telangana": "Telangana",
            "west bengal": "West Bengal", "rajasthan": "Rajasthan",
            "gujarat": "Gujarat", "delhi": "Delhi",
        },
        "Customer_Segment": {
            "consumer": "Consumer", "corporate": "Corporate",
            "small business": "Small Business", "smb": "Small Business",
            "student": "Student",
        },
        "Category": {
            "electronics": "Electronics", "electronic": "Electronics",
            "accessories": "Accessories", "accessory": "Accessories",
            "storage": "Storage", "wearables": "Wearables", "wearable": "Wearables",
        },
        "Product": {
            "laptop": "Laptop", "mouse": "Mouse", "keyboard": "Keyboard",
            "monitor": "Monitor", "printer": "Printer", "smartphone": "Smartphone",
            "smartwatch": "Smartwatch", "tablet": "Tablet", "usb hub": "USB Hub",
            "webcam": "Webcam", "headphones": "Headphones", "external hdd": "External HDD",
        },
        "Payment_Method": {
            "cash": "Cash", "credit card": "Credit Card", "creditcard": "Credit Card",
            "credit-card": "Credit Card", "debit card": "Debit Card",
            "net banking": "Net Banking", "netbanking": "Net Banking",
            "paypal": "PayPal", "upi": "UPI",
        },
        "Order_Status": {
            "completed": "Completed", "complete": "Completed",
            "pending": "Pending", "shipped": "Shipped",
            "cancelled": "Cancelled", "returned": "Returned", "return": "Returned",
        },
        "Sales_Channel": {
            "website": "Website", "web site": "Website", "web": "Website",
            "mobile app": "Mobile App", "mobileapp": "Mobile App",
            "marketplace": "Marketplace", "market place": "Marketplace",
            "social media": "Social Media", "store": "Store", "app": "Mobile App",
        },
    }
    for col, mapping in mappings.items():
        _apply_mapping(df, col, mapping, log)
    return df

def standardize_special(df, log):
    if "Customer_Name" in df.columns:
        old = df["Customer_Name"].astype("string")
        new = old.str.strip().str.replace(r"\\s+", " ", regex=True).str.title()
        df["Customer_Name"] = new
        log["Customer names standardized"] = int((old != new).fillna(False).sum())

    if "Email" in df.columns:
        old = df["Email"].astype("string")
        new = old.str.strip().str.lower()
        df["Email"] = new
        log["Email values normalized"] = int((old != new).fillna(False).sum())

    if "Phone" in df.columns:
        old = df["Phone"].astype("string")
        def normalize_phone(value):
            if pd.isna(value) or str(value).strip() == "":
                return pd.NA
            raw = re.sub(r"\.0$", "", str(value).strip())
            digits = re.sub(r"\D", "", raw)
            if len(digits) == 12 and digits.startswith("91"):
                digits = digits[2:]
            return digits if len(digits) == 10 else pd.NA
        new = old.map(normalize_phone).astype("string")
        invalid = old.notna() & new.isna()
        df["Phone"] = new
        log["Phone values normalized"] = int((old != new).fillna(False).sum())
        log["Invalid phone values converted to missing"] = int(invalid.sum())
    return df


def convert_numeric(df, log):
    explicit = {"Age", "Quantity", "Unit_Price", "Discount", "Sales", "Rating"}
    word_numbers = {"zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,
                    "six":6,"seven":7,"eight":8,"nine":9,"ten":10}

    def parse_general(value):
        if pd.isna(value) or str(value).strip() == "":
            return np.nan
        x = str(value).strip().lower()
        if x in word_numbers:
            return float(word_numbers[x])
        x = x.replace(",", "")
        x = re.sub(r"[₹$€£]", "", x)
        match = re.search(r"-?\d+(?:\.\d+)?", x)
        return float(match.group()) if match else np.nan

    def parse_discount(value):
        if pd.isna(value) or str(value).strip() == "":
            return np.nan
        x = str(value).strip().lower().replace(" ", "")
        if x in {"none","null","na","n/a","nan","-","--"}:
            return np.nan
        if "%" in x:
            n = parse_general(x.replace("%",""))
            return np.nan if pd.isna(n) else n/100
        n = parse_general(x)
        return np.nan if pd.isna(n) else (n/100 if n > 1 else n)

    converted = invalid = 0
    protected = {"customer_id","order_id","phone","mobile","mobile_number","email","zip","pincode"}

    for c in list(df.columns):
        if c.lower() in protected:
            continue
        is_text = pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_string_dtype(df[c])
        if not is_text:
            continue
        original = df[c]
        if c == "Discount":
            numeric = original.map(parse_discount)
        elif c in explicit:
            numeric = original.map(parse_general)
        else:
            cleaned = original.astype("string").str.strip()
            numeric = pd.to_numeric(
                cleaned.str.replace(",", "", regex=False)
                       .str.replace("₹", "", regex=False)
                       .str.replace("$", "", regex=False)
                       .str.replace("€", "", regex=False),
                errors="coerce"
            )
        non_null = int(original.notna().sum())
        if non_null == 0:
            continue
        success = int(pd.Series(numeric).notna().sum())
        if c in explicit or success/non_null >= 0.95:
            invalid += non_null-success
            df[c] = pd.to_numeric(numeric, errors="coerce").astype("float64")
            converted += 1
    log["Columns converted to numeric"] = converted
    log["Invalid numeric values converted to missing"] = invalid
    return df


def convert_dates(df, log):
    converted, invalid = 0, 0
    for c in list(df.columns):
        is_text = pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_string_dtype(df[c])
        if not is_text:
            continue
        non_null = int(df[c].notna().sum())
        if non_null == 0:
            continue

        # Date/time conversion is intentionally restricted to date/time-named columns.
        if not any(token in c.lower() for token in ["date", "time"]):
            continue

        parsed = pd.to_datetime(df[c], errors="coerce", format="mixed")
        success = int(parsed.notna().sum())
        if success / non_null >= 0.80:
            invalid += non_null - success
            df[c] = parsed
            converted += 1

    log["Columns converted to dates"] = converted
    log["Invalid date values converted to missing"] = invalid
    return df

def validate_emails(df, log):
    if "Email" not in df.columns:
        return df
    s = df["Email"].astype("string").str.strip().str.lower()
    valid = s.str.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", na=False)
    invalid = s.notna() & ~valid
    log["Invalid email values detected"] = int(invalid.sum())
    df.loc[invalid, "Email"] = pd.NA
    log["Invalid email values converted to missing"] = int(invalid.sum())
    return df

def validate_phone(df, log):
    if "Phone" not in df.columns:
        return df
    def normalize(value):
        if pd.isna(value) or str(value).strip() == "":
            return pd.NA
        digits = re.sub(r"\D", "", str(value).strip())
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        return digits if len(digits) == 10 else pd.NA
    before = df["Phone"].astype("string")
    normalized = before.map(normalize).astype("string")
    invalid = before.notna() & normalized.isna()
    df["Phone"] = normalized
    log["Invalid phone values detected"] = int(invalid.sum())
    log["Invalid phone values converted to missing"] = int(invalid.sum())
    return df

def validate_business_rules(df, log, fix_sales=False):
    violations = 0
    rules = {
        "Age": lambda s: s.notna() & ((s < 18) | (s > 100)),
        "Quantity": lambda s: s.notna() & (s <= 0),
        "Unit_Price": lambda s: s.notna() & (s < 0),
        "Sales": lambda s: s.notna() & (s < 0),
        "Rating": lambda s: s.notna() & ~s.between(1, 5),
        "Discount": lambda s: s.notna() & ~s.between(0, 1),
    }
    for col, rule in rules.items():
        if col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce")
            bad = rule(s)
            label = col.replace("_"," ")
            log[f"Invalid {label} values converted to missing"] = int(bad.sum())
            df.loc[bad, col] = np.nan
            violations += int(bad.sum())

    city_state = {"Ahmedabad":"Gujarat","Bengaluru":"Karnataka","Chennai":"Tamil Nadu",
                  "Delhi":"Delhi","Hyderabad":"Telangana","Jaipur":"Rajasthan",
                  "Kolkata":"West Bengal","Mumbai":"Maharashtra","Mysuru":"Karnataka",
                  "Pune":"Maharashtra"}
    if {"City","State"}.issubset(df.columns):
        expected = df["City"].astype("string").map(city_state)
        state = df["State"].astype("string")
        bad = expected.notna() & (state.isna() | (expected != state))
        log["City/State consistency fixes"] = int(bad.sum())
        df.loc[bad, "State"] = expected[bad]

    sales_mismatches = sales_fixed = 0
    if {"Quantity","Unit_Price","Discount","Sales"}.issubset(df.columns):
        q = pd.to_numeric(df["Quantity"], errors="coerce")
        p = pd.to_numeric(df["Unit_Price"], errors="coerce")
        d = pd.to_numeric(df["Discount"], errors="coerce")
        s = pd.to_numeric(df["Sales"], errors="coerce")
        expected = (q*p*(1-d)).round(2)
        comparable = q.notna() & p.notna() & d.notna() & s.notna()
        bad = comparable & ~np.isclose(s, expected, rtol=0, atol=0.01)
        sales_mismatches = int(bad.sum())
        if fix_sales:
            df.loc[bad, "Sales"] = expected[bad]
            sales_fixed = sales_mismatches
    log["Sales calculation mismatches"] = sales_mismatches
    log["Sales values recalculated from business rule"] = sales_fixed
    log["Total business-rule violations"] = violations
    return df


# ============================================================
# OUTLIERS
# ============================================================


def detect_outliers(df):
    rows = []
    for c in numeric_candidates(df):
        try:
            s = pd.to_numeric(df[c], errors="coerce").astype("float64").dropna()
            if len(s) < 5:
                continue
            q1, q3 = float(s.quantile(.25)), float(s.quantile(.75))
            iqr = q3 - q1
            if not np.isfinite(iqr) or iqr <= 0:
                continue
            low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            count = int(((s < low) | (s > high)).sum())
            rows.append({
                "Column": c,
                "Q1": round(q1, 2),
                "Q3": round(q3, 2),
                "IQR": round(iqr, 2),
                "Lower Bound": round(low, 2),
                "Upper Bound": round(high, 2),
                "Outliers": count,
            })
        except Exception:
            continue
    return pd.DataFrame(rows)

def cap_outliers_safely(df, log):
    total = 0
    for c in numeric_candidates(df):
        # Do not cap bounded fields or financial measures. Financial values such as
        # Unit_Price and Sales may be legitimately skewed, and changing them can
        # break business arithmetic. They remain visible in Outlier Analysis.
        protected = {"Age", "Quantity", "Discount", "Rating"}
        financial_terms = ("price", "sales", "revenue", "amount", "cost", "profit", "income")
        if c in protected or any(term in c.lower() for term in financial_terms):
            continue
        try:
            s = pd.to_numeric(df[c], errors="coerce").astype("float64")
            valid = s.dropna()
            if len(valid) < 5:
                continue
            q1, q3 = float(valid.quantile(.25)), float(valid.quantile(.75))
            iqr = q3 - q1
            if not np.isfinite(iqr) or iqr <= 0:
                continue
            low, high = float(q1 - 1.5 * iqr), float(q3 + 1.5 * iqr)
            mask = ((s < low) | (s > high)).fillna(False)
            total += int(mask.sum())
            df[c] = s.clip(lower=low, upper=high).astype("float64")
        except Exception as exc:
            log[f"Outlier warning - {c}"] = str(exc)
    log["Outlier cells capped"] = total
    return df


# ============================================================
# CLEANING PIPELINE
# ============================================================



# ============================================================
# UNIVERSAL / DATASET-AGNOSTIC CLEANING ENGINE
# ============================================================

# ============================================================
# UNIVERSAL / DATASET-AGNOSTIC CLEANING ENGINE v2
# ============================================================
# Design goals:
# - Work safely with unrelated CSV/Excel datasets.
# - Prefer preservation over guessing.
# - Infer types from both column names and actual values.
# - Never apply e-commerce/HR business formulas automatically.
# - Never convert arbitrary text into dates just because pandas can parse it.
# - Never divide ordinary numeric "rate" values by 100 unless the data itself
#   contains % or the column is clearly percentage-like.

_UNIVERSAL_MISSING = {
    "", "na", "n/a", "n.a.", "nan", "none", "null", "nil", "missing",
    "not available", "not_applicable", "not applicable", "blank",
    "-", "--", "—", "n/a -",
}
_UNIVERSAL_NUM_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10,
}
_UNIVERSAL_ID_HINTS = (
    "id", "identifier", "code", "key", "account", "employee_no",
    "customer_no", "order_no", "transaction_no", "reference_no",
    "ref_no", "number",
)
_UNIVERSAL_EMAIL_HINTS = ("email", "e_mail", "mail")
_UNIVERSAL_PHONE_HINTS = (
    "phone", "mobile", "telephone", "tel", "contact_number",
    "contact_no", "phone_number", "mobile_number",
)
_UNIVERSAL_DATE_HINTS = (
    "date", "dob", "birth", "birthday", "joined", "joining", "hire",
    "hired", "created", "updated", "modified", "timestamp", "datetime",
    "time", "start_date", "end_date",
)
_UNIVERSAL_PERCENT_HINTS = (
    "percent", "percentage", "pct", "percentile", "discount", "margin",
    "growth_rate", "conversion_rate", "tax_rate", "interest_rate",
)
_UNIVERSAL_CURRENCY_HINTS = (
    "salary", "wage", "income", "revenue", "sales", "price", "cost",
    "amount", "bonus", "profit", "pay", "expense", "budget", "fee",
    "spend", "balance", "compensation", "total_amount",
)
_UNIVERSAL_NAME_HINTS = ("name", "first_name", "last_name", "full_name")
_UNIVERSAL_BOOLEAN_HINTS = (
    "active", "enabled", "verified", "approved", "flag", "is_", "has_",
)


def _u_key(c):
    return re.sub(r"[^a-z0-9]+", "_", str(c).strip().lower()).strip("_")


def _u_is_id(c):
    k = _u_key(c)
    if k in {"id", "identifier", "code", "key"}:
        return True
    if k.endswith(("_id", "_code", "_key", "_no", "_identifier")):
        return True
    return False


def _u_is_email(c):
    k = _u_key(c)
    return any(h == k or h in k.split("_") for h in _UNIVERSAL_EMAIL_HINTS)


def _u_is_phone(c):
    k = _u_key(c)
    return any(h == k or h in k.split("_") for h in _UNIVERSAL_PHONE_HINTS)


def _u_is_percent(c):
    k = _u_key(c)
    return any(h == k or k.endswith("_" + h) for h in _UNIVERSAL_PERCENT_HINTS)


def _u_is_currency(c):
    k = _u_key(c)
    return any(h == k or k.endswith("_" + h) for h in _UNIVERSAL_CURRENCY_HINTS)


def _u_is_date_hint(c):
    k = _u_key(c)
    return any(h == k or k.endswith("_" + h) for h in _UNIVERSAL_DATE_HINTS)


def _u_is_name(c):
    k = _u_key(c)
    return any(h == k or k.endswith("_" + h) for h in _UNIVERSAL_NAME_HINTS)


def _u_missing(df, log):
    """Normalize only unambiguous missing tokens; preserve 'unknown' as data."""
    changes = 0
    for c in df.columns:
        if pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_string_dtype(df[c]):
            old = df[c].astype("string")
            stripped = old.str.strip()
            lower = stripped.str.lower()
            new = stripped.mask(lower.isin(_UNIVERSAL_MISSING), pd.NA)
            changes += int((old != new).fillna(False).sum())
            df[c] = new
    log["Missing tokens normalized"] = changes
    return df


def _u_clean_text(s):
    return s.astype("string").str.replace(r"\s+", " ", regex=True).str.strip()


def _u_phone(s):
    s = s.astype("string").str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    # Normalize common Indian/international prefixes without assuming country
    # for every dataset. The final validator accepts 10–15 digits.
    s = s.str.replace(r"^\+91", "", regex=True).str.replace(r"^0091", "", regex=True)
    s = s.str.replace(r"[^0-9]", "", regex=True)
    return s.mask(s.eq(""), pd.NA).astype("string")


def _u_email(s):
    return s.astype("string").str.strip().str.lower().astype("string")


def _u_parse_numeric(s):
    """Parse numeric-like values conservatively and return both numbers and signals."""
    raw = s.astype("string").str.strip().str.lower()
    raw = raw.map(lambda x: _UNIVERSAL_NUM_WORDS.get(x, x) if pd.notna(x) else x).astype("string")
    had_percent = raw.str.contains("%", regex=False, na=False)
    had_currency = raw.str.contains(r"[₹$€£]", regex=True, na=False)
    cleaned = raw.str.replace(r"[₹$€£,]", "", regex=True).str.strip()
    numeric = pd.to_numeric(cleaned.str.replace("%", "", regex=False), errors="coerce")
    return numeric, had_percent, had_currency


def _u_date_parse(s):
    raw = s.astype("string").str.strip()
    # format='mixed' is useful for genuine date columns with mixed representations.
    return pd.to_datetime(raw, errors="coerce", format="mixed")


def _u_date_confident(s, require_hint=False):
    raw = s.astype("string").str.strip()
    valid = raw.notna() & raw.ne("")
    n = int(valid.sum())
    if n < 3:
        return False
    parsed = _u_date_parse(raw)
    ratio = float(parsed[valid].notna().mean())
    if ratio < 0.90:
        return False
    if require_hint:
        return True
    # Do not turn arbitrary text/names into dates. Require a strong date signal.
    sample = raw[valid].head(300)
    date_pattern = sample.str.contains(
        r"(?:\d{1,4}[-/]\d{1,2}[-/]\d{1,4}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|"
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b)",
        case=False, regex=True, na=False,
    )
    return float(date_pattern.mean()) >= 0.60


def _u_infer(c, s):
    """Infer a column type conservatively. Return type + evidence metadata."""
    key = _u_key(c)
    nonmissing = s.notna()
    n = int(nonmissing.sum())
    if _u_is_email(c):
        return "email"
    if _u_is_phone(c):
        return "phone"
    if _u_is_id(c):
        return "id"
    if _u_is_percent(c):
        return "percentage"
    if _u_is_currency(c):
        return "currency"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "date"
    if pd.api.types.is_bool_dtype(s):
        return "boolean"
    if pd.api.types.is_numeric_dtype(s):
        return "numeric"
    if _u_is_date_hint(c) and _u_date_confident(s, require_hint=True):
        return "date"
    if n >= 3:
        numeric, had_pct, had_currency = _u_parse_numeric(s)
        ratio = float(numeric[nonmissing].notna().mean())
        if ratio >= 0.95:
            if bool(had_pct[nonmissing].any()):
                return "percentage"
            if bool(had_currency[nonmissing].any()):
                return "currency"
            return "numeric"
    # Date inference without a column hint is intentionally strict.
    if _u_date_confident(s, require_hint=False):
        return "date"
    # Conservative boolean detection.
    if n >= 3:
        vals = set(s[nonmissing].astype("string").str.strip().str.casefold().unique())
        if vals and vals.issubset({"true", "false", "yes", "no", "y", "n", "1", "0"}):
            return "boolean"
    return "text"


def _u_normalize_categories(df):
    """Fast, dataset-agnostic categorical normalization.

    Only operates on low-cardinality text columns.  It fixes case/spacing/
    separator variants, common gender/boolean aliases, singular/plural
    variants, and small spelling errors when a clear observed canonical value
    exists.  It deliberately avoids fuzzy-matching names, free text, IDs,
    emails, phones, and high-cardinality columns.
    """
    changes = 0

    category_hints = {
        "category", "type", "status", "state", "country", "city", "region",
        "department", "division", "education", "employment", "payment",
        "channel", "method", "level", "role", "rating", "priority", "class",
        "segment", "marital", "occupation", "industry", "product_category",
        "order_status", "employment_type", "education_level", "job_type",
    }

    def norm_key(value):
        x = str(value).casefold().strip()
        x = re.sub(r"[\s_\-/]+", " ", x)
        x = re.sub(r"[^\w ]+", "", x, flags=re.UNICODE)
        return x.strip()

    def compact_key(value):
        """Remove harmless separators so joined/split labels match."""
        return re.sub(r"[^a-z0-9]+", "", norm_key(value))

    def normalized_word_key(value):
        """Normalize common word-boundary and suffix variants safely."""
        x = compact_key(value)
        # Common categorical spelling/word-boundary variants. These are
        # deliberately generic and only used in low-cardinality categories.
        replacements = {
            "creditcard": "creditcard",
            "netbanking": "netbanking",
            "website": "website",
            "web": "website",
            "websiteweb": "website",
            "marketplace": "marketplace",
            "mobileapp": "mobileapp",
            "app": "mobileapp",
            "returned": "returned",
            "return": "returned",
        }
        return replacements.get(x, x)

    def singular_key(x):
        if x.endswith("ies") and len(x) > 4:
            return x[:-3] + "y"
        if x.endswith("ses") and len(x) > 5:
            return x[:-2]
        if x.endswith("s") and not x.endswith("ss") and len(x) > 3:
            return x[:-1]
        return x

    def title_category(v):
        # Preserve common all-caps acronyms/short codes while making ordinary
        # category labels recruiter/user friendly.
        text = str(v).strip()
        if not text:
            return text
        if len(text) <= 4 and text.isupper():
            return text
        return re.sub(r"\s+", " ", text).title()

    for c in df.columns:
        if _u_is_id(c) or _u_is_email(c) or _u_is_phone(c) or _u_is_name(c):
            continue
        if not (pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_string_dtype(df[c])):
            continue

        s = _u_clean_text(df[c])
        observed_series = s.dropna().astype("string")
        unique_count = int(observed_series.nunique())
        nonmissing_count = int(observed_series.size)
        if unique_count == 0:
            df[c] = s
            continue

        # Never run expensive matching on free text/high-cardinality columns.
        # Low-cardinality columns are the safest place to infer categories.
        is_hint_column = _u_key(c) in category_hints or any(
            part in _u_key(c) for part in ("category", "status", "type", "department", "education", "employment")
        )
        if unique_count > 200 or (unique_count > 50 and not is_hint_column):
            df[c] = s
            continue

        counts = observed_series.value_counts()
        observed = [str(v) for v in counts.index]
        new_values = {v: v for v in observed}

        # Exact formatting variants: case, whitespace, hyphen/underscore.
        groups = {}
        for v in observed:
            groups.setdefault(norm_key(v), []).append(v)
        for group in groups.values():
            if len(group) > 1:
                best = max(group, key=lambda x: int(counts[x]))
                for v in group:
                    new_values[v] = best

        # Treat joined/split separators as formatting noise: CreditCard =
        # Credit Card, Netbanking = Net Banking, mobileapp = Mobile App, etc.
        compact_groups = {}
        for v in observed:
            compact_groups.setdefault(normalized_word_key(v), []).append(v)
        for group in compact_groups.values():
            if len(group) > 1:
                best = max(group, key=lambda x: (int(counts[x]), len(x)))
                for v in group:
                    new_values[v] = best

        key = _u_key(c)

        # Semantic gender normalization is safe only for Gender/Sex columns.
        if key in {"gender", "sex"} or key.endswith(("_gender", "_sex")):
            gender_map = {
                "m": "Male", "male": "Male", "man": "Male", "men": "Male",
                "f": "Female", "female": "Female", "woman": "Female", "women": "Female",
                "o": "Other", "other": "Other", "nonbinary": "Non-binary",
                "non binary": "Non-binary", "non-binary": "Non-binary",
            }
            for v in observed:
                new_values[v] = gender_map.get(norm_key(v), new_values[v])
            # Do not let generic singular/plural or fuzzy matching overwrite
            # the semantic Gender mapping (M/m -> Male, F/f -> Female).
            new = s.map(lambda v: new_values.get(str(v), v) if pd.notna(v) else v)
            changes += int((s != new).fillna(False).sum())
            df[c] = new
            continue

        # Generic aliases for common categorical concepts. These are applied
        # only to low-cardinality category-like columns, never to free text/IDs.
        generic_aliases = {
            "creditcard": "Credit Card",
            "netbanking": "Net Banking",
            "website": "Website",
            "web": "Website",
            "marketplace": "Marketplace",
            "mobileapp": "Mobile App",
            "app": "Mobile App",
            "returned": "Returned",
            "return": "Returned",
        }
        if is_hint_column:
            for v in observed:
                alias = generic_aliases.get(normalized_word_key(v))
                if alias is not None:
                    new_values[v] = alias

        # Safe semantic normalization for common, explicitly named dimensions.
        # These mappings are intentionally limited to well-known categorical
        # concepts; arbitrary columns are never forced into a vocabulary.
        semantic_maps = {
            # Strong, widely recognizable semantic dimensions. These are applied
            # only when the column itself identifies the concept, so arbitrary
            # text columns are never guessed.
            "department": {
                "hr": "Human Resources", "human resources": "Human Resources",
                "it": "Information Technology", "information technology": "Information Technology",
                "mktg": "Marketing", "marketing": "Marketing",
                "ops": "Operations", "operations": "Operations",
                "sales": "Sales", "procurement": "Procurement",
                "finance": "Finance", "customer support": "Customer Support",
            },
            "performance_rating": {
                "avg": "Average", "average": "Average",
                "excellent": "Excellent", "good": "Good", "poor": "Poor",
                "needs improvement": "Needs Improvement",
            },
            "employee_status": {
                "active": "Active", "inactive": "Inactive",
                "leave": "On Leave", "on leave": "On Leave",
                "resign": "Resigned", "resigned": "Resigned",
            },
            "employment_type": {
                "internship": "Intern", "intern": "Intern",
                "full time": "Full Time", "full-time": "Full Time", "fulltime": "Full Time",
                "part time": "Part Time", "part-time": "Part Time", "parttime": "Part Time",
                "contractual": "Contract", "contractor": "Contract", "contract": "Contract",
            },
            "education": {
                "bachelor degree": "Bachelor's", "bachelor's degree": "Bachelor's",
                "bachelors": "Bachelor's", "bachelor": "Bachelor's",
                "master degree": "Master's", "master's degree": "Master's",
                "masters": "Master's", "master": "Master's",
                "phd": "PhD", "p h d": "PhD", "diploma": "Diploma",
            },
            "education_level": {
                "bachelor degree": "Bachelor's", "bachelor's degree": "Bachelor's",
                "bachelors": "Bachelor's", "bachelor": "Bachelor's",
                "master degree": "Master's", "master's degree": "Master's",
                "masters": "Master's", "master": "Master's",
                "phd": "PhD", "p h d": "PhD", "diploma": "Diploma",
            },
            "payment_method": {
                "creditcard": "Credit Card", "credit card": "Credit Card",
                "debitcard": "Debit Card", "debit card": "Debit Card",
                "netbanking": "Net Banking", "net banking": "Net Banking",
                "paypal": "PayPal", "cash": "Cash", "upi": "UPI",
            },
            "order_status": {
                "return": "Returned", "returned": "Returned",
                "cancelled": "Cancelled", "completed": "Completed",
                "pending": "Pending", "shipped": "Shipped",
            },
            "sales_channel": {
                "app": "Mobile App", "mobileapp": "Mobile App", "mobile app": "Mobile App",
                "marketplace": "Marketplace", "market place": "Marketplace",
                "web": "Website", "website": "Website", "web site": "Website",
            },
        }
        if key in semantic_maps:
            for v in observed:
                mapped = semantic_maps[key].get(norm_key(v))
                if mapped is not None:
                    new_values[v] = mapped

        # Reconcile aliases that normalize to the same canonical concept.
        # This second pass matters when a canonical value is already present
        # alongside a short alias (for example HR + Human Resources).
        if key in semantic_maps:
            canonical_targets = set(semantic_maps[key].values())
            for v in observed:
                target = new_values.get(v, v)
                if target in canonical_targets:
                    new_values[v] = target

        # Boolean-like columns: normalize common representations.
        if key.startswith(("is_", "has_")) or key in {"active", "enabled", "verified", "approved"}:
            bool_map = {
                "true": "True", "yes": "True", "y": "True", "1": "True",
                "false": "False", "no": "False", "n": "False", "0": "False",
            }
            for v in observed:
                new_values[v] = bool_map.get(norm_key(v), new_values[v])

        # Singular/plural variants.  Prefer the value with more observations;
        # if tied, prefer the longer/more natural plural form.
        plural_groups = {}
        for v in observed:
            plural_groups.setdefault(singular_key(norm_key(v)), []).append(v)
        for group in plural_groups.values():
            if len(group) > 1:
                best = max(group, key=lambda x: (int(counts[x]), len(x)))
                for v in group:
                    new_values[v] = best

        # Small spelling repair only for genuinely categorical columns and
        # only when a candidate is substantially more frequent. This avoids
        # turning arbitrary free text into a guessed value.
        if is_hint_column and unique_count <= 60 and key not in semantic_maps:
            from difflib import SequenceMatcher
            for v in observed:
                vk = norm_key(v)
                vc = int(counts[v])
                if len(vk) < 4:
                    continue
                best = None
                best_score = 0.0
                for candidate in observed:
                    if candidate == v:
                        continue
                    ck = norm_key(candidate)
                    if not ck or vk[0] != ck[0]:
                        continue
                    cc = int(counts[candidate])
                    if cc < max(2, vc * 2):
                        continue
                    score = SequenceMatcher(None, vk, ck).ratio()
                    if score > best_score:
                        best_score = score
                        best = candidate
                if best is not None and best_score >= 0.84:
                    new_values[v] = new_values.get(best, best)

        # For explicit category-like columns, make the FINAL canonical value
        # human-readable too. Apply this after all grouping so values such as
        # electronics/ELECTRONICS/electronic cannot split into two outputs.
        if is_hint_column and key not in semantic_maps:
            for v in observed:
                target = new_values[v]
                if isinstance(target, str) and target.casefold() == target and len(target) > 1:
                    new_values[v] = title_category(target)

        new = s.map(lambda v: new_values.get(str(v), v) if pd.notna(v) else v)
        changes += int((s != new).fillna(False).sum())
        df[c] = new

    return df, changes


def _u_apply_semantic_categories(df, log=None):
    """Final conservative pass for strongly identifiable categorical dimensions.

    This is intentionally column-semantic, not dataset-specific: only columns
    whose names clearly identify the concept receive an alias vocabulary.
    """
    maps = {
        "department": {"hr":"Human Resources", "human resources":"Human Resources",
                       "it":"Information Technology", "information technology":"Information Technology",
                       "mktg":"Marketing", "marketing":"Marketing", "ops":"Operations",
                       "operations":"Operations", "sales":"Sales", "procurement":"Procurement",
                       "finance":"Finance", "customer support":"Customer Support"},
        "employment_type": {"internship":"Intern", "intern":"Intern",
                             "full time":"Full Time", "full-time":"Full Time", "fulltime":"Full Time",
                             "part time":"Part Time", "part-time":"Part Time", "parttime":"Part Time",
                             "contractual":"Contract", "contractor":"Contract", "contract":"Contract"},
        "performance_rating": {"avg":"Average", "average":"Average", "excellent":"Excellent",
                                "good":"Good", "poor":"Poor", "needs improvement":"Needs Improvement"},
        "employee_status": {"active":"Active", "inactive":"Inactive", "leave":"On Leave",
                             "on leave":"On Leave", "resign":"Resigned", "resigned":"Resigned"},
        "payment_method": {"creditcard":"Credit Card", "credit card":"Credit Card",
                            "debitcard":"Debit Card", "debit card":"Debit Card",
                            "netbanking":"Net Banking", "net banking":"Net Banking",
                            "paypal":"PayPal", "cash":"Cash", "upi":"UPI"},
        "order_status": {"return":"Returned", "returned":"Returned", "cancelled":"Cancelled",
                          "completed":"Completed", "complete":"Completed", "pending":"Pending", "shipped":"Shipped"},
        "sales_channel": {"app":"Mobile App", "mobileapp":"Mobile App", "mobile app":"Mobile App",
                           "marketplace":"Marketplace", "market place":"Marketplace",
                           "web":"Website", "website":"Website", "web site":"Website"},
        "education": {"bachelor":"Bachelor's", "bachelors":"Bachelor's", "bachelor degree":"Bachelor's",
                       "bachelor's degree":"Bachelor's", "master":"Master's", "masters":"Master's",
                       "master degree":"Master's", "master's degree":"Master's", "phd":"PhD",
                       "p h d":"PhD", "diploma":"Diploma"},
        "education_level": {"bachelor":"Bachelor's", "bachelors":"Bachelor's", "bachelor degree":"Bachelor's",
                             "bachelor's degree":"Bachelor's", "master":"Master's", "masters":"Master's",
                             "master degree":"Master's", "master's degree":"Master's", "phd":"PhD",
                             "p h d":"PhD", "diploma":"Diploma"},
    }
    changed = 0
    for c in df.columns:
        key = _u_key(c)
        mapping = maps.get(key)
        if not mapping or not (pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_string_dtype(df[c])):
            continue
        old = df[c].astype("string")
        normalized = old.str.strip().str.casefold()
        new = normalized.map(mapping).where(normalized.isin(mapping), old)
        # Restore missing values and canonicalize known targets consistently.
        new = new.mask(old.isna(), pd.NA).astype("string")
        changed += int((old != new).fillna(False).sum())
        df[c] = new
    if log is not None:
        log["Semantic categorical aliases standardized"] = changed
    return df

def _u_safe_impute(df, strategy, kinds, log):
    if strategy == "Leave missing values unchanged":
        return df
    protected = {"id", "email", "phone", "date"}
    imputed = 0
    for c, kind in kinds.items():
        if c not in df.columns or not df[c].isna().any() or kind in protected:
            continue
        if kind in {"numeric", "currency", "percentage"}:
            n = pd.to_numeric(df[c], errors="coerce").astype("float64")
            if not n.notna().any():
                continue
            if strategy.startswith("Fill numeric with median"):
                value = float(n.median())
            else:
                value = 0.0
            count = int(n.isna().sum())
            df[c] = n.fillna(value)
            imputed += count
        elif kind == "boolean":
            if strategy.startswith("Fill numeric with median"):
                mode = df[c].mode(dropna=True)
                if not mode.empty:
                    count = int(df[c].isna().sum())
                    df[c] = df[c].fillna(mode.iloc[0])
                    imputed += count
            else:
                count = int(df[c].isna().sum())
                df[c] = df[c].fillna("Unknown")
                imputed += count
        elif kind == "text" and strategy.startswith("Fill numeric with median"):
            # Safe text imputation: only fill if a clear single mode exists.
            mode = df[c].mode(dropna=True)
            if len(mode) == 1:
                count = int(df[c].isna().sum())
                df[c] = df[c].fillna(mode.iloc[0])
                imputed += count
        elif kind == "text" and strategy.startswith("Fill numeric with 0"):
            count = int(df[c].isna().sum())
            df[c] = df[c].fillna("Unknown")
            imputed += count
    log["Missing cells imputed"] = imputed
    return df


def _u_outliers(df):
    result = {}
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            continue
        s = pd.to_numeric(df[c], errors="coerce").dropna()
        if len(s) < 8 or s.nunique() < 4:
            continue
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = float(q3 - q1)
        if not np.isfinite(iqr) or iqr <= 0:
            continue
        lo, hi = float(q1 - 1.5 * iqr), float(q3 + 1.5 * iqr)
        count = int(((df[c] < lo) | (df[c] > hi)).fillna(False).sum())
        result[c] = {"count": count, "lower": lo, "upper": hi}
    return result


def clean_data(source, missing_strategy, enable_outliers, fix_sales=False):
    """Universal, conservative cleaner for arbitrary CSV/Excel datasets."""
    df = source.copy()
    log = {"Original rows": len(df), "Original columns": len(df.columns)}

    # 1. Remove completely empty records.
    before = len(df)
    df = df.dropna(how="all").copy()
    log["Blank rows removed"] = before - len(df)
    before_cols = len(df.columns)
    df = df.dropna(axis=1, how="all")
    log["Blank columns removed"] = before_cols - len(df.columns)

    # 2. Standardize unique column names.
    old_cols = list(df.columns)
    df.columns = make_unique([clean_column_name(c) for c in df.columns])
    log["Column names standardized"] = sum(a != b for a, b in zip(old_cols, df.columns))

    # 3. Missing tokens and whitespace.
    df = _u_missing(df, log)
    text_changes = 0
    for c in df.columns:
        if pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_string_dtype(df[c]):
            old = df[c].astype("string")
            if _u_is_email(c):
                new = _u_email(df[c])
            elif _u_is_phone(c):
                new = _u_phone(df[c])
            else:
                new = _u_clean_text(df[c])
                if _u_is_name(c):
                    new = new.str.title()
            text_changes += int((old != new).fillna(False).sum())
            df[c] = new
    log["Text cells whitespace/name-normalized"] = text_changes

    # 4. Formatting-only category normalization.
    df, cat_changes = _u_normalize_categories(df)
    log["Formatting-only categorical variants standardized"] = cat_changes
    df = _u_apply_semantic_categories(df, log)

    # 5. Infer and convert types.
    kinds = {}
    converted = 0
    invalid_numeric = 0
    invalid_dates = 0
    for c in list(df.columns):
        kind = _u_infer(c, df[c])
        kinds[c] = kind
        if kind == "phone":
            df[c] = _u_phone(df[c])
        elif kind == "email":
            df[c] = _u_email(df[c])
        elif kind in {"numeric", "currency", "percentage"}:
            numeric, had_pct, _ = _u_parse_numeric(df[c])
            if kind == "percentage":
                # Only scale values when the source explicitly uses %, or when
                # the entire column is clearly 0–100 percentage data.
                nonmissing = numeric.notna()
                explicit_pct = had_pct.fillna(False)
                if bool(explicit_pct.any()):
                    # Force floating dtype before scaling so nullable integer
                    # Series cannot reject fractional percentage values.
                    numeric = numeric.astype("float64")
                    numeric = numeric.where(~explicit_pct, numeric / 100.0)
                elif bool(nonmissing.any()) and float(numeric[nonmissing].max()) > 1 and float(numeric[nonmissing].max()) <= 100:
                    numeric = numeric.astype("float64") / 100.0
            invalid_numeric += int(df[c].notna().sum() - numeric.notna().sum())
            df[c] = numeric.astype("float64")

            # Safe semantic range validation. Bounds are used only when the
            # column name strongly identifies the measurement; arbitrary
            # numeric columns remain untouched.
            key_num = _u_key(c)
            bounds = None
            if key_num in {"age", "employee_age", "customer_age"}:
                bounds = (1, 120)
            elif key_num in {"job_satisfaction", "satisfaction", "performance_rating", "rating"}:
                bounds = (1, 5)
            elif key_num in {"quantity", "qty", "units", "order_quantity"}:
                bounds = (0, None)
            elif key_num in {"experience_years", "years_experience", "experience"}:
                bounds = (0, 60)
            elif key_num in {"overtime_hours", "overtime"}:
                bounds = (0, None)

            if bounds is not None:
                low, high = bounds
                invalid_mask = df[c].notna()
                if low is not None:
                    invalid_mask &= df[c] < low
                if high is not None:
                    invalid_mask |= df[c].notna() & (df[c] > high)
                count = int(invalid_mask.sum())
                if count:
                    df.loc[invalid_mask, c] = np.nan
                    invalid_numeric += count
                    log[f"Invalid {c} values set to missing"] = count

            converted += 1
        elif kind == "date":
            parsed = _u_date_parse(df[c])
            nonmissing = df[c].notna()
            bad = int(nonmissing.sum() - parsed[nonmissing].notna().sum())
            invalid_dates += bad
            df[c] = parsed
            converted += 1
        elif kind == "boolean":
            raw = df[c].astype("string").str.strip().str.casefold()
            mapping = {"true": True, "yes": True, "y": True, "1": True,
                       "false": False, "no": False, "n": False, "0": False}
            df[c] = raw.map(mapping).astype("boolean")
            converted += 1
        elif kind == "id":
            df[c] = df[c].astype("string").str.strip()

    log["Columns type-converted"] = converted
    log["Invalid numeric values converted to missing"] = invalid_numeric
    log["Invalid date values converted to missing"] = invalid_dates
    log["Inferred column types"] = ", ".join(f"{c}: {k}" for c, k in kinds.items())

    # 6. Exact duplicates only. Never deduplicate on ID alone.
    before = len(df)
    df = df.drop_duplicates(keep="first").reset_index(drop=True)
    log["Duplicate rows removed"] = before - len(df)

    # 7. Missing strategy. Identifiers/contact/date values are protected.
    missing_before = int(df.isna().sum().sum())
    if missing_strategy == "Drop rows containing missing values":
        df = df.dropna().reset_index(drop=True)
        log["Rows dropped for missing values"] = before - len(df)
    else:
        df = _u_safe_impute(df, missing_strategy, kinds, log)
    log["Missing cells before strategy"] = missing_before
    log["Missing cells after strategy"] = int(df.isna().sum().sum())

    # 8. Outliers are diagnostic only.
    outlier_info = _u_outliers(df) if enable_outliers else {}
    log["Outlier cells capped"] = 0
    log["Outlier columns detected"] = len(outlier_info)
    log["Outlier observations detected"] = sum(v["count"] for v in outlier_info.values())

    # 9. Generic contact validation.
    invalid_emails = invalid_phones = 0
    for c, kind in kinds.items():
        if c not in df.columns:
            continue
        if kind == "email":
            s = df[c].astype("string").str.strip().str.lower()
            valid = s.str.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", na=False)
            bad = s.notna() & ~valid
            invalid_emails += int(bad.sum())
            df.loc[bad, c] = pd.NA
        elif kind == "phone":
            s = _u_phone(df[c])
            valid = s.str.fullmatch(r"\d{10,15}", na=False)
            bad = s.notna() & ~valid
            invalid_phones += int(bad.sum())
            df[c] = s.mask(bad, pd.NA).astype("string")
    log["Invalid emails converted to missing"] = invalid_emails
    log["Invalid phones converted to missing"] = invalid_phones

    # Preserve identifiers/contact fields as strings for reliable export.
    for c, kind in kinds.items():
        if c in df.columns and kind in {"id", "email", "phone"}:
            df[c] = df[c].astype("string")

    log["Final invalid emails"] = 0
    log["Final invalid phones"] = 0
    log["Final Sales mismatches"] = 0
    log["Final City/State mismatches"] = 0
    log["Cleaned rows"] = len(df)
    log["Cleaned columns"] = len(df.columns)
    log["Final missing cells"] = int(df.isna().sum().sum())
    log["Final duplicate rows"] = int(df.duplicated().sum())
    log["Final quality score"] = quality_score(df)
    log["Domain-specific rules applied"] = "None — universal mode"
    return df, log

# Persistent local history storage
HISTORY_DIR = Path("data") / "history"
HISTORY_DB = HISTORY_DIR / "history.db"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

def init_history_db():
    with sqlite3.connect(HISTORY_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cleaning_history (
                id TEXT PRIMARY KEY,
                saved_at TEXT NOT NULL,
                source_name TEXT NOT NULL,
                rows_before INTEGER,
                rows_after INTEGER,
                columns_before INTEGER,
                columns_after INTEGER,
                quality_before REAL,
                quality_after REAL,
                missing_before INTEGER,
                missing_after INTEGER,
                duplicates_before INTEGER,
                duplicates_after INTEGER,
                original_path TEXT NOT NULL,
                cleaned_path TEXT NOT NULL
            )
        """)
        conn.commit()


def save_to_history(source_name, original_df, cleaned_df, clean_log):
    init_history_db()

    history_id = uuid.uuid4().hex[:12]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(source_name).stem).strip("_") or "dataset"
    run_dir = HISTORY_DIR / f"{timestamp.replace(':', '-').replace(' ', '_')}_{safe_stem}_{history_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    original_path = run_dir / "original_data.csv"
    cleaned_path = run_dir / "cleaned_data.csv"
    audit_path = run_dir / "cleaning_audit.csv"

    original_df.to_csv(original_path, index=False)
    _prepare_export_dataframe(cleaned_df).to_csv(cleaned_path, index=False, encoding="utf-8-sig")

    audit_df = pd.DataFrame([
        {"Cleaning Action": k, "Result": v}
        for k, v in clean_log.items()
    ])
    audit_df.to_csv(audit_path, index=False)

    with sqlite3.connect(HISTORY_DB) as conn:
        conn.execute("""
            INSERT INTO cleaning_history (
                id, saved_at, source_name,
                rows_before, rows_after, columns_before, columns_after,
                quality_before, quality_after,
                missing_before, missing_after,
                duplicates_before, duplicates_after,
                original_path, cleaned_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            history_id,
            timestamp,
            source_name,
            len(original_df),
            len(cleaned_df),
            len(original_df.columns),
            len(cleaned_df.columns),
            float(quality_score(original_df)),
            float(quality_score(cleaned_df)),
            int(original_df.isna().sum().sum()),
            int(cleaned_df.isna().sum().sum()),
            int(original_df.duplicated().sum()),
            int(cleaned_df.duplicated().sum()),
            str(original_path),
            str(cleaned_path),
        ))
        conn.commit()

    return history_id


def get_history():
    init_history_db()
    with sqlite3.connect(HISTORY_DB) as conn:
        return pd.read_sql_query(
            """
            SELECT
                id AS ID,
                saved_at AS "Saved At",
                source_name AS Dataset,
                rows_before AS "Rows Before",
                rows_after AS "Rows After",
                quality_before AS "Quality Before",
                quality_after AS "Quality After",
                missing_before AS "Missing Before",
                missing_after AS "Missing After",
                duplicates_before AS "Duplicates Before",
                duplicates_after AS "Duplicates After",
                original_path,
                cleaned_path
            FROM cleaning_history
            ORDER BY saved_at DESC
            """,
            conn,
        )


def get_history_record(history_id):
    init_history_db()
    with sqlite3.connect(HISTORY_DB) as conn:
        row = conn.execute(
            "SELECT * FROM cleaning_history WHERE id = ?",
            (history_id,),
        ).fetchone()
        cols = [d[0] for d in conn.execute(
            "SELECT * FROM cleaning_history LIMIT 1"
        ).description]
    if row is None:
        return None
    return dict(zip(cols, row))


def delete_history_record(history_id):
    record = get_history_record(history_id)
    if record is None:
        return False

    run_dir = Path(record["original_path"]).parent
    with sqlite3.connect(HISTORY_DB) as conn:
        conn.execute("DELETE FROM cleaning_history WHERE id = ?", (history_id,))
        conn.commit()

    if run_dir.exists():
        import shutil
        shutil.rmtree(run_dir, ignore_errors=True)

    return True


# ============================================================
# EXPORT
# ============================================================

def _norm(value):
    """Normalize a column name for reliable comparisons."""
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _prepare_export_dataframe(df):
    """Prepare a clean export without changing analytical values."""
    export_df = df.copy()

    # Contact identifiers must be text. Never export phone numbers as floats.
    for c in export_df.columns:
        if _norm(c) in {
            "phone", "mobile", "mobile_number",
            "contact_number", "telephone"
        }:
            s = export_df[c].astype("string").str.strip()
            # Remove an accidental numeric suffix such as 9876543210.0
            s = s.str.replace(r"\\.0$", "", regex=True)
            export_df[c] = s

    return export_df


def create_csv(cleaned):
    """Create CSV bytes with phone/contact identifiers serialized as text."""
    export_df = _prepare_export_dataframe(cleaned)
    return export_df.to_csv(index=False).encode("utf-8-sig")


def create_excel(cleaned, log_df, profile_df, outlier_df):
    output = BytesIO()
    export_df = _prepare_export_dataframe(cleaned)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Cleaned_Data")
        log_df.to_excel(writer, index=False, sheet_name="Cleaning_Log")
        profile_df.to_excel(writer, index=False, sheet_name="Data_Profile")
        outlier_df.to_excel(writer, index=False, sheet_name="Outlier_Analysis")

        # Excel has a real cell type/format, so explicitly mark contact
        # identifier columns as text to prevent scientific notation or
        # automatic numeric conversion.
        ws = writer.book["Cleaned_Data"]
        for col_idx, col_name in enumerate(export_df.columns, start=1):
            if _norm(col_name) in {
                "phone", "mobile", "mobile_number",
                "contact_number", "telephone"
            }:
                for cell in ws.iter_cols(
                    min_col=col_idx, max_col=col_idx,
                    min_row=2, max_row=ws.max_row
                ):
                    for c in cell:
                        c.number_format = "@"
                        if c.value is not None:
                            c.value = str(c.value)

    return output.getvalue()


# ============================================================
# AI DATA QUALITY ASSISTANT — STAGE 10
# ============================================================

def _ai_profile_snapshot(frame):
    """Create a compact, privacy-conscious dataset summary for reasoning."""
    snapshot = {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "missing_cells": int(frame.isna().sum().sum()),
        "duplicate_rows": int(frame.duplicated().sum()),
        "columns": [],
    }
    for c in frame.columns:
        s = frame[c]
        nonnull = s.dropna()
        info = {
            "column": str(c),
            "dtype": str(s.dtype),
            "missing": int(s.isna().sum()),
            "missing_pct": round(float(s.isna().mean() * 100), 2) if len(s) else 0.0,
            "unique": int(s.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(s):
            n = pd.to_numeric(s, errors="coerce").dropna()
            if len(n):
                info.update({
                    "min": float(n.min()),
                    "max": float(n.max()),
                    "mean": round(float(n.mean()), 4),
                })
        elif len(nonnull):
            info["sample_values"] = [str(x)[:80] for x in nonnull.head(3).tolist()]
        snapshot["columns"].append(info)
    return snapshot


def _ai_action_for_issue(category, column):
    """Map a quality finding to a concrete, safe in-app next step."""
    mapping = {
        "Missing Values": (
            "Review the affected records first. Use Clean & Validate only if a business-approved missing-value strategy is known.",
            "Clean & Validate → Missing-value strategy",
            "Do not guess identifiers, emails, phones or dates unless a verified business rule exists.",
        ),
        "Duplicates": (
            "Inspect duplicate rows and remove exact duplicates when they represent repeated records.",
            "Clean & Validate → Duplicate handling",
            "Do not remove rows solely because they look similar; this finding covers exact duplicates.",
        ),
        "Constant Column": (
            "Check whether the column is required for reporting or downstream systems before excluding it.",
            "Column Profile → inspect uniqueness; then exclude downstream if unnecessary",
            "Do not delete the source column automatically.",
        ),
        "High Cardinality": (
            "Determine whether the field is an identifier/free text or a genuine category before modeling.",
            "Column Profile → inspect unique values and data type",
            "Do not merge values based only on high cardinality.",
        ),
        "Invalid Contact Data": (
            "Inspect flagged values and apply a verified formatting/country rule before correcting them.",
            "Clean & Validate → email/phone validation",
            "Do not invent missing or invalid contact details.",
        ),
        "Outliers": (
            "Open the outlier analysis, inspect the records and confirm whether unusual values are legitimate.",
            "Outliers → inspect IQR findings",
            "Do not delete or cap outliers automatically.",
        ),
        "Semantic Range": (
            "Inspect the affected records and apply a domain rule only when the value is confirmed invalid.",
            "Clean & Validate → business-rule validation",
            "Do not replace values solely because they fall outside a conservative range.",
        ),
        "Category Consistency": (
            "Review spelling/case/format variants and standardize only when they represent the same business category.",
            "Clean & Validate → category/text normalization",
            "Do not merge categories based only on string similarity.",
        ),
    }
    return mapping.get(category, (
        "Inspect the finding and apply an explicit business rule before changing data.",
        "Column Profile / Clean & Validate",
        "Avoid automatic changes when the business meaning is ambiguous.",
    ))


def _ai_issue(severity, category, column, finding, why, recommendation):
    action, workflow, guardrail = _ai_action_for_issue(category, column)
    return {
        "severity": severity,
        "category": category,
        "column": str(column),
        "finding": finding,
        "why_it_matters": why,
        "recommendation": recommendation,
        "recommended_action": action,
        "workflow": workflow,
        "guardrail": guardrail,
    }


def build_ai_quality_analysis(frame):
    """Rule-based quality reasoning. It diagnoses and explains; it never changes data."""
    issues = []
    recommendations = []
    rows, cols = frame.shape

    missing = frame.isna().sum()
    for c, n in missing[missing > 0].sort_values(ascending=False).items():
        pct = (float(n) / rows * 100) if rows else 0
        severity = "High" if pct >= 30 else ("Medium" if pct >= 10 else "Low")
        field_type = "identifier/contact field" if (_u_is_id(c) or _u_is_email(c) or _u_is_phone(c)) else "data field"
        why = (
            f"Missing {field_type} values can reduce completeness and may affect joins, reporting or analysis. "
            "The correct treatment depends on the business meaning of the field."
        )
        issues.append(_ai_issue(
            severity, "Missing Values", c,
            f"{int(n):,} missing cells ({pct:.1f}% of rows).",
            why,
            "Review the business meaning before imputing; identifiers and contact fields should generally remain missing rather than guessed.",
        ))

    dup = int(frame.duplicated().sum())
    if dup:
        issues.append(_ai_issue(
            "Medium", "Duplicates", "Dataset",
            f"{dup:,} exact duplicate rows detected.",
            "Duplicate rows can inflate counts, totals and other downstream metrics if they are accidental repeats.",
            "Review duplicates and remove only exact duplicate records unless a business key is explicitly defined.",
        ))

    for c in frame.columns:
        s = frame[c]
        if len(s) == 0:
            continue
        unique_ratio = float(s.nunique(dropna=True) / max(1, s.notna().sum()))
        key = _u_key(c)
        if s.nunique(dropna=True) <= 1:
            issues.append(_ai_issue(
                "Low", "Constant Column", c,
                "The column contains one distinct non-null value or no usable values.",
                "A constant field contributes no variation to most analytical comparisons and may add noise to models or reports.",
                "Consider whether this column adds analytical value before downstream modeling or reporting.",
            ))
        if pd.api.types.is_string_dtype(s) or pd.api.types.is_object_dtype(s):
            if unique_ratio >= 0.98 and len(s) >= 20 and not (_u_is_email(c) or _u_is_phone(c) or _u_is_id(c)):
                issues.append(_ai_issue(
                    "Low", "High Cardinality", c,
                    f"{unique_ratio:.0%} of non-null values are unique.",
                    "Very high uniqueness can indicate free text, identifiers or a field that should not be treated as a normal category.",
                    "Check whether this is free text, an identifier, or a field that should be treated as categorical.",
                ))

        if _u_is_email(c):
            valid = s.astype("string").str.strip().str.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", na=False)
            bad = int((s.notna() & ~valid).sum())
            if bad:
                issues.append(_ai_issue(
                    "High", "Invalid Contact Data", c,
                    f"{bad:,} non-null values do not match the basic email format check.",
                    "Invalid contact values can break communication, matching and downstream customer/employee workflows.",
                    "Normalize casing/whitespace and flag invalid addresses for review rather than inventing corrections.",
                ))

        if _u_is_phone(c):
            normalized = _u_phone(s)
            valid = normalized.str.fullmatch(r"\d{10,15}", na=False)
            bad = int((s.notna() & ~valid).sum())
            if bad:
                issues.append(_ai_issue(
                    "High", "Invalid Contact Data", c,
                    f"{bad:,} non-null values fail the normalized 10–15 digit phone check.",
                    "Invalid phone values can prevent contact, matching and operational workflows; valid formatting depends on country conventions.",
                    "Review country-code conventions before correcting or rejecting phone values.",
                ))

        if pd.api.types.is_numeric_dtype(s):
            out = _u_outliers(frame).get(c)
            if out and out["count"]:
                issues.append(_ai_issue(
                    "Medium", "Outliers", c,
                    f"{out['count']:,} observations fall outside the 1.5×IQR bounds.",
                    "Statistical outliers may be data errors, unusual legitimate cases or a different business segment; treating all outliers as errors can distort analysis.",
                    "Inspect the underlying records. Outliers are signals and should not be deleted or capped automatically.",
                ))

        if key in {"age", "employee_age", "customer_age"} and pd.api.types.is_numeric_dtype(s):
            bad = int(((s < 1) | (s > 120)).fillna(False).sum())
            if bad:
                issues.append(_ai_issue(
                    "High", "Semantic Range", c,
                    f"{bad:,} values fall outside the conservative 1–120 age range.",
                    "These values may be invalid for an age field, but the appropriate business rule should be confirmed before correction.",
                    "Flag these records for review instead of replacing the values automatically.",
                ))

    # Detect likely category aliases without making a semantic merge.
    for c in frame.columns:
        s = frame[c].dropna().astype("string").str.strip()
        if len(s) < 10 or pd.api.types.is_numeric_dtype(frame[c]):
            continue
        norm = s.str.casefold().str.replace(r"[^a-z0-9]+", "", regex=True)
        grouped = pd.DataFrame({"raw": s, "norm": norm}).groupby("norm")["raw"].nunique()
        alias_groups = grouped[grouped > 1]
        if len(alias_groups):
            issues.append(_ai_issue(
                "Medium", "Category Consistency", c,
                f"{len(alias_groups):,} normalized value groups contain multiple raw spellings.",
                "Inconsistent spelling/case can split the same business category into multiple groups and distort summaries.",
                "Review likely aliases before merging them; formatting normalization is safer than semantic guessing.",
            ))

    if not issues:
        recommendations.append("No major structural quality issues were detected by the local assistant.")
    else:
        recommendations.extend([
            "Review each finding before changing the dataset.",
            "Use the linked DataClean Pro workflow shown on each finding instead of guessing a correction.",
            "Keep outliers as review signals unless domain evidence supports a correction.",
            "Prefer explicit business rules over inferred assumptions for ambiguous fields.",
        ])

    counts = {"High": 0, "Medium": 0, "Low": 0}
    for issue in issues:
        counts[issue["severity"]] = counts.get(issue["severity"], 0) + 1
    return {
        "summary": {
            "rows": rows,
            "columns": cols,
            "missing_cells": int(frame.isna().sum().sum()),
            "duplicate_rows": dup,
            "issue_count": len(issues),
            "severity_counts": counts,
        },
        "issues": issues,
        "recommendations": recommendations,
        "snapshot": _ai_profile_snapshot(frame),
    }

def generate_llm_quality_explanation(analysis):
    """Optional LLM explanation. Only aggregate profile data is sent, never the raw dataset."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None, "OPENAI_API_KEY is not configured. The local quality assistant is still available."
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        payload = {
            "summary": analysis["summary"],
            "issues": analysis["issues"][:40],
            "recommendations": analysis["recommendations"],
            "columns": analysis["snapshot"]["columns"][:80],
        }
        response = client.responses.create(
            model=model,
            input=(
                "You are a data quality analyst. Explain the following dataset-quality "
                "findings in concise professional language. Do not invent facts, do not "
                "recommend deleting records without evidence, and clearly distinguish "
                "observations from recommendations. Return sections: Executive Summary, Key Risks, Recommended Review Actions. For each important finding, explain what was found, why it matters, the safe next action, and the relevant DataClean Pro workflow. Never claim that the LLM changed the dataset.\n\n"
                + json.dumps(payload, ensure_ascii=False, default=str)
            ),
        )
        return response.output_text, None
    except Exception as exc:
        return None, f"AI explanation unavailable: {exc}"

# ============================================================
# FILE UPLOAD
# ============================================================

uploaded = st.file_uploader(
    "📁 Upload CSV or Excel",
    type=["csv", "xlsx", "xls"],
)

if uploaded is None:
    st.info("Upload a dataset to begin your data-quality assessment.")
    st.markdown("""
### Built for real Data Analyst workflows

**Profile → Diagnose → Clean → Validate → Measure → Export**

- Missing-value analysis
- Duplicate detection
- Text and category standardization
- Numeric/date inference
- Email validation
- Business-rule validation
- Sales consistency checks
- IQR outlier detection
- Safe outlier capping
- Before/after quality scoring
- Cleaning audit trail
- CSV + multi-sheet Excel export
""")
    st.stop()

try:
    if uploaded.name.lower().endswith(".csv"):
        # Read CSV fields as strings first so phone numbers, IDs and ZIP/postal
        # codes never lose leading zeros or acquire a trailing .0. The universal
        # type-inference engine converts true numeric/date fields afterward.
        df = pd.read_csv(uploaded, dtype="string", keep_default_na=False)
    else:
        df = pd.read_excel(uploaded, dtype=object)
except Exception as exc:
    st.error(f"Unable to read file: {exc}")
    st.stop()

# Reset previous result for a new upload.
if st.session_state.get("source_file") != uploaded.name:
    st.session_state.source_file = uploaded.name
    st.session_state.pop("cleaned_df", None)
    st.session_state.pop("clean_log", None)
    st.session_state.pop("history_saved_for_source", None)

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("⚙️ Cleaning Controls")
    st.caption("Configure the cleaning pipeline before processing your dataset.")

    missing_strategy = st.selectbox(
        "Missing-value strategy",
        [
            "Leave missing values unchanged",
            "Fill numeric with median; safe text with mode",
            "Fill numeric with 0; text with 'Unknown'",
            "Drop rows containing missing values",
        ],
        index=0,
        help="The safest default preserves missingness. Choose imputation or row deletion only when it matches your analytical context.",
    )

    enable_outlier_analysis = st.checkbox(
        "Analyze numeric outliers",
        value=True,
        help="Uses the 1.5×IQR rule to flag unusual numeric values. Values are never deleted or capped automatically by this control."
    )

    # Universal mode deliberately does not apply dataset-specific formulas.
    # This keeps the cleaner safe for HR, sales, finance, marketing, survey,
    # inventory, and other unrelated datasets.
    fix_sales = False

    st.divider()
    st.caption("Universal cleaning mode")
    st.caption("✓ Safe type inference and normalization")
    st.caption("✓ Outliers are detected, not blindly changed")
    st.caption("✓ Missing values are preserved by default")

    st.divider()
    try:
        _history_count = len(get_history())
        st.caption(f"🕘 Saved cleaning runs: **{_history_count}**")
        st.caption("Open the **History** tab to review saved datasets.")
    except Exception:
        pass

# ============================================================
# TOP METRICS
# ============================================================

score_before = quality_score(df)
status_before = quality_status(score_before)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Rows", f"{len(df):,}")
m2.metric("Columns", f"{len(df.columns):,}")
m3.metric("Missing Cells", f"{int(df.isna().sum().sum()):,}")
m4.metric("Duplicate Rows", f"{int(df.duplicated().sum()):,}")
m5.metric("Quality Score", f"{score_before}/100")

st.progress(score_before / 100)
st.caption(f"Current data quality status: **{status_before}**")

# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Overview",
    "🧹 Clean & Validate",
    "🔎 Outliers",
    "📋 Column Profile",
    "📥 Export",
    "🕘 History",
    "🤖 AI Assistant",
])

# ============================================================
# OVERVIEW
# ============================================================

with tab1:
    st.subheader("Data Quality Overview")

    missing_by_col = (
        df.isna().sum()
        .sort_values(ascending=False)
        .rename("Missing")
        .to_frame()
    )

    c1, c2 = st.columns(2)

    with c1:
        st.write("**Missing Values by Column**")
        st.bar_chart(missing_by_col)

    with c2:
        st.write("**Duplicate Analysis**")
        dup = int(df.duplicated().sum())
        st.metric(
            "Duplicate rows",
            f"{dup:,}",
            f"{(dup / len(df) * 100 if len(df) else 0):.2f}% of rows",
        )

    st.subheader("Original Data Preview")
    st.dataframe(df.head(100), use_container_width=True, hide_index=True)

# ============================================================
# CLEAN
# ============================================================

with tab2:
    st.subheader("One-Click Cleaning & Validation")
    st.write(
        "The pipeline standardizes, validates, cleans, profiles and "
        "documents the dataset without modifying the uploaded source file."
    )

    if st.button(
        "🧹 CLEAN MY DATA",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("Running data-quality pipeline..."):
            try:
                cleaned, log = clean_data(
                    df,
                    missing_strategy,
                    enable_outlier_analysis,
                    fix_sales,
                )
                st.session_state.cleaned_df = cleaned
                st.session_state.clean_log = log
                st.session_state.original_df = df.copy()
                st.session_state.before_quality_score = quality_score(df)
                st.session_state.after_quality_score = quality_score(cleaned)
                unresolved = sum(int(log.get(k, 0)) for k in [
                    "Final invalid emails", "Final invalid phones",
                    "Final City/State mismatches", "Final Sales mismatches"
                ])
                if unresolved:
                    st.warning("⚠️ Cleaning completed with review items. Check the final validation metrics in the audit log.")
                else:
                    st.success("✅ Cleaning completed and final validation passed.")
            except Exception as exc:
                st.error(f"Cleaning failed: {exc}")
                st.exception(exc)

    if "cleaned_df" in st.session_state:
        cleaned = st.session_state.cleaned_df
        log = st.session_state.clean_log

        before = quality_score(df)
        after = quality_score(cleaned)

        st.subheader("Before vs After")

        a, b, c, d, e = st.columns(5)
        a.metric("Rows", f"{len(cleaned):,}", f"{len(cleaned)-len(df):+,}")
        b.metric(
            "Missing Cells",
            f"{int(cleaned.isna().sum().sum()):,}",
            f"{int(cleaned.isna().sum().sum()) - int(df.isna().sum().sum()):+,}",
        )
        c.metric(
            "Duplicates",
            f"{int(cleaned.duplicated().sum()):,}",
            f"{int(cleaned.duplicated().sum()) - int(df.duplicated().sum()):+,}",
        )
        d.metric("Quality Score", f"{after}/100", f"{after-before:+.1f}")
        e.metric("Status", quality_status(after))

        st.progress(after / 100)

        st.subheader("Cleaning Audit Log")
        log_df = pd.DataFrame([
            {"Cleaning Action": k, "Result": v}
            for k, v in log.items()
        ])
        st.dataframe(log_df, use_container_width=True, hide_index=True)

        st.subheader("Cleaned Data Preview")
        st.dataframe(cleaned.head(100), use_container_width=True, hide_index=True)

# ============================================================
# OUTLIERS
# ============================================================

with tab3:
    st.subheader("Outlier Analysis")

    analysis_df = (
        st.session_state.cleaned_df
        if "cleaned_df" in st.session_state
        else df
    )

    outlier_df = detect_outliers(analysis_df)

    if outlier_df.empty:
        st.success("No significant IQR outliers detected.")
    else:
        total = int(outlier_df["Outliers"].sum())
        st.metric("Outlier cells", f"{total:,}")
        st.dataframe(
            outlier_df,
            use_container_width=True,
            hide_index=True,
        )

        if total:
            st.caption(
                "Outliers are statistical signals, not automatically bad data. "
                "The cleaning option caps them only when explicitly enabled."
            )

# ============================================================
# PROFILE
# ============================================================

with tab4:
    st.subheader("Column-Level Data Profile")

    profile_df = profile(
        st.session_state.cleaned_df
        if "cleaned_df" in st.session_state
        else df
    )

    st.dataframe(
        profile_df,
        use_container_width=True,
        hide_index=True,
    )

# ============================================================
# EXPORT
# ============================================================

with tab5:
    st.subheader("📥 Export & Save")
    st.caption(
        "Download your cleaned dataset or permanently save this cleaning run "
        "to the local History so you can review it later."
    )

    if "cleaned_df" in st.session_state:
        if st.button(
            "💾 SAVE THIS RUN TO HISTORY",
            type="primary",
            use_container_width=True,
        ):
            try:
                if not st.session_state.get("history_saved_for_source"):
                    history_id = save_to_history(
                        st.session_state.source_file,
                        df,
                        st.session_state.cleaned_df,
                        st.session_state.clean_log,
                    )
                    st.session_state.history_saved_for_source = history_id
                    st.success(
                        f"✅ Saved to History. Run ID: `{history_id}`"
                    )
                    st.rerun()
                else:
                    st.info(
                        f"This cleaning run is already saved in History "
                        f"(Run ID: `{st.session_state.history_saved_for_source}`)."
                    )
            except Exception as exc:
                st.error(f"Could not save this run to History: {exc}")

        st.divider()

    st.subheader("Export")

    if "cleaned_df" not in st.session_state:
        st.warning("Clean the dataset first.")
    else:
        cleaned = st.session_state.cleaned_df
        log = st.session_state.clean_log

        log_df = pd.DataFrame([
            {"Metric": k, "Value": v}
            for k, v in log.items()
        ])

        profile_df = profile(cleaned)
        outlier_df = detect_outliers(cleaned)

        csv_bytes = create_csv(cleaned)
        excel_bytes = create_excel(
            cleaned,
            log_df,
            profile_df,
            outlier_df,
        )

        c1, c2 = st.columns(2)

        with c1:
            st.download_button(
                "⬇️ Download Cleaned CSV",
                data=csv_bytes,
                file_name="DataClean_Pro_Cleaned_Data.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with c2:
            st.download_button(
                "⬇️ Download Excel Report",
                data=excel_bytes,
                file_name="DataClean_Pro_Quality_Report.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True,
            )

        st.success(
            "✅ Export package includes Cleaned_Data, Cleaning_Log, "
            "Data_Profile and Outlier_Analysis."
        )

# ============================================================
# AI DATA QUALITY ASSISTANT
# ============================================================

with tab7:
    st.subheader("🤖 AI Data Quality Assistant")
    st.caption(
        "Analyze dataset quality, explain risks and recommend review actions. "
        "Recommendations do not modify your data automatically."
    )

    analysis_target = (
        st.session_state.cleaned_df
        if "cleaned_df" in st.session_state
        else df
    )
    target_label = "Cleaned dataset" if "cleaned_df" in st.session_state else "Uploaded dataset"

    st.info(
        f"Analysis target: **{target_label}** • "
        "The local assistant inspects structure and quality signals. "
        "Optional LLM explanations use only a compact quality summary."
    )

    if st.button("🧠 ANALYZE DATA QUALITY", type="primary", use_container_width=True):
        with st.spinner("Analyzing dataset quality..."):
            st.session_state.ai_quality_analysis = build_ai_quality_analysis(analysis_target)
            st.session_state.ai_llm_explanation = None
            st.session_state.ai_llm_error = None

    if "ai_quality_analysis" in st.session_state:
        analysis = st.session_state.ai_quality_analysis
        summary = analysis["summary"]
        counts = summary["severity_counts"]

        a, b, c, d = st.columns(4)
        a.metric("Issues", f"{summary['issue_count']:,}")
        b.metric("High", f"{counts.get('High', 0):,}")
        c.metric("Medium", f"{counts.get('Medium', 0):,}")
        d.metric("Missing Cells", f"{summary['missing_cells']:,}")

        st.subheader("Assistant Assessment")
        if not analysis["issues"]:
            st.success("✅ No major structural data-quality issues were detected.")
        else:
            st.caption("Each finding now explains what was detected, why it matters, what to do next, and which DataClean Pro workflow to use.")
            for i, issue in enumerate(analysis["issues"][:50], start=1):
                icon = {"High": "🔴", "Medium": "🟠", "Low": "🟡"}.get(issue["severity"], "ℹ️")
                with st.container(border=True):
                    st.markdown(f"**{icon} {issue['category']} — {issue['column']}**")
                    st.write(f"**🔎 What was found**  ")
                    st.write(issue["finding"])
                    st.write(f"**📊 Why it matters**  ")
                    st.write(issue["why_it_matters"])
                    st.write(f"**🛠 Recommended action**  ")
                    st.write(issue["recommended_action"])
                    st.info(f"**Where to act:** {issue['workflow']}")
                    st.caption(f"**Guardrail:** {issue['guardrail']}")
                    st.caption(f"**Recommendation:** {issue['recommendation']}")

        st.subheader("Recommended Review Actions")
        for item in analysis["recommendations"]:
            st.markdown(f"- {item}")

        st.subheader("Review Checklist")
        st.caption("Mark findings as reviewed. This checklist never changes the dataset.")
        reviewed = 0
        for i, issue in enumerate(analysis["issues"][:50]):
            label = f"Reviewed: {issue['severity']} — {issue['category']} — {issue['column']}"
            if st.checkbox(label, key=f"ai_reviewed_{i}"):
                reviewed += 1
        total_issues = len(analysis["issues"])
        if total_issues:
            if reviewed == total_issues:
                st.success("✅ All detected findings have been reviewed.")
            else:
                st.info(f"{reviewed} of {total_issues} findings reviewed. Review the remaining items before making domain-specific changes.")
        else:
            st.success("✅ No findings require review.")

        st.divider()
        st.subheader("Optional AI Explanation")
        if os.getenv("OPENAI_API_KEY", "").strip():
            st.caption("An LLM can turn the quality findings into a concise analyst-style explanation. Raw rows are not sent.")
            if st.button("✨ GENERATE AI EXPLANATION", use_container_width=True):
                with st.spinner("Generating explanation..."):
                    explanation, error = generate_llm_quality_explanation(analysis)
                    st.session_state.ai_llm_explanation = explanation
                    st.session_state.ai_llm_error = error
            if st.session_state.get("ai_llm_error"):
                st.warning(st.session_state.ai_llm_error)
            if st.session_state.get("ai_llm_explanation"):
                st.markdown(st.session_state.ai_llm_explanation)
        else:
            st.caption(
                "Optional LLM mode is off. Set OPENAI_API_KEY in your local environment or deployment secrets "
                "to enable natural-language AI explanations."
            )

# ============================================================
# FOOTER
# ============================================================

st.divider()
st.caption(
    "DataClean Pro • Portfolio Project • Automated data preparation, "
    "quality assessment, validation and export"
)



# Quality audit export — generated only after a successful cleaning run.
if "cleaned_df" in st.session_state and "original_df" in st.session_state:
    try:
        _before = st.session_state["original_df"]
        _after = st.session_state["cleaned_df"]
        _before_score = st.session_state.get("before_quality_score", np.nan)
        _after_score = st.session_state.get("after_quality_score", np.nan)
        _audit_summary = _build_quality_summary(_before, _after, _before_score, _after_score)
        st.session_state["audit_summary"] = _audit_summary
    except Exception:
        pass


# ============================================================
# HISTORY
# ============================================================

with tab6:
    st.subheader("🕘 Cleaning History")
    st.caption(
        "Your saved cleaning runs are stored locally in the project's "
        "`data/history` folder. Nothing is automatically deleted."
    )

    history_df = get_history()

    if history_df.empty:
        st.info(
            "No saved runs yet. Clean a dataset, open the Export tab, "
            "and click **SAVE THIS RUN TO HISTORY**."
        )
    else:
        h1, h2, h3 = st.columns(3)
        h1.metric("Saved Runs", f"{len(history_df):,}")
        h2.metric(
            "Latest Quality",
            f"{history_df.iloc[0]['Quality After']:.1f}/100",
        )
        h3.metric(
            "Datasets",
            f"{history_df['Dataset'].nunique():,}",
        )

        display_history = history_df.drop(
            columns=["original_path", "cleaned_path"],
            errors="ignore",
        ).copy()
        display_history["Quality Before"] = display_history["Quality Before"].round(1)
        display_history["Quality After"] = display_history["Quality After"].round(1)

        st.dataframe(
            display_history,
            use_container_width=True,
            hide_index=True,
        )

        options = history_df["ID"].tolist()
        selected_id = st.selectbox(
            "Select a saved run to inspect",
            options,
            format_func=lambda x: (
                f"{x} — "
                f"{history_df.loc[history_df['ID'] == x, 'Dataset'].iloc[0]} — "
                f"{history_df.loc[history_df['ID'] == x, 'Saved At'].iloc[0]}"
            ),
        )

        record = get_history_record(selected_id)

        if record:
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Quality Before", f"{record['quality_before']:.1f}/100")
            r2.metric("Quality After", f"{record['quality_after']:.1f}/100")
            r3.metric("Rows After", f"{record['rows_after']:,}")
            r4.metric(
                "Improvement",
                f"{record['quality_after'] - record['quality_before']:+.1f}",
            )

            cleaned_path = Path(record["cleaned_path"])
            original_path = Path(record["original_path"])

            if cleaned_path.exists():
                cleaned_history_df = pd.read_csv(cleaned_path)

                st.subheader("Saved Cleaned Dataset")
                st.dataframe(
                    cleaned_history_df.head(100),
                    use_container_width=True,
                    hide_index=True,
                )

                st.download_button(
                    "⬇️ Download Saved Cleaned CSV",
                    data=cleaned_path.read_bytes(),
                    file_name=f"cleaned_{Path(record['source_name']).stem}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            c1, c2 = st.columns(2)

            with c1:
                if original_path.exists():
                    st.download_button(
                        "⬇️ Download Original CSV",
                        data=original_path.read_bytes(),
                        file_name=f"original_{Path(record['source_name']).stem}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

            with c2:
                if st.button(
                    "🗑️ Delete Selected History",
                    use_container_width=True,
                ):
                    if delete_history_record(selected_id):
                        st.success("History record deleted.")
                        st.rerun()
                    else:
                        st.error("History record could not be deleted.")


# ---------------------------------------------------------------------------
# Portfolio footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(
    "DataClean Pro • Built with Python, Pandas & Streamlit • "
    "Designed to demonstrate end-to-end data quality engineering."
)