import subprocess
import sys

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError("Executable is disallowed")
    
    # Use subprocess with shell=False to prevent shell metacharacter injection
    # Pass arguments directly as a list to avoid command string construction
    process = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        check=True
    )
    return process.stdout
