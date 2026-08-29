# Installation and Setup Guide (Reproducing from Source ZIP)

**Project:** Multi-Tenant Inter-Office Memo Management System  
**Course:** CSE226 Foundations of Vibe Coding  
**Author:** Zaman Shafin  

---

## 1. Prerequisites & Required Software

- **Python:** Python 3.10, 3.11, or 3.12+
- **Package Manager:** uv (Recommended for fast resolution) or standard pip + env
- **Database:** SQLite (Default zero-config local mode) or PostgreSQL (Production mode)
- **Web Browser:** Modern web browser (Chrome, Edge, Firefox, Safari)

---

## 2. Quick Setup with uv (Recommended)

### Step 1: Install uv (if not already installed)
`powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
C:/Users/User/.gemini/antigravity/bin;C:\Users\User\AppData\Roaming\Antigravity\bin;C:\Windows\system32;C:\Windows;C:\Windows\System32\Wbem;C:\Windows\System32\WindowsPowerShell\v1.0\;C:\Windows\System32\OpenSSH\;C:\Users\User\.local\bin;C:\Users\User\AppData\Local\Microsoft\WindowsApps;C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Git.MinGit_Microsoft.Winget.Source_8wekyb3d8bbwe\cmd = "C:\Users\User\.local\bin;C:/Users/User/.gemini/antigravity/bin;C:\Users\User\AppData\Roaming\Antigravity\bin;C:\Windows\system32;C:\Windows;C:\Windows\System32\Wbem;C:\Windows\System32\WindowsPowerShell\v1.0\;C:\Windows\System32\OpenSSH\;C:\Users\User\.local\bin;C:\Users\User\AppData\Local\Microsoft\WindowsApps;C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Git.MinGit_Microsoft.Winget.Source_8wekyb3d8bbwe\cmd"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
`

### Step 2: Extract ZIP & Install Dependencies
`ash
# Navigate to the extracted project directory
cd memo-system

# Install dependencies using uv
uv pip install -r requirements.txt
`

---

## 3. Alternative Setup with Standard Python pip

`ash
# Create and activate virtual environment
python -m venv .venv

# On Windows:
.\.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
`

---

## 4. Environment Variables Configuration

Create a .env file in the root directory (or use default built-in fallbacks):

`ini
# Application Secrets & JWT Key
SECRET_KEY=super-secret-enterprise-memo-jwt-key-2026-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database Connection (SQLite local default or PostgreSQL)
DATABASE_URL=sqlite:///./memo_system.db

# Storage Directory
UPLOAD_DIR=./uploads
`

---

## 5. Initialize & Seed Demonstration Data

Populate the database with pre-configured organizational hierarchy, departments, categories, and demo accounts:

`ash
# Using uv:
uv run python -m app.seed

# Using standard python:
python -m app.seed
`

---

## 6. Run the Local Development Server

`ash
# Using uv:
uv run python run.py

# Using standard python:
python run.py
`

The application will be running at:  
👉 **http://127.0.0.1:8000**

---

## 7. Run Automated Tests

To execute the complete 20-test automated validation suite:

`ash
uv run pytest tests/
`

Expected output: **20 passed in ~20s**

---

## 8. Demonstration Evaluation Accounts

- **Organization Code:** cme
- **Universal Password:** password123

| Role | Email | Purpose |
| :--- | :--- | :--- |
| **Admin** | dmin@acmecorp.com | Org Admin & Audit Logs |
| **Author** | lex.morgan@acmecorp.com | Memo Drafting & Submissions |
| **Dept Head** | head.eng@acmecorp.com | Tier-1 Approvals & Delegations |
| **Delegate** | jessica.taylor@acmecorp.com | Delegated Sign-off on David's behalf |
| **Finance** | inance.mgr@acmecorp.com | Tier-2 Financial Approvals |
| **Director** | director@acmecorp.com | Tier-3 Operational Approvals |
| **CEO** | ceo@acmecorp.com | Final Sign-off & PDF Generation |
