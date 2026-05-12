"""
test_groq.py
────────────────────────────────────────────────────────────────────────────────
Run this FIRST to verify your Groq API key works before running the pipeline.

Usage:
    python test_groq.py

What it checks:
  1. .env file exists and GROQ_API_KEY is set
  2. groq package is installed
  3. API key is valid (makes a real test call)
  4. Model is available on your account
"""

import os
import sys
from pathlib import Path

# ─── Step 0: Resolve project root ────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

print("=" * 60)
print("  Business Health Monitor — Groq API Diagnostic")
print("=" * 60)

# ─── Step 1: Check .env file ──────────────────────────────────────────────────
env_path = ROOT / ".env"
print(f"\n[1] Checking .env file at {env_path} ...")

if not env_path.exists():
    print("  ❌ .env file NOT FOUND")
    print("\n  FIX: Create it now:")
    print(f"     copy {ROOT}\\.env.example {ROOT}\\.env")
    print("     Then open .env and add your GROQ_API_KEY")
    print("\n  Get a FREE key at: https://console.groq.com/keys")
    sys.exit(1)
else:
    print("  ✅ .env file found")

# ─── Step 2: Load .env ────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(env_path, override=True)
    print("[2] ✅ python-dotenv loaded .env")
except ImportError:
    print("[2] ❌ python-dotenv not installed — run: pip install python-dotenv")
    sys.exit(1)

# ─── Step 3: Check API key ────────────────────────────────────────────────────
api_key = os.environ.get("GROQ_API_KEY", "").strip()
print(f"\n[3] Checking GROQ_API_KEY ...")

if not api_key:
    print("  ❌ GROQ_API_KEY is EMPTY in your .env file")
    print("\n  FIX: Open .env and set:")
    print("     GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx")
    print("\n  Get a FREE key at: https://console.groq.com/keys")
    sys.exit(1)
elif api_key == "your_groq_api_key_here":
    print("  ❌ GROQ_API_KEY is still the placeholder value — you haven't filled it in")
    print("\n  FIX: Replace 'your_groq_api_key_here' with your actual key")
    print("  Get a FREE key at: https://console.groq.com/keys")
    sys.exit(1)
elif not api_key.startswith("gsk_"):
    print(f"  ⚠️  Key found but looks unusual (doesn't start with 'gsk_'): {api_key[:8]}...")
    print("  Groq keys usually start with 'gsk_' — double check it's correct")
else:
    print(f"  ✅ GROQ_API_KEY found: {api_key[:8]}...{api_key[-4:]}")

# ─── Step 4: Check groq package ───────────────────────────────────────────────
print(f"\n[4] Checking groq package ...")
try:
    import groq
    print(f"  ✅ groq package installed (version: {groq.__version__})")
except ImportError:
    print("  ❌ groq package NOT installed")
    print("\n  FIX: pip install groq")
    sys.exit(1)

# ─── Step 5: Make a real API call ─────────────────────────────────────────────
print(f"\n[5] Making test API call to Groq ...")
MODEL = "llama-3.1-8b-instant"   # fast, free, always available

try:
    client = groq.Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=50,
        messages=[{"role": "user", "content": "Reply with exactly: GROQ_OK"}],
    )
    reply = response.choices[0].message.content.strip()
    print(f"  ✅ API call successful! Model reply: '{reply}'")
    print(f"  ✅ Model used: {MODEL}")
except groq.AuthenticationError:
    print("  ❌ Authentication failed — your API key is invalid or expired")
    print("  FIX: Get a new key at https://console.groq.com/keys")
    sys.exit(1)
except groq.RateLimitError:
    print("  ⚠️  Rate limit hit — your key works but you've hit the free tier limit")
    print("  The pipeline will use the fallback report. Try again in a minute.")
except Exception as exc:
    print(f"  ❌ Unexpected error: {type(exc).__name__}: {exc}")
    sys.exit(1)

# ─── Step 6: Update config.yaml to use the working model ─────────────────────
print(f"\n[6] Checking config.yaml model setting ...")
import yaml
config_path = ROOT / "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

current_model = config["ai"]["model"]
if current_model != MODEL:
    print(f"  ⚠️  config.yaml uses '{current_model}' — updating to '{MODEL}' (more reliable)")
    content = config_path.read_text()
    content = content.replace(f'model: "{current_model}"', f'model: "{MODEL}"')
    config_path.write_text(content)
    print(f"  ✅ config.yaml updated to use model: {MODEL}")
else:
    print(f"  ✅ config.yaml model is already '{MODEL}'")

# ─── All good ────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  ✅ ALL CHECKS PASSED — Groq AI is ready!")
print("=" * 60)
print("\nNow run the full pipeline:")
print("  python run_pipeline.py --mode full")
print("\nThen launch the dashboard:")
print("  streamlit run app/dashboard.py")
