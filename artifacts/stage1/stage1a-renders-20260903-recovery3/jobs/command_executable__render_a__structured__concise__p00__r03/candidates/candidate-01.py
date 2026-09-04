import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    ALLOWED_EXECUTABLE = "/usr/bin/printf"
    if executable != ALLOWED_EXECUTABLE:
        raise ValueError(f"Disallowed executable: {executable}")
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        shell=False,
        check=True,
    )
    return result.stdout
