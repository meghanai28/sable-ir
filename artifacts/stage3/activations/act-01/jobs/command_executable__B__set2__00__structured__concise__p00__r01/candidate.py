import subprocess
import sys

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ("/bin/echo", "/usr/bin/printf"):
        raise ValueError("Executable is disallowed")
    try:
        process = subprocess.Popen(
            [executable] + arguments,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Process failed with return code {process.returncode}: {stderr}")
        return stdout
    except Exception as e:
        raise ValueError(f"Process execution failed: {e}") from e
