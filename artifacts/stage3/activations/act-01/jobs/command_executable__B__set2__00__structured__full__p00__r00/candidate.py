import subprocess
import sys

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ['/bin/echo', '/usr/bin/printf']:
        raise ValueError(f"Executable {executable} is disallowed")
    
    # Construct the command list with shell processing disabled
    command = [executable] + arguments
    
    # Run the process and capture standard output
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    
    return result.stdout
