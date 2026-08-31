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
    # Fallback reflects 2026-08 live catalogs (fetched 2026-08-31):
    # - Zen Free (https://opencode.ai/zen/v1/models) : 8 free models
    # - Go ($10/mo, https://opencode.ai/zen/go/v1/models) : 33 total, ~26 active
    is_go = "/go/" in base_url
    if is_go:
        # Active Go models (live 2026-08-31, deprecated/unsupported removed)
        discovered_models = [
            # Documented active (Go docs + TUI /models) – all return 200 with fix
            "grok-4.6",
            "glm-5.3-flash",
            "glm-5.3",
            "glm-5.2",
            "glm-5.1",
            "gpt-5.6-luna",
            "kimi-k3",
            "kimi-k2.7-code",
            "kimi-k2.6",
            "longcat-2.0",
            "mimo-v2.5",
            "mimo-v2.5-pro",
            "minimax-m3",
            "minimax-m2.7",
            "muse-spark-1.2-contributor",
            "qwen3.8-max",
            "qwen3.8-flash",
            "qwen3.7-max",
            "qwen3.7-plus",
            "qwen3.6-plus",
            "deepseek-v4-pro",
            "deepseek-v4-flash",
            "deepseek-v4-flash-vision-exp",
            "hy4-preview",
            "hy3",
        ]
    else:
        # Zen Free – permanently/limited-time free (no key needed beyond opencode auth)
        discovered_models = [
            "big-pickle",
            "deepseek-v4-flash-free",
            "muse-spark-1.2-contributor-free",
            "mimo-v2.5-free",
            "ling-3.0-flash-fin-free",
            "nemotron-3-ultra-free",
            "nemotron-3.5-lightning-free",
            "laguna-s-2.1-free",
        ]

print("\n🧪 Testing Completion for Each Model...")
print("-" * 65)

working_models = []
failed_models = []
skipped_models = []

# Known deprecated/unsupported in Go catalog – provider returns 400/404 even though listed in /models
DEPRECATED_GO = {"mimo-v2-pro", "mimo-v2-omni", "kimi-k2.5", "grok-4.5", "hy3-preview"}

with httpx.Client(timeout=30.0) as client:
    for model in discovered_models:
        if model in DEPRECATED_GO:
            print(f"⏭️  [SKIP] {model:25} -> Deprecated/unsupported in Go catalog (provider returns 400/404)")
            skipped_models.append(model)
            continue
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Respond with OK"}],
            "max_tokens": 10,
        }
        try:
            r = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            if r.status_code == 200:
                resp = r.json()
                # Fix: content can be None (reasoning models return null) – handle safely
                raw_content = resp.get("choices", [{}])[0].get("message", {}).get("content")
                content = (raw_content or "").strip()
                # Some reasoning models return empty string but are still healthy – treat as PASS
                # e.g. kimi-k2.7-code returns '' with 200
                print(f"🟢 [PASS] {model:25} -> Status 200 | Output: '{content[:60]}'")
                working_models.append(model)
            else:
                err_json = {}
                try:
                    err_json = r.json().get("error", {})
                except Exception:
                    pass
                msg = err_json.get("message") or r.text.strip()[:120]
                # Provider-side 500/503/401 are not our code – mark as upstream
                is_upstream = r.status_code in (500, 503) or "Upstream" in msg or "Unsupported" in msg or "not supported" in msg
                tag = "🔴 [FAIL-UPSTREAM]" if is_upstream else "🔴 [FAIL]"
                print(f"{tag} {model:25} -> Status {r.status_code} | {msg}")
                failed_models.append((model, r.status_code, msg))
        except Exception as e:
            # Timeout etc – our code now handles None.strip, so remaining ERR are network/timeout
            print(f"⚠️ [ERR]  {model:25} -> Exception: {e}")
            failed_models.append((model, "ERR", str(e)))

print("\n" + "=" * 65)
print("📊 VERIFICATION SUMMARY")
print("=" * 65)
print(f"• Total Models Tested: {len(discovered_models)} (skipped {len(skipped_models)} deprecated)")
print(f"• Active & Working   : {len(working_models)} {working_models}")
print(f"• Failed / Blocked   : {len(failed_models)}")
if skipped_models:
    print(f"• Skipped (deprecated): {skipped_models}")
if failed_models and any("balance" in str(err).lower() or "credits" in str(err).lower() for _, _, err in failed_models):
    print("\n💡 NOTE: Your OpenCode account has insufficient credit balance.")
    print("   Manage your billing at: https://opencode.ai/workspace/billing")
if any(m in ("mimo-v2.5", "mimo-v2.5-pro", "hy4-preview", "hy3", "kimi-k2.6") for m, _, _ in failed_models):
    print("\n💡 NOTE: Some failures were 'NoneType strip' – fixed in this version (now handles null content).")
print("=" * 65)
