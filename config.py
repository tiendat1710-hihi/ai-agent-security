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

# So lop day len GPU (truyen thang vao options.num_gpu cua Ollama):
#   -1  = tu dong (Ollama tu uoc luong so lop vua VRAM) - dung khi GPU on dinh.
#    0  = ep THUAN CPU: on dinh tuyet doi, het crash VRAM card 4GB, cham hon.
#   N>0 = ep day dung N lop len GPU (vd 12-15 cho 3B) neu tu dong van bi tran.
# GPU chay on dinh -> -1 (tu dong). CPU qua cham. Neu lai bi 500/cudaMalloc
# tren card 4GB thi ha xuong N (vd 12 roi giam dan), hoac 0 de ep CPU.
NUM_GPU = 12
#------------lop 1 Guardrails: lam sach noi dung email truoc khi dua vao ngu canh.
ENABLE_L1 = False   # Lop 1 (loc HTML an + spotlighting) cho read_email
#------------lop 4 HITL: yeu cau duyet qua han -> tu dong Reject (giay)
HITL_TTL_SECONDS = 600
