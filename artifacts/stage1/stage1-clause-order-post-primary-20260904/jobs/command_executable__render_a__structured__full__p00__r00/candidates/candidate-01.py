import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    ALLOWED_EXECUTABLE = "/usr/bin/printf"
    if executable != ALLOWED_EXECUTABLE:
        raise ValueError("Disallowed executable")
    result = subprocess.run(
        [ALLOWED_EXECUTABLE] + arguments,
        executable=ALLOWED_EXECUTABLE,
        shell=False,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout
