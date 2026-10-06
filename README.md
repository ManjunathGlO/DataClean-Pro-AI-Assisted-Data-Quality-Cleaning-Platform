# 🧹 DataClean Pro

### AI-Assisted Data Quality & Cleaning Platform

> **Turn messy CSV/Excel datasets into reliable, analysis-ready data with transparent quality checks, deterministic cleaning, validation, and AI-assisted recommendations.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python\&logoColor=white)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-150458?logo=pandas\&logoColor=white)](https://pandas.pydata.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit\&logoColor=white)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/SQLite-Local%20History-003B57?logo=sqlite\&logoColor=white)](https://www.sqlite.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-Optional%20AI%20Layer-412991?logo=openai\&logoColor=white)](https://openai.com/)
[![Tests](https://img.shields.io/badge/Tests-8%20Passing-success)](#testing)

---

## 📌 Project Overview

Real-world datasets are rarely analysis-ready.

They often contain:

* Missing values
* Duplicate records
* Invalid contact information
* Inconsistent data types
* Statistical outliers
* Constant or low-value columns
* Ambiguous categorical values
* Formatting inconsistencies
* Unexpected values that can affect analysis

**DataClean Pro** was built to address this problem through an end-to-end data-quality workflow.

Instead of treating data cleaning as a collection of one-off Pandas scripts, the application provides a reusable platform where analysts can:

**Upload → Profile → Diagnose → Review → Clean → Validate → Measure → Export → Track History**

The platform is designed to be **dataset-agnostic**, meaning it can work with unfamiliar CSV and Excel datasets without requiring a fixed schema.

---

# 🎯 What Problem Does It Solve?

A typical data analyst may spend significant time manually checking:

> "How many values are missing?"

> "Are there duplicates?"

> "Which columns have quality problems?"

> "Are these extreme values actually errors?"

> "What changed after cleaning?"

> "Can I reproduce or explain what I changed?"

DataClean Pro brings these checks into one workflow and makes the results easier to inspect, explain, validate, and export.

---

# 🚀 Key Features

## 📂 1. Universal Dataset Profiling

Upload CSV or Excel files and automatically generate a structural profile.

The application identifies:

* Row and column counts
* Data types
* Missing values
* Unique values
* Completeness
* Cardinality
* Numeric characteristics
* Potential quality issues

No fixed dataset schema is required.

---

## 🧹 2. Conservative Data Cleaning

DataClean Pro performs deterministic transformations using Python and Pandas.

Supported operations include:

* Missing-value normalization
* Whitespace/text normalization
* Duplicate detection and removal
* Email validation
* Phone validation
* Date parsing
* Numeric parsing
* Percentage parsing
* Configurable missing-value strategies
* Semantic range validation

The cleaner is intentionally conservative.

**It does not make aggressive assumptions about business data.**

---

## 📊 3. Data Quality Scoring

The platform calculates quality measurements before and after cleaning.

This allows analysts to answer:

> **Did the cleaning process actually improve the dataset?**

The application tracks metrics such as:

* Missing cells
* Duplicate records
* Invalid values
* Quality score
* Outlier signals
* Before/after changes

---

## 📈 4. Outlier Analysis

Numeric columns are analyzed using the **1.5×IQR rule**.

Outliers are treated as **review signals**, not automatic errors.

For example:

```text
Unit_Price
──────────
100
105
110
108
103
9999  ← statistical outlier
```

The platform does not automatically delete or cap the value.

This prevents legitimate business observations from being accidentally removed.

---

# 🤖 AI Data Quality Assistant

DataClean Pro includes an optional AI-assisted quality analysis layer.

The AI Assistant is designed as a **Data Quality Copilot**, not an autonomous data editor.

For each detected issue, the assistant explains:

### 🔎 What was found

The measurable quality problem.

### 📊 Why it matters

The potential analytical or operational impact.

### 🛠 Recommended action

A practical next step for the analyst.

### 📍 Where to act

The relevant DataClean Pro workflow.

### 🛡️ Guardrail

What the application deliberately avoids doing automatically.

Example:

> **🟠 Outliers — Unit_Price**
>
> **What was found:** 145 observations fall outside the 1.5×IQR bounds.
>
> **Why it matters:** These values may represent either data-entry errors or legitimate high-value products.
>
> **Recommended action:** Inspect the affected records before modifying them.
>
> **Where to act:** Outliers → inspect IQR findings.
>
> **Guardrail:** Outliers are not automatically deleted or capped.

---

# 🧠 AI Architecture

A key design principle of DataClean Pro is the separation between **AI reasoning** and **actual data transformation**.

```text
                    DATASET
                       │
                       ▼
              ┌─────────────────┐
              │ Data Profiler   │
              └────────┬────────┘
                       │
                       ▼
              Quality Findings
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
     Deterministic Engine   AI Assistant
             │                   │
       Detect / Validate    Explain / Recommend
             │                   │
             └─────────┬─────────┘
                       ▼
                 HUMAN REVIEW
                       │
                       ▼
              Deterministic
                  Cleaning
                       │
                       ▼
                VALIDATED DATA
```

### Why this architecture?

The AI layer should not silently modify business data.

Therefore:

**AI = reasoning + explanation + recommendations**

**Python/Pandas = actual data transformations**

This provides greater transparency and reduces the risk of unexplained AI-generated changes.

---

# 🔐 Privacy-Conscious AI Design

When the optional OpenAI integration is enabled, the application does **not send raw dataset rows to the LLM for analysis**.

Instead, it works with compact quality/profile information such as:

* Dataset dimensions
* Missing-value statistics
* Quality findings
* Column-level summaries
* Detected issue categories
* Recommendations

This keeps the AI layer focused on **data-quality reasoning rather than raw-row processing**.

---

# 🔄 End-to-End Workflow

```text
        Upload CSV / Excel
                │
                ▼
          Profile Dataset
                │
                ▼
        Diagnose Quality Issues
                │
                ▼
          AI Review
                │
                ▼
         Human Review
                │
                ▼
        Deterministic Cleaning
                │
                ▼
            Validation
                │
                ▼
       Before / After Metrics
                │
                ▼
        Quality Report
                │
                ▼
          Export Dataset
                │
                ▼
          Save to History
```

---

# 📑 Application Modules

| Module               | Purpose                                      |
| -------------------- | -------------------------------------------- |
| **Overview**         | Dataset summary and quality indicators       |
| **Clean & Validate** | Deterministic cleaning and validation        |
| **Outliers**         | Statistical outlier analysis                 |
| **Column Profile**   | Column-level data-quality inspection         |
| **Export**           | Clean datasets and quality reports           |
| **History**          | Review previous cleaning runs                |
| **AI Assistant**     | Explain findings and provide review guidance |

---

# 📊 Quality & Validation Capabilities

DataClean Pro can identify and analyze:

### Missing Data

* Missing-cell counts
* Missing percentages
* Column-level completeness

### Duplicates

* Exact duplicate records
* Duplicate removal during cleaning

### Invalid Values

* Email validation
* Phone validation
* Numeric parsing
* Date parsing
* Percentage parsing

### Statistical Issues

* IQR-based outliers
* Constant columns
* High-cardinality columns

### Semantic Issues

* High-confidence range checks
* Potential category inconsistencies
* Ambiguous values requiring business review

---

# 📋 Auditability & History

Every cleaning workflow is designed to be explainable.

The application maintains:

* Cleaning operations
* Before/after measurements
* Quality metrics
* Outlier findings
* Run history
* Exportable quality information

Local history is stored using **SQLite**.

This allows previous cleaning runs to be reviewed without relying on an external database.

---

# 📤 Export

DataClean Pro supports:

### CSV

Export the cleaned dataset for downstream analysis.

### Excel

Generate multi-sheet Excel quality reports containing information such as:

* Cleaned data
* Data profile
* Quality metrics
* Outlier analysis
* Cleaning information

---

# 🛡️ Safety & Data Quality Principles

DataClean Pro follows several conservative principles:

### 1. Missing values are preserved by default

The application does not automatically guess missing business values.

### 2. Outliers are signals

An outlier is not automatically a bad record.

### 3. AI does not silently modify data

AI recommendations require analyst review.

### 4. Business rules take priority

Where domain knowledge is required, the application avoids unsupported assumptions.

### 5. Deterministic transformations remain deterministic

Actual cleaning is performed by the application logic rather than delegated to an LLM.

---

# 🛠️ Technology Stack

| Technology     | Purpose                                   |
| -------------- | ----------------------------------------- |
| **Python**     | Application and data-processing logic     |
| **Pandas**     | Data manipulation and analysis            |
| **NumPy**      | Numerical analysis                        |
| **Streamlit**  | Interactive web application               |
| **SQLite**     | Local run history                         |
| **OpenAI API** | Optional AI-assisted quality explanations |
| **OpenPyXL**   | Excel processing/export                   |
| **Pytest**     | Automated testing                         |

---

# 🧪 Testing

The project includes automated tests covering core functionality.

Run:

```bash
python -m pytest -q
```

Current test coverage includes:

* Generic messy-data cleaning
* Email validation
* Phone validation
* Percentage parsing
* AI quality issue detection
* Before/after quality summaries
* Core application behavior

**Current release: 8 tests passing.**

---

# 💻 Local Installation

## 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/DataClean-Pro.git
cd DataClean-Pro
```

## 2. Create a virtual environment

### Windows

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python -m venv venv
source venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Run the application

```bash
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

---

# 🤖 Optional OpenAI Configuration

The application works without an OpenAI API key.

To enable the optional natural-language AI explanation layer:

```text
OPENAI_API_KEY=your_api_key
```

Optional model configuration:

```text
OPENAI_MODEL=gpt-4.1-mini
```

For Streamlit deployment, configure the API key through **Streamlit Secrets** rather than committing credentials to the repository.

**Never commit API keys or `.env` files to GitHub.**

---

# 📁 Project Structure

```text
DataClean-Pro/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── .streamlit/
│   └── config.toml
│
└── tests/
    └── test_core.py
```

---

# 🎯 Skills Demonstrated

This project demonstrates practical experience across:

### Data Analytics

* Data cleaning
* Data profiling
* Data validation
* Data-quality measurement
* Outlier analysis
* Data preparation

### Python

* Pandas
* NumPy
* Functions and modular logic
* Exception handling
* Data-processing pipelines

### Application Development

* Streamlit
* Interactive dashboards
* File upload/export workflows
* SQLite persistence

### AI

* LLM integration
* AI-assisted data-quality reasoning
* Structured prompts
* Privacy-conscious AI architecture
* Human-in-the-loop workflows

### Software Engineering

* Virtual environments
* Requirements management
* Automated testing
* Git/GitHub-ready project structure
* Defensive data-processing logic

---

# 💼 Business Value

DataClean Pro is designed around a practical analyst problem:

> **How can an analyst quickly understand an unfamiliar dataset, identify quality risks, clean it safely, and demonstrate what changed?**

The platform reduces repetitive manual inspection and creates a more structured workflow for preparing data for:

* Exploratory Data Analysis
* Reporting
* Business Intelligence
* Dashboard development
* Machine Learning preprocessing
* Operational analytics

---

# 🚀 Future Roadmap

Potential future improvements include:

* Interactive issue explorer
* Data-quality rule builder
* Advanced before/after comparison
* Automated quality-report generation
* Dataset version comparison
* More configurable validation rules
* Role-based workflows for team environments
* Cloud database support

---

# 👨‍💻 Portfolio Positioning

**DataClean Pro** demonstrates the ability to move beyond individual analysis notebooks and build a reusable analytical application.

It combines:

**Data Analysis + Data Quality + Python + Automation + AI + Application Development**

### Resume-ready description

> **DataClean Pro — AI-Assisted Data Quality & Cleaning Platform**
> Built a dataset-agnostic data quality platform using Python, Pandas, Streamlit and SQLite to profile unfamiliar CSV/Excel datasets, detect missing values, duplicates, invalid fields and statistical outliers, perform conservative deterministic cleaning and validation, maintain audit history, measure before/after quality, and provide AI-assisted explanations and recommendations.

---

# ⭐ Project Highlights

```text
✓ Dataset-agnostic CSV/Excel processing
✓ Automated data profiling
✓ Missing-value analysis
✓ Duplicate detection
✓ Email & phone validation
✓ Date & numeric parsing
✓ IQR outlier analysis
✓ Semantic validation
✓ Before/after quality measurement
✓ Cleaning audit trail
✓ SQLite run history
✓ Excel & CSV export
✓ AI Data Quality Assistant
✓ Human-in-the-loop AI review
✓ Privacy-conscious LLM architecture
✓ Automated tests
```

---

## 📌 Built With

**Python · Pandas · NumPy · Streamlit · SQLite · OpenAI API · OpenPyXL · Pytest**

---

### 👨‍💻 Author

**Manjunath G L**

 Data Analyst | Python | SQL | Power BI | Data Analytics

---

⭐ **If you find this project useful, consider starring the repository.**
