"""Standalone Gemini check: one short prompt with the configured key and model.

    python backend/scripts/test_gemini.py

Prints the reply or the exact error. Never prints the API key (it is redacted from errors).
Exit code 0 = Gemini works, 1 = it does not.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config  # noqa: E402


def main():
    key = Config.GEMINI_API_KEY
    print(f"GEMINI_MODEL = {Config.GEMINI_MODEL}")
    print(f"GEMINI_API_KEY set: {'yes' if key else 'no'} (length {len(key)})")
    if not key:
        print("RESULT: FAIL - GEMINI_API_KEY is empty in backend/.env")
        return 1

    from google import genai

    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents="Reply with exactly: Gemini OK",
        )
        print("REPLY:", (response.text or "").strip()[:200])
        print("RESULT: PASS")
        return 0
    except Exception as exc:
        message = str(exc).replace(key, "<redacted>")
        print(f"ERROR: {type(exc).__name__}: {message}")
        print("RESULT: FAIL")
        return 1


if __name__ == "__main__":
    sys.exit(main())
