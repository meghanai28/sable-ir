import subprocess
import sys

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ('/usr/bin/printf', '/bin/echo'):
        raise ValueError(f"Executable {executable!r} is disallowed")
    
    # Use subprocess with shell=False to prevent shell injection
    # Pass arguments directly as a list to avoid shell interpretation
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
