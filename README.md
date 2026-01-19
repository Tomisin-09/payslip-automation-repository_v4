# Payslip Automation (PDF-only, Excel-agnostic)

This project generates **professional PDF payslips** for employees using **pure-Python ReportLab**.  
Excel is used **only as a data source** (to read employee and payroll values).  
There is **no Excel automation**, **no Office licence dependency**, and **no HTML rendering**.
The project can work on a Mac OS but will not send to outlook due to specific Windows system requirements to make this process work 

The system is **configuration-driven**, **auditable**, and designed so non-developers can update payroll fields, branding, and behaviour **without touching code**.

---

## What this system does

1. Reads employee payroll data from an Excel **Data Source** sheet  
2. Validates required columns and branding assets  
3. Computes totals (Gross Income, Total Deductions, Net Pay)  
4. Generates **one PDF payslip per employee**  
5. Saves outputs and logs into a **date-specific directory**  
6. Allows the user to **review PDFs before emailing**  
7. Optionally emails payslips using **Outlook Desktop**

---
## Prerequisites
You need to have Python installed on your system. Go to https://www.python.org/downloads/ to get the latest version 

---

## Key design goals

- **PDF-only output**
- **Pure Python (ReportLab)**
- **Config over code (YAML-driven)**
- **Well detailed logs, on the console and log files**
- **Fail fast with clear errors**
- **Human-in-the-loop before email**
- **Easy to extend with new payroll fields**

---

## Folder structure (simplified)

```
payslip-automation/
│
├─ assets/
│  └─ branding/
│     ├─ logo.png
│     └─ signature.png
│
├─ config/
│  └─ settings.yml
│
├─ data/
│  └─ payslip_te.xlsx   ← Data Source sheet lives here
│
├─ output/                    ← Generated per run
│
├─ src/
│  ├─ main.py
│  ├─ preflight.py
│  ├─ pdf/
│  │  └─ reportlab_payslip_exporter.py
│  ├─ data_io/
│  │  └─ load_data.py
│  ├─ email/
│  │  └─ outlook_sender.py
│  └─ utils/
│     ├─ asset_validation.py
│     ├─ config.py
│     ├─ logging_utils.py
│     └─ period.py
│
├─ run.ps1
├─ run.bat
├─ run.sh
├─ requirements.txt
└─ README.md
```

---

## How the process works (step-by-step)

1. **Run the process**
   - Use `run.ps1` (PowerShell) or `run.bat`
   - This is the *only* entrypoint

2. **Preflight checks**
   - Python version is verified
   - Required Python libraries are checked
   - Outlook availability is checked (if emailing is enabled)

3. **Configuration is loaded**
   - All behaviour comes from `config/settings.yml`

4. **Branding assets are validated**
   - Logo and signature files must:
     - Exist
     - Match allowed file types
     - Match required image resolution
   - The process stops if validation fails

5. **Payroll period is resolved**
   - Controlled via:
     - `auto_previous_month`
     - `auto_current_month`
     - `manual`

6. **Employee data is loaded**
   - Read from the **Data Source** sheet
   - Required columns must exist
   - Missing or unexpected columns are reported clearly

7. **PDF payslips are generated**
   - One PDF per employee
   - Totals are computed automatically
   - Layout includes:
     - Company header
     - Logo (top-right)
     - Employee information
     - Earnings
     - Deductions
     - Net Pay (highlighted)
     - Signature (bottom-left)

8. **Outputs are written**
   - PDFs, logs, and summary files are written to a folder for that run

9. **Approval gate**
   - User is asked to confirm before emails are sent
   - Allows inspection of PDFs first

10. **Optional email step**
    - Emails are sent or displayed via Outlook
    - Controlled by configuration

---

## Output structure

Each run creates a **date-specific folder** with **timestamped logs**.

```
output/<period_id>/
│
├─ pdf/
│  └─ {ref}_{name}_{date}.pdf
│
├─ logs/<run_date>/
│        └─ run_log_<YYYY-MM-DD_HH-MM-SS>.log
│
└─ summary/
   └─ manifest_<YYYY-MM-DD_HH-MM-SS>.csv
```

This ensures:
- Every run is auditable
- Logs always match the PDFs they generated

---

## Adding or changing payroll fields (no code changes)

To add a new earning or deduction:

1. Add a **new column** to the Data Source sheet
2. Add a matching entry in `settings.yml` under:
   - `earnings:` or `deductions:`
3. Run the process again

The system will:
- Validate the column exists
- Include it in the PDF
- Automatically recalculate totals

---

## Branding updates (no code changes)

To update branding:
- Replace `assets/branding/logo.png`
- Replace `assets/branding/signature.png`

As long as the files:
- Have the correct filename
- Match the required resolution
- Match the allowed extension

…the system will accept them without code changes.

---

## Email behaviour

Email sending is optional and controlled via config.

- **display** mode  
  Opens Outlook drafts for review

- **send** mode  
  Sends emails automatically

Emails are only sent **after user confirmation**.

---

## Summary

This is a **robust, production-ready payslip generator** designed to be:
- Safe
- Auditable
- Configurable
- Easy to operate
- Easy to extend

If you treat `settings.yml` and the Data Source sheet as the “interface”,  
the code itself rarely needs to change.

---

## Quick start

### macOS / Linux

```bash
./run.sh
```

### Windows (PowerShell)

```powershell
.\run.ps1
```

### Windows (CMD)

```bat
run.bat
```

## Minimal Excel Data Source columns

Your `Data Source` sheet must include:

- Reference Number
- Employee Name
- Designation
- Department
- Email

Plus the earning/deduction columns you define in `config/settings.yml` under `fields:`.

## Notes

- Emailing uses **Outlook Desktop automation**, so it will only work on **Windows** with Outlook + `pywin32`.
- PDF rendering is **pure-Python ReportLab** (no Excel, no HTML).
