# Library Management System (LMS)

Flask + Jinja2 + SQLite3 implementation of the LMS using a strict three-layer architecture:

- **Presentation Layer**: `app/routes` + `app/templates`
- **Business Logic Layer**: `app/services`
- **Data Layer**: `app/models.py` (SQLAlchemy)

This implementation is aligned to the approved design documents:

- Class Diagram (exact classes, attributes, method signatures, relationships, multiplicities)
- Three critical Sequence Diagrams (Member search/borrow, Librarian add book, Admin overdue report)

---

## 1) Setup Instructions

### A. Create and activate virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

### B. Install dependencies

```bash
pip install -r requirements.txt
```

### C. Run the app

Option 1:

```bash
python run.py
```

Option 2 (`flask run`):

Windows PowerShell:

```bash
$env:FLASK_APP="run.py"
flask run
```

Linux/macOS:

```bash
export FLASK_APP=run.py
flask run
```

App default URL: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 2) Seed Test Users

Before login in local run mode, seed the default users once:

```bash
python seed.py
```

The script is idempotent (it skips already-existing usernames).

---

## 3) Test Accounts

Use these sample credentials after inserting users into the database (or via test fixture data):

- **Member**
  - username: `member1`
  - password: `member123`
- **Librarian**
  - username: `librarian1`
  - password: `librarian123`
- **Administrator**
  - username: `admin1`
  - password: `admin123`

> Passwords are stored as Werkzeug hashes in the database.

---

## 4) Design Consistency Note

This LMS codebase is intentionally constrained to preserve **100% design-code consistency** with:

- the approved UML Class Diagram (names and signatures such as `searchBooks`, `borrowBook`, `addBook`, `generateReport`, etc.)
- the approved Sequence Diagrams for:
  1. Member login/search/borrow
  2. Librarian login/add book
  3. Administrator login/generate overdue report

No route performs direct database operations; all route actions call service methods.

---

## 5) Run Tests (Pytest)

```bash
pytest -q
```

The tests cover end-to-end validation of the three critical sequence flows and role access expectations:

- Member search + borrow + return
- Librarian add book (with validation)
- Administrator overdue report generation

---

## 6) Project Structure

```text
lms_project/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── routes/
│   ├── services/
│   └── templates/
├── tests/
├── requirements.txt
├── run.py
└── README.md
```
