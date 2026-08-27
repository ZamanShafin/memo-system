# Enterprise Inter-Office Memo Management System

A full-featured, secure, multi-tenant web application designed to digitize, streamline, and govern internal organizational communications, sequential multi-level approvals, reviews, and versioned feedback loops.

---

## 🏛️ System Features

- 🏢 **Strict Multi-Tenancy:** Complete data, user, and workflow isolation per organization (`Acme Corporation`, `Nexus Financial Group`, etc.).
- 🔄 **Sequential Workflow Engine:** Multi-step sequential approval paths (`Requester → Dept Head → Finance Manager → Director → CEO`) with out-of-order execution prevention.
- 🤝 **Workflow Authority Delegation:** Temporary delegation with timestamped *acting-on-behalf* audit logs.
- 📝 **Rich Text & Versioning:** Rich-text memo composer with automated version snapshotting (`v1`, `v2`) on resubmission.
- 📄 **Formal PDF Export:** Official corporate letterhead memo PDF generator via ReportLab with approval stamp history.
- 🔔 **Real-Time Notification Hub:** In-app notification center with unread counters.
- 📊 **Analytics & Reporting:** Interactive dashboards with Chart.js for KPIs, status distributions, and turnaround times.
- 🛡️ **Security & Compliance:** BCrypt password hashing, JWT sessions, server-side authorization, and immutable audit logs.
- ⚡ **Demo Switcher:** Instant one-click demo login across all roles and organizations.

---

## 🚀 Quick Start

### 1. Start the Server
```powershell
# Using uv (Recommended)
uv run python run.py

# Or using standard python
python run.py
```
Open your browser at: **`http://127.0.0.1:8000`**

### 2. Run Automated Tests
```powershell
uv run pytest -v
```

### 3. Package Source Code Archive
```powershell
uv run python package_source.py
```

---

## 👥 Pre-Configured Demonstration Accounts

All accounts use the password: `password123`

| Organization | Role | Name | Email |
|---|---|---|---|
| **Acme Corporation** | Org Admin | Sarah Jenkins | `admin@acmecorp.com` |
| **Acme Corporation** | Dept Head (Engineering) | David Vance | `head.eng@acmecorp.com` |
| **Acme Corporation** | Finance Manager | Rachel Green | `finance.mgr@acmecorp.com` |
| **Acme Corporation** | Director of Operations | Marcus Sterling | `director@acmecorp.com` |
| **Acme Corporation** | Chief Executive Officer (CEO) | Eleanor Vance | `ceo@acmecorp.com` |
| **Acme Corporation** | Senior Software Engineer | Alex Morgan | `alex.morgan@acmecorp.com` |
| **Acme Corporation** | Operations Specialist | Jessica Taylor | `jessica.taylor@acmecorp.com` |
| **Nexus Financial Group** | Managing Director / Admin | Jonathan Hayes | `admin@nexusgroup.com` |
| **Nexus Financial Group** | Principal Strategist | Victoria Price | `lead.analyst@nexusgroup.com` |

---

## 📚 Documentation Index

- 📖 [Comprehensive Project Documentation](docs/PROJECT_DOCUMENTATION.md)
- ⚙️ [Installation and Setup Guide](docs/INSTALLATION.md)
- 🤖 [AI Prompt & Response Development History](docs/AI_VIBE_CODING_LOG.md)

