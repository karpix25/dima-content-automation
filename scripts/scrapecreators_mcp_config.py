from __future__ import annotations

import json
import os

from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    api_key = (os.getenv("SCRAPECREATORS_API_KEY") or "").strip() or "PUT_YOUR_SCRAPECREATORS_API_KEY_HERE"
    config = {
        "mcpServers": {
            "scrape-creators": {
                "command": "npx",
                "args": ["@scrape-creators/mcp"],
                "env": {
                    "SCRAPECREATORS_API_KEY": api_key,
                },
            }
        }
    }
    print(json.dumps(config, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
