import os
import sys
from pathlib import Path

# Add project root directory to python path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.database import engine, Base
from app.seed import seed_database
from app.main import app

# Ensure database tables and seed data are initialized on serverless invocation
try:
    Base.metadata.create_all(bind=engine)
    seed_database()
except Exception as e:
    print(f"Serverless initialization note: {e}")
