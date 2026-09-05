import subprocess
import sys

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError(f"Disallowed executable: {executable}")
    
    cmd = [executable] + arguments
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout
