#!/usr/bin/env python3
"""
Error Clipboard Sentinel Plugin for offensivectl
Automatically intercepts critical errors, tracebacks, and stderr during debugging
and pipes them directly to the system clipboard using xclip.
"""

import sys
import subprocess
import os
import select
from pathlib import Path
import logging

logger = logging.getLogger("offensivectl.plugins.error_xclip")

class ErrorClipboardSentinel:
    def __init__(self):
        self.xclip_available = self._check_xclip()

    def _check_xclip(self) -> bool:
        """Verifies if xclip is installed and available in the environment."""
        try:
            res = subprocess.run(["which", "xclip"], capture_output=True, text=True)
            return res.returncode == 0
        except Exception:
            return False

    def copy_to_clipboard(self, text: str) -> bool:
        """Pipes text directly into the system clipboard via xclip."""
        if not self.xclip_available:
            logger.warning("xclip is not installed or unavailable in this session.")
            return False

        try:
            process = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            process.communicate(input=text)
            return process.returncode == 0
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            return False

    def watch_and_execute(self, cmd: list[str]):
        """Executes a command, streams stdout normally, but captures stderr/errors and auto-xclips them."""
        print(f"[*] Sentinel active watching execution: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            stderr_buffer = []

            # Read outputs in real-time
            while True:
                reads = [process.stdout.fileno(), process.stderr.fileno()]
                ret = select.select(reads, [], [], 0.1)
                
                if not ret[0] and process.poll() is not None:
                    break

                for fd in ret[0]:
                    if fd == process.stdout.fileno():
                        line = process.stdout.readline()
                        if line:
                            sys.stdout.write(line)
                            sys.stdout.flush()
                    elif fd == process.stderr.fileno():
                        line = process.stderr.readline()
                        if line:
                            sys.stderr.write(line)
                            sys.stderr.flush()
                            stderr_buffer.append(line)

            process.wait()

            # If execution failed or stderr was captured, auto-xclip the error payload
            if process.returncode != 0 and stderr_buffer:
                error_text = "".join(stderr_buffer)
                success = self.copy_to_clipboard(error_text)
                if success:
                    print("\n[+] [Error Xclip Sentinel]: Critical stderr/traceback automatically copied to clipboard!")
                else:
                    print("\n[!] [Error Xclip Sentinel]: Command failed, but xclip pipe failed.")

            sys.exit(process.returncode)

        except Exception as e:
            print(f"[-] Sentinel execution error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    sentinel = ErrorClipboardSentinel()
    if len(sys.argv) > 1:
        # Run command passed as arguments
        sentinel.watch_and_execute(sys.argv[1:])
    else:
        print("Usage: error_xclip_plugin.py <command to watch [args...]>")
