import subprocess
import sys

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError(f"Executable '{executable}' is disallowed")
    
    try:
        result = subprocess.run(
            [executable] + arguments,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise e
    except Exception as e:
        raise e
