import ast
import sys
import types
from pathlib import Path
import pandas as pd

# The reusable engine can be tested without installing/running Streamlit.
st = types.ModuleType("streamlit")
st.set_page_config = lambda *args, **kwargs: None
st.markdown = lambda *args, **kwargs: None
sys.modules.setdefault("streamlit", st)

APP = Path(__file__).resolve().parents[1] / "app.py"
SOURCE = APP.read_text(encoding="utf-8")

# Load only imports, constants, and function/class definitions before the Streamlit
# file-upload/UI execution block. This lets us test the reusable engine without
# starting the interactive application.
tree = ast.parse(SOURCE)
cut_line = next(
    n.lineno for n in tree.body
    if isinstance(n, ast.Assign)
    and any(isinstance(t, ast.Name) and t.id == "uploaded" for t in n.targets)
)
selected = []
for node in tree.body:
    if getattr(node, "lineno", 0) >= cut_line:
        break
    if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.FunctionDef, ast.AsyncFunctionDef)):
        selected.append(node)
module = ast.Module(body=selected, type_ignores=[])
code = compile(module, str(APP), "exec")
ns = {}
exec(code, ns)


def test_source_compiles():
    compile(SOURCE, str(APP), "exec")


def test_clean_data_handles_messy_generic_dataset():
    df = pd.DataFrame({
        " Customer ID ": ["001", "002", "002", "003", None],
        "Name": [" alice ", "BOB", "BOB", "Carol", "Dave"],
        "Email": ["alice@example.com", "bad-email", "bob@example.com", "carol@example.com", None],
        "Age": [25, 150, 30, 40, 35],
        "Amount": ["₹1,200", "2500", "3,000", None, "4,500"],
    })
    cleaned, log = ns["clean_data"](
        df,
        "Leave missing values unchanged",
        True,
        False,
    )
    assert len(cleaned) == 5  # no rows are exact duplicates
    assert cleaned["Customer_ID"].dtype.name == "string"
    assert "Final quality score" in log
    assert "Domain-specific rules applied" in log
    assert log["Domain-specific rules applied"] == "None — universal mode"


def test_email_and_phone_validation_do_not_invent_values():
    df = pd.DataFrame({
        "email": ["valid@example.com", "not-an-email", None],
        "phone": ["+91 98765 43210", "123", None],
    })
    cleaned, log = ns["clean_data"](
        df,
        "Leave missing values unchanged",
        False,
        False,
    )
    assert cleaned.loc[1, "email"] is pd.NA or pd.isna(cleaned.loc[1, "email"])
    assert pd.isna(cleaned.loc[1, "phone"])
    assert log["Invalid emails converted to missing"] >= 1
    assert log["Invalid phones converted to missing"] >= 1


def test_percentage_parsing_is_conservative():
    df = pd.DataFrame({"conversion_rate": ["10%", "25%", "50%"]})
    cleaned, _ = ns["clean_data"](df, "Leave missing values unchanged", False, False)
    assert cleaned["conversion_rate"].tolist() == [0.10, 0.25, 0.50]


def test_ai_quality_assistant_detects_core_issues():
    df = pd.DataFrame({
        "Email": ["ok@example.com", "bad", None, "x@y.com"],
        "Age": [25, 150, 30, 31],
        "Status": ["Active", "active", "ACTIVE", "Active"],
    })
    analysis = ns["build_ai_quality_analysis"](df)
    categories = {i["category"] for i in analysis["issues"]}
    assert "Missing Values" in categories
    assert "Invalid Contact Data" in categories
    assert "Semantic Range" in categories
    assert analysis["summary"]["issue_count"] >= 3


def test_quality_summary_is_before_after_only():
    before = pd.DataFrame({"a": [1, None, 1]})
    after = pd.DataFrame({"a": [1, 1]})
    summary = ns["_build_quality_summary"](before, after, 60, 90)
    assert summary["Rows Before"] == 3
    assert summary["Rows After"] == 2
    assert summary["Missing Cells Before"] == 1
    assert summary["Quality Score After"] == 90.0


def test_ai_findings_include_explanation_and_workflow():
    df = pd.DataFrame({"Email": [None, "ok@example.com"], "Unit_Price": [10, 1000]})
    analysis = ns["build_ai_quality_analysis"](df)
    missing = next(i for i in analysis["issues"] if i["category"] == "Missing Values")
    assert missing["why_it_matters"]
    assert missing["recommended_action"]
    assert missing["workflow"]
    assert missing["guardrail"]


def test_ai_outlier_finding_has_safe_guardrail():
    df = pd.DataFrame({"Unit_Price": [10, 11, 12, 13, 14, 15, 16, 1000]})
    analysis = ns["build_ai_quality_analysis"](df)
    outlier = next(i for i in analysis["issues"] if i["category"] == "Outliers")
    assert "Outliers" in outlier["workflow"]
    assert "delete or cap outliers automatically" in outlier["guardrail"]
