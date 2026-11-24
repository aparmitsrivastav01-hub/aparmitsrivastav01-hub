#!/usr/bin/env python3
import json, os
from datetime import datetime, timezone
from pathlib import Path
import requests

username = os.getenv("GITHUB_USERNAME", "aparmitsrivastav01-hub")
url = f"https://github-contributions-api.jogruber.de/v4/{username}?y=last"
response = requests.get(url, timeout=30)
response.raise_for_status()
payload = response.json()
payload["fetched_at"] = datetime.now(timezone.utc).isoformat()
out = Path("data/contributions.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(f"Saved {len(payload.get('contributions', []))} contribution days")
