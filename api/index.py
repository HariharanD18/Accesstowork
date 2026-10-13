import os
import sys

# Ensure root and package directories are on Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
APP_DIR = os.path.join(ROOT_DIR, "ACCESS2WORK_FullStack")

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from ACCESS2WORK_FullStack.app import app, init_db

# Initialize database tables on serverless startup
try:
    init_db()
except Exception:
    pass

# Vercel serverless entrypoint
handler = app
