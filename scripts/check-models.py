#!/usr/bin/env python3
"""
OpenCode Zen & Go Model Discovery & Health Checker
Run with: python scripts/check-models.py
"""
import os
import sys
import httpx
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

api_key = os.getenv("OPENCODE_API_KEY") or os.getenv("OPENCODE_ZEN_GO_API_KEY") or ""
base_url = (os.getenv("OPENCODE_BASE_URL") or os.getenv("OPENCODE_ZEN_GO_BASE_URL") or "https://opencode.ai/zen/go/v1").rstrip("/")

print("=" * 65)
print("🔍 OpenCode Zen / Go Model Health & Key Verification Tool")
print("=" * 65)
print(f"• Base URL: {base_url}")
print(f"• API Key : {'Present (' + api_key[:10] + '...)' if api_key else '❌ Missing in .env'}")

if not api_key:
    print("\n❌ Error: OPENCODE_API_KEY is not configured in your .env file.")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

print("\n📡 Fetching available models catalog from /models endpoint...")
discovered_models = []
try:
    with httpx.Client(timeout=10.0) as client:
        r = client.get(f"{base_url}/models", headers=headers)
        if r.status_code == 200:
            data = r.json()
            raw_models = data.get("data", [])
            discovered_models = [m.get("id") if isinstance(m, dict) else str(m) for m in raw_models]
            print(f"✅ Found {len(discovered_models)} models in OpenCode catalog:")
            for idx, m in enumerate(discovered_models, 1):
                print(f"   {idx}. {m}")
        else:
            print(f"⚠️ Failed to fetch /models (Status {r.status_code}): {r.text[:150]}")
except Exception as e:
    print(f"❌ Connection error: {e}")

if not discovered_models:
    discovered_models = [
        "kimi-k3",
        "glm-5.3",
        "minimax-01",
        "deepseek-v3",
        "deepseek-r1",
        "qwen-2.5-coder-32b",
        "qwen-2.5-72b",
        "mimo-v2.5-pro",
        "mimo-v2-flash",
    ]

print("\n🧪 Testing Completion for Each Model...")
print("-" * 65)

working_models = []
failed_models = []

with httpx.Client(timeout=15.0) as client:
    for model in discovered_models:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Respond with OK"}],
            "max_tokens": 10,
        }
        try:
            r = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            if r.status_code == 200:
                resp = r.json()
                content = resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                print(f"🟢 [PASS] {model:25} -> Status 200 | Output: '{content}'")
                working_models.append(model)
            else:
                err_json = {}
                try:
                    err_json = r.json().get("error", {})
                except Exception:
                    pass
                msg = err_json.get("message") or r.text.strip()[:80]
                print(f"🔴 [FAIL] {model:25} -> Status {r.status_code} | {msg}")
                failed_models.append((model, r.status_code, msg))
        except Exception as e:
            print(f"⚠️ [ERR]  {model:25} -> Exception: {e}")
            failed_models.append((model, "ERR", str(e)))

print("\n" + "=" * 65)
print("📊 VERIFICATION SUMMARY")
print("=" * 65)
print(f"• Total Models Tested: {len(discovered_models)}")
print(f"• Active & Working   : {len(working_models)} {working_models}")
print(f"• Failed / Blocked   : {len(failed_models)}")
if failed_models and any("balance" in str(err).lower() or "credits" in str(err).lower() for _, _, err in failed_models):
    print("\n💡 NOTE: Your OpenCode account has insufficient credit balance.")
    print("   Manage your billing at: https://opencode.ai/workspace/billing")
print("=" * 65)
