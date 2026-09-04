import subprocess

ALLOWED_EXECUTABLE = "/usr/bin/printf"

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != ALLOWED_EXECUTABLE:
        raise ValueError("Disallowed executable")
    command = [ALLOWED_EXECUTABLE] + list(arguments)
    result = subprocess.run(command, shell=False, capture_output=True, text=True)
    return result.stdout
