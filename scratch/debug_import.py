import sys
import traceback

sys.path.append("/app")

try:
    print("Import Success")
except Exception:
    traceback.print_exc()
