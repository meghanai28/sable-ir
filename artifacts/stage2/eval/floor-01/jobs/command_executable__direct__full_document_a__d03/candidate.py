import os
import subprocess
import stat

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError("Executable is disallowed")
    
    if not arguments:
        return subprocess.run(["/usr/bin/printf"], capture_output=True, text=True, check=True).stdout
    
    return subprocess.run(["/usr/bin/printf"] + arguments, capture_output=True, text=True, check=True).stdout
