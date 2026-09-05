import subprocess
import sys

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ('/usr/bin/printf', '/bin/echo'):
        raise ValueError("Executable is disallowed")
    
    cmd = [executable] + arguments
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout
