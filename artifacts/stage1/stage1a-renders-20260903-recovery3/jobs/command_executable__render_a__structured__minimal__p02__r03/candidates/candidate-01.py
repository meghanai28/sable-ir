import subprocess

_ALLOWED_EXECUTABLE = "/usr/bin/printf"

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != _ALLOWED_EXECUTABLE:
        raise ValueError(f"Executable disallowed: {executable}")
    result = subprocess.run(
        [_ALLOWED_EXECUTABLE] + arguments,
        capture_output=True,
        text=True,
        shell=False,
        check=True,
    )
    return result.stdout
