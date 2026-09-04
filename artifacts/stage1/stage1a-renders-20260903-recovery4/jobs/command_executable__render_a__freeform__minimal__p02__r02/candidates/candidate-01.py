import subprocess

_ALLOWED_EXECUTABLE = "/usr/bin/printf"

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != _ALLOWED_EXECUTABLE:
        raise ValueError(f"Disallowed executable: {executable!r}")
    result = subprocess.run(
        [_ALLOWED_EXECUTABLE] + arguments,
        capture_output=True,
        shell=False,
        check=False,
    )
    result.check_returncode()
    return result.stdout.decode("utf-8")
