# 🧹 DataClean Pro — AI-Assisted Data Quality & Cleaning Platform

DataClean Pro is a Streamlit-based, dataset-agnostic data quality platform designed for real Data Analyst workflows.

It accepts CSV and Excel files, profiles unfamiliar datasets, performs conservative automated cleaning, validates common data-quality signals, detects statistical outliers, maintains a cleaning audit trail, stores run history, and provides an AI Data Quality Assistant for issue explanation and review recommendations.

## Core workflow

**Upload → Profile → Diagnose → AI Review → Clean → Validate → Measure → Export**

## Features

- CSV / XLSX upload
- Dataset-agnostic type inference
- Missing-value normalization
- Safe text and whitespace normalization
- Email and phone validation
- Conservative date / numeric / percentage parsing
- Exact duplicate removal
- Optional missing-value strategies
- IQR outlier detection without blind deletion/capping
- Semantic range checks for high-confidence fields
- Before/after quality scoring
- Column-level profiling
- Cleaning audit log
- SQLite-backed local history
- CSV export
- Multi-sheet Excel quality report
- AI Data Quality Assistant
- Optional LLM explanation using aggregate quality information rather than raw dataset rows

## AI architecture

The application separates **deterministic data transformations** from **AI reasoning**:

1. The universal profiler extracts structural quality signals.
2. The local assistant identifies quality issues and produces recommendations.
3. If an OpenAI API key is configured, the optional LLM layer explains those findings in analyst-friendly language.
4. The deterministic cleaner remains responsible for actual data transformations.

This design avoids silently letting an LLM rewrite production data.

## Run locally

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

The application works without an OpenAI key. The optional natural-language explanation requires:

```text
OPENAI_API_KEY=your_key_here
```

Optional model override:

```text
OPENAI_MODEL=gpt-4.1-mini
```

For Streamlit deployment, place these values in the app's Secrets configuration rather than committing them to Git.

## Final release safeguards

- Safe missing-value behavior is the default: missing values are preserved unless the user explicitly selects an imputation/deletion strategy.
- AI findings are recommendations and review signals; they never silently modify the dataset.
- A review checklist lets the analyst mark AI findings as reviewed before making domain-specific decisions.
- Raw dataset rows are not sent to the optional LLM layer; only compact quality/profile information is used.
- The deterministic cleaner remains responsible for all actual transformations.

## Testing

Run:

```bash
python -m pytest -q
```

The included tests cover:

- syntax compilation
- generic messy-data cleaning
- email / phone validation
- percentage parsing
- AI quality issue detection
- before/after quality summaries

## Project structure

```text
DataClean_Pro_Final/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml
└── tests/
    └── test_core.py
```

## Portfolio positioning

**Project:** DataClean Pro — AI-Assisted Data Quality & Cleaning Platform

**Stack:** Python, Pandas, NumPy, Streamlit, SQLite, OpenAI API, Excel/CSV

**Resume bullet:**

> Built a dataset-agnostic data quality platform that profiles unfamiliar CSV/Excel datasets, performs conservative automated cleaning and validation, detects outliers, maintains audit history, generates quality reports, and provides AI-assisted data-quality recommendations using Python, Pandas, Streamlit and SQLite.

## AI Assistant — Review Guidance

The AI Assistant is a **data-quality reasoning layer**, not an autonomous data editor. It diagnoses quality signals and explains what they mean before any deterministic cleaning action is taken.

Each detected finding now provides:
- **What was found** — the measurable quality signal and affected column.
- **Why it matters** — the potential analytical or operational impact.
- **Recommended action** — a safe next step for the analyst.
- **Where to act** — the relevant DataClean Pro workflow/tab.
- **Guardrail** — what the application will deliberately avoid doing automatically.

This keeps AI recommendations explainable and prevents silent changes to business data. Outliers, missing values, category aliases and ambiguous fields remain review signals unless an explicit business rule supports a transformation.
