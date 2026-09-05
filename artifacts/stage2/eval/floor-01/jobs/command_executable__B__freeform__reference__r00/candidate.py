import subprocess
import os

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ['/usr/bin/printf', '/bin/echo']:
        raise ValueError("Executable is disallowed")
    
    command = [executable] + arguments
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return result.stdout
