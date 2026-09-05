import subprocess
import sys

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError(f"Disallowed executable: {executable}")
    
    # Build the argument list directly, avoiding shell interpretation
    cmd = [executable] + arguments
    
    # Run the process and capture standard output
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False
    )
    
    # Let process failures propagate (non-zero exit code)
    if result.returncode != 0:
        raise RuntimeError(f"Process failed with return code {result.returncode}")
    
    return result.stdout
