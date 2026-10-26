#!/usr/bin/env python3
"""
Alias Learner Plugin for offensivectl
Intelligently mines shell history using local Ollama models to discover
reusable complex one-liners and suggests clean, non-hyphenated aliases.
"""

import os
import sys
import re
import json
import requests
from pathlib import Path
import logging

logger = logging.getLogger("offensivectl.plugins.alias_learner")

class AliasLearner:
    def __init__(self, model_name: str = "qwen2.5:1.5b", history_path: str = None):
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434/api/generate"
        if not history_path:
            home = Path.home()
            zsh_hist = home / ".zsh_history"
            bash_hist = home / ".bash_history"
            self.history_path = zsh_hist if zsh_hist.exists() else bash_hist
        else:
            self.history_path = Path(history_path)

    def extract_recent_commands(self, limit: int = 300) -> list[str]:
        if not self.history_path.exists():
            return []
        commands = []
        try:
            with open(self.history_path, "rb") as f:
                content = f.read().decode("utf-8", errors="ignore")
            for line in content.splitlines():
                if ";" in line and "(: " in line or line.startswith(": "):
                    parts = line.split(";", 1)
                    if len(parts) > 1:
                        commands.append(parts[1].strip())
                else:
                    commands.append(line.strip())
            return list(dict.fromkeys([c for c in commands if c and len(c) > 5]))[-limit:]
        except Exception:
            return []

    def mine_one_liners(self) -> list[dict]:
        cmds = self.extract_recent_commands(limit=250)
        if not cmds:
            return []
        prompt = (
            "You are an expert Linux systems engineer and security scripter. "
            "Review the following shell history commands and identify 5-10 useful one-liners "
            "that deserve single-word aliases (strictly NO hyphens, e.g., 'ports', 'kick', 'intel').\n\n"
            "Commands:\n" + "\n".join(cmds[-150:]) + "\n\n"
            "Return ONLY a valid JSON list of objects with keys: 'alias', 'command', 'reason'."
        )
        payload = {"model": self.model_name, "prompt": prompt, "stream": False}
        try:
            res = requests.post(self.ollama_url, json=payload, timeout=60)
            if res.status_code == 200:
                text = res.json().get("response", "").strip()
                if "[" in text and "]" in text:
                    return json.loads(text[text.find("["):text.rfind("]") + 1])
        except Exception:
            pass
        return []

    def suggest_and_apply(self):
        suggestions = self.mine_one_liners()
        if not suggestions:
            print("[-] No alias suggestions generated.")
            return
        for idx, item in enumerate(suggestions, 1):
            print(f" [{idx}] Alias: {item.get('alias')} => {item.get('command')}")

if __name__ == "__main__":
    AliasLearner().suggest_and_apply()
