from pathlib import Path

# =========================
# DOSYA YOLLARI
# =========================
BASE_DIR = Path(__file__).resolve().parent
MEMORY_DIR = BASE_DIR / "memory"
MEMORY_FILE = MEMORY_DIR / "memory.json"
DATABASE_FILE = MEMORY_DIR / "klis_memory.db"

MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# LM STUDIO AYARLARI
# =========================
API_BASE_URL = "http://localhost:1235/v1"
API_KEY = "lm-studio"
MODEL_NAME = "qwen3.6@iq4_nl" # LM studio içinde yüklü olan asıl ID'yi buraya yazıyoruz
TEMPERATURE = 0.7