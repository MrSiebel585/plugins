#!/usr/bin/env python3
"""
MCP Bridge Plugin for offensivectl
Exposes framework workspace, tool execution, and recon telemetry via Model Context Protocol.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Any

# Ensure parent and core plugins are reachable
sys.path.append(str(Path(__file__).parent.resolve()))
from apt_integrator import AptToolIntegrator

logger = logging.getLogger("offensivectl.plugins.mcp")

class OffensiveMCPBridge:
    def __init__(self, workspace_path: str = "/opt/offensive/workspace"):
        self.workspace = Path(workspace_path)
        self.integrator = AptToolIntegrator(workspace_path=str(self.workspace))
        # Pre-scan system tools upon initialization
        self.integrator.scan_installed_tools()

    def handle_request(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        """Handles incoming MCP-compatible JSON-RPC style tool/resource requests."""
        method = request_payload.get("method")
        params = request_payload.get("params", {})
        req_id = request_payload.get("id", 1)

        try:
            if method == "tools/list":
                return self._list_tools(req_id)
            elif method == "tools/call":
                return self._call_tool(params, req_id)
            elif method == "resources/list":
                return self._list_resources(req_id)
            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                    "id": req_id
                }
        except Exception as e:
            logger.error(f"MCP Bridge error on method {method}: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": req_id
            }

    def _list_tools(self, req_id: int) -> dict[str, Any]:
        """Exposes discovered apt tools and workspace utilities as MCP tools."""
        tools = []
        for name, info in self.integrator.discovered_tools.items():
            tools.append({
                "name": f"run_{name}",
                "description": f"Execute system tool {name} ({info['category']}) safely within workspace.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": f"Command-line arguments for {name}"
                        }
                    },
                    "required": ["args"]
                }
            })
        return {"jsonrpc": "2.0", "result": {"tools": tools}, "id": req_id}

    def _call_tool(self, params: dict[str, Any], req_id: int) -> dict[str, Any]:
        """Executes a requested MCP tool wrapper."""
        tool_call_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        if not tool_call_name.startswith("run_"):
            return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid tool naming convention"}, "id": req_id}
        
        tool_name = tool_call_name.replace("run_", "")
        args = arguments.get("args", [])

        if tool_name not in self.integrator.discovered_tools:
            return {"jsonrpc": "2.0", "error": {"code": -32602, "message": f"Tool '{tool_name}' not available."}, "id": req_id}

        # Execute tool and capture exit code (stdout/stderr handling can be piped to workspace log)
        tool_info = self.integrator.discovered_tools[tool_name]
        import subprocess
        cmd = [tool_info["path"]] + args
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            output_data = {
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr
            }
            return {"jsonrpc": "2.0", "result": {"content": [{"type": "text", "text": json.dumps(output_data)}]}, "id": req_id}
        except Exception as e:
            return {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": req_id}

    def _list_resources(self, req_id: int) -> dict[str, Any]:
        """Exposes workspace subdirectories as accessible MCP resources."""
        resources = []
        for p in self.workspace.glob("**/*"):
            if p.is_file():
                resources.append({
                    "uri": f"file://{p}",
                    "name": str(p.relative_to(self.workspace)),
                    "mimeType": "application/octet-stream"
                })
        return {"jsonrpc": "2.0", "result": {"resources": resources}, "id": req_id}

if __name__ == "__main__":
    bridge = OffensiveMCPBridge()
    # Simple CLI test of MCP resource listing
    print(json.dumps(bridge.handle_request({"method": "tools/list", "id": 1}), indent=2))
