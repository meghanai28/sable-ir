import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError("Executable is disallowed")
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        shell=False,
        check=True,
    )
    return result.stdout
