# AaganshikshaPortal Project

## Setup and Run Instructions

### 1. Create and activate a virtual environment (optional but recommended)

On Windows:
```
python -m venv venv
venv\Scripts\activate
```

On Linux/macOS:
```
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```
pip install email-validator flask flask-login flask-sqlalchemy gunicorn psycopg2-binary flask-wtf reportlab
```

### 3. Run the project

- Development mode (with auto-reload):
```
python main.py
```

- Production mode (using gunicorn):
```
gunicorn --bind 0.0.0.0:5000 --reload main:app
```

The application will be accessible at http://localhost:5000
