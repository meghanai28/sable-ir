import subprocess
import sys

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ['/bin/echo', '/usr/bin/printf']:
        raise ValueError("Executable is disallowed")
    
    # Build the argument list safely without shell processing
    cmd = [executable] + arguments
    
    # Run the command with shell=False to prevent shell metacharacters
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        # Let process failures propagate as per requirements
        raise e
