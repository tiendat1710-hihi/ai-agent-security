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
  
NUM_PREDICT = 512   # so token toi da moi lan model tra loi (256 de bi cat JSON)

# So lop day len GPU. Ollama 0.40.x uoc luong VRAM qua tay tren card 4GB
# (RTX 2050 chi ~3.2GB trong) -> nhoi qua nhieu lop -> cudaMalloc fail giua
# chung -> runner crash (500/ConnectionError). Khong che de khong bao gio tran:
#   0   = chay THUAN CPU: on dinh tuyet doi, khong bao gio crash VRAM, cham hon.
#   N>0 = day N lop len GPU (vd 12-15 cho model 3B), phan con lai chay CPU.
#   None= de Ollama tu quyet (hanh vi cu, de bi tran tren card 4GB).
# GPU da chay on dinh sau khi cai lai Ollama -> de None (GPU tu dong).
# Neu sau nay lai bi 500/cudaMalloc tren card 4GB, dat NUM_GPU = 12 (roi ha dan)
# de khong che so lop GPU, hoac 0 de chay thuan CPU.
NUM_GPU = None