import subprocess
import sys

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError("Executable is disallowed")
    
    # Use subprocess.run with shell=False to prevent shell injection
    # Pass arguments as a list to avoid command string building
    try:
        result = subprocess.run(
            [executable] + arguments,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        # Let process failures propagate as expected
        raise e
