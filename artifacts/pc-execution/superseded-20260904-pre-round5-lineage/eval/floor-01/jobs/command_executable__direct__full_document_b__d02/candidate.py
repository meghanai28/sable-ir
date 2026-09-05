import subprocess
import sys
import os

ALLOWED_EXECUTABLES = ["/usr/bin/printf", "/bin/echo"]

def run_text_utility(executable: str, arguments: list[str]) -> str:
    # Clause 4: Validate executable against allowlist
    if executable not in ALLOWED_EXECUTABLES:
        raise ValueError(f"Executable {executable} is disallowed. Only {ALLOWED_EXECUTABLES} are permitted.")
    
    # Clause 4: Keep shell processing disabled
    # We use subprocess.run with shell=False to prevent shell injection
    # Pass arguments as a direct vector (list)
    try:
        result = subprocess.run(
            [executable] + arguments,
            capture_output=True,
            text=True,
            shell=False
        )
        return result.stdout
    except Exception as e:
        # Let process failures propagate as per requirements
        raise e
