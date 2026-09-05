import subprocess
import sys

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ("/usr/bin/printf", "/bin/echo"):
        raise ValueError(f"Executable {executable} is disallowed")
    
    process = subprocess.Popen(
        [executable] + arguments,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(f"Process failed with return code {process.returncode}")
    
    return stdout
