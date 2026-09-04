import subprocess

ALLOWED_EXECUTABLES = {"/usr/bin/printf", "/bin/echo"}


def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ALLOWED_EXECUTABLES:
        raise ValueError("Disallowed executable: " + executable)
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        shell=False,
    )
    return result.stdout.decode("utf-8")
