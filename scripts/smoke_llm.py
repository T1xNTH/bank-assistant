#!/usr/bin/env python3
"""Ping real aliases with synthetic input; never print keys or provider errors."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:4000")
    parser.add_argument("--models", nargs="+", default=["cloud-chat", "local-chat"])
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    headers = {"Content-Type": "application/json"}
    if key := os.getenv("LITELLM_MASTER_KEY"):
        headers["Authorization"] = f"Bearer {key}"
    failed = False
    for model in args.models:
        payload = {"model": model, "messages": [
            {"role": "user", "content": "Reply with the single word pong."}
        ], "max_tokens": 512}
        if model == "cloud-chat":
            # Gemini Flash variants do not all support the minimal/none level.
            payload["reasoning_effort"] = "low"
            payload["max_tokens"] = 2048
        request = urllib.request.Request(
            args.base_url.rstrip("/") + "/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=args.timeout) as response:
                result = json.load(response)
            content = result["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty answer")
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            code = f" HTTP {exc.code}" if isinstance(exc, urllib.error.HTTPError) else ""
            print(f"FAIL {model}:{code} {type(exc).__name__}", file=sys.stderr)
            failed = True
        else:
            print(f"PASS {model}: nonempty chat completion")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
