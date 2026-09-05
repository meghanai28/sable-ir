import subprocess
import sys

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ("/usr/bin/printf", "/bin/echo"):
        raise ValueError("Executable is disallowed")
    
    process = subprocess.Popen([executable] + arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"Process failed with return code {process.returncode}")
    return stdout.decode("utf-8")
