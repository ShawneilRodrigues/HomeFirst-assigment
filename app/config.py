"""Settings loaded from environment."""
import os

from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SUPABASE_PROJECT_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")
DATABASE_URL = os.getenv(
	"DATABASE_URL",
	"postgresql+psycopg://postgres:[YOUR-PASSWORD]@db.mqmncljqhlbavwfobmkr.supabase.co:5432/postgres",
)
CHROMADB_PATH = os.getenv("CHROMADB_PATH", "./tmp/chromadb")
DEFAULT_INTEREST_RATE = float(os.getenv("DEFAULT_INTEREST_RATE", "12.0"))
DEFAULT_TENURE_MONTHS = int(os.getenv("DEFAULT_TENURE_MONTHS", "240"))
FOIR_LIMIT = float(os.getenv("FOIR_LIMIT", "0.50"))
LEAD_SCORE_HANDOFF_THRESHOLD = int(os.getenv("LEAD_SCORE_HANDOFF_THRESHOLD", "8"))
SARVAM_TTS_SPEAKER = os.getenv("SARVAM_TTS_SPEAKER", "rupali")
SARVAM_TTS_MODEL = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3")
