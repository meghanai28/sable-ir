import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError("Disallowed executable")
    result = subprocess.run(
        ["/usr/bin/printf"] + arguments,
        shell=False,
        capture_output=True,
    )
    return result.stdout.decode()
