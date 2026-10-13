# ACCESS2WORK — Full-Stack MVP

**Verified Ability. Prepared Employers. Sustainable Employment.**

A full-stack prototype inspired by the ACCESS2WORK Yuva Hackathon presentation. It supports separate candidate and employer accounts, candidate profiles, employer readiness self-assessment, job listings, applications, and application status updates.

## Features

- Candidate and employer registration and login
- Password hashing with Werkzeug
- SQLite database with foreign-key constraints
- Candidate Ability Passport profile (skills are explicitly self-reported until assessed)
- Employer Readiness Index checklist (self-assessment, not certification)
- Employers can post and manage their own jobs
- Candidates can browse roles and apply once per job
- Employers can update application status
- Responsive interface and accessibility basics (skip link, labels, keyboard focus, semantic structure)
- Role-based route checks and parameterized SQL queries

## Requirements

- Python 3.10+
- pip

## Run locally

### Windows (PowerShell)

```powershell
cd ACCESS2WORK_FullStack
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SECRET_KEY = "replace-this-with-a-long-random-secret"
py app.py
```

### Windows (Command Prompt)

```bat
cd ACCESS2WORK_FullStack
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set SECRET_KEY=replace-this-with-a-long-random-secret
py app.py
```

Open **http://127.0.0.1:5000** in your browser. The SQLite database is created automatically on first run.

## Demo flow

1. Register as a **Candidate** with one email.
2. Complete the Ability Passport profile.
3. Sign out and register a separate **Employer** account using another email.
4. Complete the employer readiness checklist and post a job.
5. Sign back in as the candidate and apply.
6. Sign in as the employer and update the application status.

## Project structure

```text
ACCESS2WORK_FullStack/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── register.html
│   ├── login.html
│   ├── candidate_dashboard.html
│   ├── employer_dashboard.html
│   ├── candidate_profile.html
│   ├── employer_profile.html
│   ├── jobs.html
│   ├── job_detail.html
│   ├── create_job.html
│   └── error.html
└── static/
    └── style.css
```

## Important limitations before public deployment

This is a learning/demo MVP, not a production-ready employment service.

- Set a strong random `SECRET_KEY` using environment variables.
- Use HTTPS and secure cookies in production.
- Add CSRF protection (for example Flask-WTF), rate limiting, email verification, password reset, audit logging, backups and a production WSGI server before public deployment.
- Accessibility preferences may contain sensitive information. Use synthetic data for demos, collect only necessary data, define access/retention rules, and get appropriate consent before real use.
- Candidate skills and employer readiness are self-reported in this MVP; no practical skill assessment, independent employer audit, official verification badge, real matching algorithm, or 3/6-month retention automation is implemented yet.
- SQLite is suitable for a local demo. Use managed PostgreSQL for a multi-user production deployment.
- GitHub Pages cannot run Flask/Python. Deploy the backend to a Python-capable host and configure its environment variables; deploy the database on persistent storage.

## Hackathon context

Based on the ACCESS2WORK presentation for Yi Future 6.0 | Yi YUVA | Yi Connect, track **Employment for Persons with Disabilities**. The proposed pilot in the presentation focuses on Coimbatore and nearby Tier 2/3 areas. Targets in the presentation are proposed targets, not results achieved by this code.
