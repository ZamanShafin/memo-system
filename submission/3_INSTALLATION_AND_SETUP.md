# Installation and Setup Guide

**Enterprise Inter-Office Memo Management System**

---

## 1. Prerequisites & Required Software

- **Operating System:** Windows 10/11, macOS, or Linux
- **Python Version:** Python 3.12 or higher
- **Package Manager:** `uv` (Recommended) or standard `python -m venv` + `pip`
- **Web Browser:** Modern browser (Chrome, Firefox, Edge, Safari, Brave)

---

## 2. Fast Setup with `uv` (Recommended)

### Step 1: Install `uv` (if not already installed)
```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
$env:Path = "$HOME\.local\bin;$env:Path"

# Unix / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 2: Navigate to Project Directory & Install Dependencies
```powershell
cd c:\Users\User\Desktop\memo

# Create virtual environment and install packages
uv venv
uv pip install -r requirements.txt
```

---

## 3. Alternative Setup with Standard Python `pip`

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 4. Environment Variables Configuration

Create a `.env` file in the root directory (optional; default values are pre-configured):

```ini
SECRET_KEY=super-secret-enterprise-memo-jwt-key-2026-production
DATABASE_URL=sqlite:///./memo_system.db
UPLOAD_DIR=./uploads
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

---

## 5. Initialize & Seed Database

The application automatically seeds rich enterprise demonstration data on initial startup. To explicitly seed or reset the database at any time:

```powershell
uv run python -m app.seed
```

---

## 6. Start the Web Application

Launch the local web server:

```powershell
uv run python run.py
```

The application will be accessible at:
👉 **`http://127.0.0.1:8000`**

---

## 7. Run Automated Tests

To execute the test suite (testing auth, tenant isolation, sequential workflows, delegation, version snapshots, and PDF export):

```powershell
uv run pytest -v
```

---

## 8. Pre-Configured Enterprise Demonstration Accounts

| Organization | Role | Name | Email | Password |
|---|---|---|---|---|
| **Acme Corporation** | Org Admin | Sarah Jenkins | `admin@acmecorp.com` | `password123` |
| **Acme Corporation** | Dept Head (Engineering) | David Vance | `head.eng@acmecorp.com` | `password123` |
| **Acme Corporation** | Finance Manager | Rachel Green | `finance.mgr@acmecorp.com` | `password123` |
| **Acme Corporation** | Director of Operations | Marcus Sterling | `director@acmecorp.com` | `password123` |
| **Acme Corporation** | Chief Executive Officer (CEO) | Eleanor Vance | `ceo@acmecorp.com` | `password123` |
| **Acme Corporation** | Senior Software Engineer | Alex Morgan | `alex.morgan@acmecorp.com` | `password123` |
| **Acme Corporation** | Operations Specialist | Jessica Taylor | `jessica.taylor@acmecorp.com` | `password123` |
| **Nexus Financial Group** | Managing Director / Admin | Jonathan Hayes | `admin@nexusgroup.com` | `password123` |
| **Nexus Financial Group** | Principal Strategist | Victoria Price | `lead.analyst@nexusgroup.com` | `password123` |

> 💡 **Tip:** Use the **Demo Switcher** dropdown button in the top navigation bar for one-click instant login between all roles during grading!
