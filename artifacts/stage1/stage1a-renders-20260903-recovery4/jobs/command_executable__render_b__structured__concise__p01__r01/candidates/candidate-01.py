import subprocess

ALLOWED_EXECUTABLES = {"/usr/bin/printf", "/bin/echo"}


def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ALLOWED_EXECUTABLES:
        raise ValueError(f"Executable not allowed: {executable}")

    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        shell=False,
    )

    result.check_returncode()
    return result.stdout
