import subprocess
import sys

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ("/usr/bin/printf", "/bin/echo"):
        raise ValueError(f"Disallowed executable: {executable}")
    
    cmd = [executable] + arguments
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    
    if result.returncode != 0:
        raise RuntimeError(f"Process failed with return code {result.returncode}")
    
    return result.stdout
