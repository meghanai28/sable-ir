import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ("/usr/bin/printf", "/bin/echo"):
        raise ValueError("Executable is not allowed")
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        shell=False,
        check=True,
    )
    return result.stdout
