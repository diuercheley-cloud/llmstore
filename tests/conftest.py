import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "control_plane"
if ROOT.exists() and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
APP_ROOT = Path(__file__).resolve().parents[1]
if (APP_ROOT / "app").exists() and str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
