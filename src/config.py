"""Configuration module for VoiceOps 2026 Capstone Project."""
import os
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_ROOT = PROJECT_ROOT / "Capstone_Project_Dataset_FTTT_2026"

KB_DIR = DATASET_ROOT / "kb"
DATA_DIR = DATASET_ROOT / "data"
PRACTICE_DIR = DATASET_ROOT / "practice"
TOOLS_DIR = DATASET_ROOT / "tools"

# Load .env file manually if python-dotenv is not installed
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# Environment settings
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_EMBED_MODEL = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")
GNANI_API_KEY = os.environ.get("GNANI_API_KEY", "")

# Domain Reference Rules
REFERENCE_DATE = "2026-10-20"  # Capstone Brief Rule: Today is 20 October 2026
COMPANY_NAME = "ZentroMart"
