"""Make the repository root importable and keep every test offline (the stub model, no Ollama)."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ["DW_MODEL_PATH"] = "stub"


def pytest_configure(config):
    config.addinivalue_line("markers", "invariant: passes on the starter as well as on the reference tree")
