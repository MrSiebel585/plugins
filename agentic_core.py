#!/usr/bin/env python3
"""
Agentic AI Agent Core Plugin for offensivectl
Drives autonomous, multi-step tool execution loops using local Ollama models.
"""

import sys
import json
import requests
from pathlib import Path
import logging

sys.path.append(str(Path(__file__).parent.resolve()))
from apt_integrator import AptToolIntegrator

logger = logging.getLogger("offensivectl.plugins.agentic")

class OffensiveAgent:
    def __init__(self, model_name: str = "qwen2.5:1.5b", workspace_path: str = "/opt/offensive/workspace"):
        self.model_name = model_name
        self.workspace = Path(workspace_path)
        self.integrator = AptToolIntegrator(workspace_path=str(self.workspace))
        self.integrator.scan_installed_tools()
        self.ollama_url = "http://localhost:11434/api/generate"

    def _query_ollama(self, prompt: str) -> str:
        """Queries the local Ollama instance for reasoning and step generation."""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }
        try:
            response = requests.post(self.ollama_url, json=payload, timeout=60)
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception as e:
            logger.error(f"Ollama connection error: {e}")
        return ""

    def run_agentic_loop(self, objective: str, max_steps: int = 3) -> None:
        """Executes an autonomous plan-execute-evaluate loop toward a target security objective."""
        print(f"\n[*] Starting Agentic Loop for Objective: '{objective}'")
        print(f"[*] Available Discovered Tools: {list(self.integrator.discovered_tools.keys())}\n")

        context_history = f"Objective: {objective}\n"

        for step in range(1, max_steps + 1):
            print(f"--- Step {step} of {max_steps} ---")
            
            # Construct prompt for the local LLM agent
            prompt = (
                f"{context_history}\n"
                f"You have access to these security tools: {list(self.integrator.discovered_tools.keys())}.\n"
                f"Determine the next single command to execute as a JSON object with keys: "
                f"'tool' (name of tool or 'DONE' if finished), and 'args' (list of string arguments).\n"
                f"Example: {{\"tool\": \"nmap\", \"args\": [\"-p80\", \"127.0.0.1\"]}}\n"
                f"Respond ONLY with valid JSON."
            )

            response_text = self._query_ollama(prompt)
            print(f"[AI Reasoning Output]:\n{response_text}\n")

            try:
                # Extract JSON action block
                if "{" in response_text and "}" in response_text:
                    json_str = response_text[response_text.find("{"):response_text.rfind("}")+1]
                    action = json.loads(json_str)
                else:
                    print("[-] Failed to parse agent action JSON.")
                    break

                tool = action.get("tool")
                args = action.get("args", [])

                if tool == "DONE" or not tool:
                    print("[+] Agentic objective completed or terminated.")
                    break

                print(f"[*] Agent executing tool: {tool} with args: {args}")
                
                # Execute through apt integrator and capture output
                if tool in self.integrator.discovered_tools:
                    tool_info = self.integrator.discovered_tools[tool]
                    import subprocess
                    cmd = [tool_info["path"]] + args
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    
                    execution_result = f"Exit Code: {res.returncode}\nStdout:\n{res.stdout}\nStderr:\n{res.stderr}"
                    print(f"[{tool} Output Preview]:\n{res.stdout[:500]}...\n")
                    
                    context_history += f"\nExecuted: {tool} {' '.join(args)}\nResult:\n{execution_result}\n"
                else:
                    print(f"[-] Tool '{tool}' not found in registered tools.")
                    context_history += f"\nAttempted tool '{tool}' which was unavailable.\n"

            except json.JSONDecodeError:
                print("[-] JSON decoding error from agent response.")
                break
            except Exception as e:
                print(f"[-] Execution error: {e}")
                break

if __name__ == "__main__":
    # Test agent with a sample recon objective using local Ollama
    agent = OffensiveAgent(model_name="qwen2.5:1.5b")
    agent.run_agentic_loop(objective="Scan localhost for active ports using nmap", max_steps=2)
