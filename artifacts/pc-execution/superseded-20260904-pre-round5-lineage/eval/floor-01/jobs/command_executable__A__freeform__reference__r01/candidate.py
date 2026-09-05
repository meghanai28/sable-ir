import subprocess
import sys

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError("Executable is disallowed")
    
    # Build the argument list directly without shell processing
    cmd = [executable] + arguments
    
    # Run the process and capture standard output
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True
    )
    
    return result.stdout
