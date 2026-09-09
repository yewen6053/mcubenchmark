# -*- coding: utf-8 -*-
"""Smoke test for the proxy endpoint: plain generation + json_schema structured output."""
import os
import sys
import time

import anthropic

MODEL = os.environ.get("BENCH_MODEL", "claude-fable-5")
client = anthropic.Anthropic(timeout=300.0, max_retries=1)  # reads ANTHROPIC_AUTH_TOKEN / ANTHROPIC_BASE_URL

print(f"base_url = {client.base_url}")
print(f"model    = {MODEL}")

# ---- test 1: plain streaming generation ----
t0 = time.time()
try:
    with client.messages.stream(
        model=MODEL,
        max_tokens=2000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": "Reply with exactly: MCU-BENCH-OK"}],
    ) as stream:
        msg = stream.get_final_message()
    text = "".join(b.text for b in msg.content if b.type == "text")
    print(f"[gen] {time.time()-t0:.1f}s stop={msg.stop_reason} model={msg.model}")
    print(f"[gen] usage in={msg.usage.input_tokens} out={msg.usage.output_tokens}")
    print(f"[gen] text: {text[:100]!r}")
except anthropic.APIStatusError as e:
    print(f"[gen] FAILED {e.status_code}: {e.message}")
    sys.exit(1)

# ---- test 2: json_schema structured output (for the judge phase) ----
t0 = time.time()
schema = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "fail"]},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
    "additionalProperties": False,
}
try:
    with client.messages.stream(
        model=MODEL,
        max_tokens=2000,
        output_config={
            "effort": "low",
            "format": {"type": "json_schema", "schema": schema},
        },
        messages=[{"role": "user", "content": "Does 2+2 equal 4? Answer as the schema."}],
    ) as stream:
        msg = stream.get_final_message()
    text = "".join(b.text for b in msg.content if b.type == "text")
    print(f"[json] {time.time()-t0:.1f}s stop={msg.stop_reason}")
    print(f"[json] text: {text[:200]!r}")
    import json
    print(f"[json] parsed: {json.loads(text)}")
except anthropic.APIStatusError as e:
    print(f"[json] structured output not supported by proxy? {e.status_code}: {e.message}")
    print("[json] will fall back to prompt-based JSON in judge phase")

print("SMOKE TEST DONE")
