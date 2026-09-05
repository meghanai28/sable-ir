import subprocess
import os

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError("Executable is disallowed")
    
    cmd = [executable] + arguments
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.stdout
