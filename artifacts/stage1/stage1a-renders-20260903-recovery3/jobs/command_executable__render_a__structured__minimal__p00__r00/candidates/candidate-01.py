import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError("Disallowed executable")
    result = subprocess.run(
        ["/usr/bin/printf"] + arguments,
        capture_output=True,
        text=True,
        shell=False,
    )
    result.check_returncode()
    return result.stdout
