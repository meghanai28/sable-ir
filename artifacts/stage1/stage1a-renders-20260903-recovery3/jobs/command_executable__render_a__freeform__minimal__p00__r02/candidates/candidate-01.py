import subprocess

ALLOWED_EXECUTABLE = "/usr/bin/printf"

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != ALLOWED_EXECUTABLE:
        raise ValueError(f"Disallowed executable: {executable}")
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        shell=False,
    )
    result.check_returncode()
    return result.stdout
