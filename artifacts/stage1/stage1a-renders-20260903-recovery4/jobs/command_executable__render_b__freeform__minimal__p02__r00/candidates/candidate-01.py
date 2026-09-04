import subprocess

_ALLOWED_EXECUTABLES = {"/usr/bin/printf", "/bin/echo"}


def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in _ALLOWED_EXECUTABLES:
        raise ValueError(f"Disallowed executable: {executable}")
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        shell=False,
        check=True,
    )
    return result.stdout
