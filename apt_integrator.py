#!/usr/bin/env python3
"""
Apt Integrator Core Plugin for offensivectl
Dynamically discovers and folds system apt-installed tools into the framework.
"""

import os
import subprocess
import shutil
from pathlib import Path
import logging

logger = logging.getLogger("offensivectl.plugins.apt")

# Common security tool binary prefixes/names to scan for
SECURITY_TOOLS = [
    # Recon & Scanning
    "nmap", "masscan", "netcat", "nc", "dnsrecon", "enum4linux", "amass", "nikto", "sqlmap",
    # Exploitation & Cracking
    "hydra", "john", "hashcat", "medusa", "aircrack-ng", "metasploit", "msfconsole",
    # Forensics & Analysis
    "wireshark", "tshark", "binwalk", "foremost", "volatility", "tcpdump", "strings",
    # System & Network Utilities
    "iptables", "nftables", "tcpdump", "tmux", "screen", "socat", "rsync", "sshfs"
]

class AptToolIntegrator:
    def __init__(self, workspace_path: str = "/opt/offensive/workspace"):
        self.workspace = Path(workspace_path)
        self.discovered_tools = {}

    def scan_installed_tools(self) -> dict:
        """Scans the system PATH for installed security binaries."""
        logger.info("Scanning system for apt-installed security tools...")
        self.discovered_tools.clear()

        for tool in SECURITY_TOOLS:
            binary_path = shutil.which(tool)
            if binary_path:
                self.discovered_tools[tool] = {
                    "path": binary_path,
                    "category": self._categorize_tool(tool)
                }
        
        logger.info(f"Successfully folded {len(self.discovered_tools)} system tools into offensivectl.")
        return self.discovered_tools

    def _categorize_tool(self, tool_name: str) -> str:
        recon = {"nmap", "masscan", "netcat", "nc", "dnsrecon", "enum4linux", "amass", "nikto", "sqlmap"}
        exploit = {"hydra", "john", "hashcat", "medusa", "aircrack-ng", "metasploit", "msfconsole"}
        forensics = {"wireshark", "tshark", "binwalk", "foremost", "volatility", "tcpdump", "strings"}
        
        if tool_name in recon:
            return "recon"
        elif tool_name in exploit:
            return "exploitation"
        elif tool_name in forensics:
            return "forensics"
        return "utilities"

    def execute_tool(self, tool_name: str, args: list[str]) -> int:
        """Executes a dynamically discovered tool safely within the framework environment."""
        if tool_name not in self.discovered_tools:
            print(f"[-] Error: Tool '{tool_name}' is not installed or not registered by the Apt Integrator.")
            return 1

        tool_info = self.discovered_tools[tool_name]
        cmd = [tool_info["path"]] + args
        
        print(f"[*] Executing [{tool_name}] -> {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd)
            return result.returncode
        except Exception as e:
            logger.error(f"Failed to execute {tool_name}: {e}")
            return 1

if __name__ == "__main__":
    integrator = AptToolIntegrator()
    tools = integrator.scan_installed_tools()
    for name, details in tools.items():
        print(f"  [+] {name:15} -> {details['path']} ({details['category']})")
