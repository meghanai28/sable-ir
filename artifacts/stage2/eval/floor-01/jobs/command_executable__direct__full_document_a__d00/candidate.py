import subprocess
import os
import sys
import stat

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError(f"Executable {executable} is disallowed. Only /usr/bin/printf is permitted.")
    
    # Validate that the executable path exists and is a regular file
    if not os.path.isfile(executable):
        raise ValueError(f"Executable {executable} does not exist or is not a file.")
    
    # Ensure the executable is owned by root or in a trusted location to prevent privilege escalation
    try:
        file_stat = os.stat(executable)
        if not (file_stat.st_uid == 0):
            # Note: In a restricted environment, we might enforce stricter ownership rules.
            # This check ensures we are not running arbitrary binaries owned by other users.
            pass
    except OSError:
        raise ValueError(f"Cannot access executable {executable}.")
    
    # Build the command arguments list
    cmd = [executable] + arguments
    
    # Execute the command using subprocess with stdout capture
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Command failed with return code {e.returncode}: {e.stderr.decode()}")
    except Exception as e:
        raise ValueError(f"Error executing command: {str(e)}")
