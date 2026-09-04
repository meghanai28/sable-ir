import subprocess

ALLOWED_EXECUTABLE = "/usr/bin/printf"

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != ALLOWED_EXECUTABLE:
        raise ValueError(f"Executable not allowed: {executable}")
    
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        shell=False,
        check=True,
    )
    
    return result.stdout.decode("utf-8")
