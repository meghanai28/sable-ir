import subprocess
import os
import sys

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ['/usr/bin/printf', '/bin/echo']:
        raise ValueError(f"Executable {executable} is disallowed")
    
    # Prepare the command list
    cmd = [executable] + arguments
    
    # Execute the command
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise e
    except Exception as e:
        raise ValueError(f"Process execution failed: {e}")
