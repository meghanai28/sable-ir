import subprocess
import os

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ("/usr/bin/printf", "/bin/echo"):
        raise ValueError("Executable is disallowed")
    
    # Pass arguments directly as a list to subprocess to disable shell processing
    # This prevents injection of shell metacharacters
    return subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        check=True
    ).stdout
