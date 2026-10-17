from pathlib import Path

ROOT = Path(__file__).parent

# ---------- LLM ----------
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "dolphin-llama3:8b"
NUM_CTX = 4096
TEMPERATURE = 0.0

# ---------- Lab: hop thu ----------
INTERNAL_DOMAIN = "company.test"
INTERNAL_MAIL = {"smtp_host": "localhost", "smtp_port": 1025, "api": "http://localhost:8025"}
EXTERNAL_MAIL = {"smtp_host": "localhost", "smtp_port": 1026, "api": "http://localhost:8026"}

# ---------- Lab: co so du lieu ----------
DB_PATH = ROOT / "lab" / "company.db"
MANIFEST_PATH = ROOT / "lab" / "secrets_manifest.json"
SEED = 42  # co dinh de du lieu gia luon giong nhau moi lan sinh

# ---------- Log ----------
LOG_DIR = ROOT / "experiments" / "results_raw" / "logs"