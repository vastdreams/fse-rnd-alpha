"""AI configuration - provider, model names, rate limits."""
from config.settings import get_settings

settings = get_settings()

OPENAI_API_KEY = settings.OPENAI_API_KEY
GPT_MODEL = settings.GPT_MODEL or "gpt-5.1"  # Default to gpt-5.1 (latest) if not set
MAX_TOKENS = 16000  # Increased for GPT-5.1 comprehensive extraction
TEMPERATURE = 0.0  # Low temperature for extraction tasks (deterministic)
REQUEST_TIMEOUT = 180  # Increased timeout for GPT-5.1 complex extractions
