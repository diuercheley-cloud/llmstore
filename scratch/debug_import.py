import traceback
import sys
import os

sys.path.append("/app")

try:
    from app.main import app
    print("Import Success")
except Exception:
    traceback.print_exc()
