import subprocess

ALLOWLIST = ("/usr/bin/printf", "/bin/echo")

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ALLOWLIST:
        raise ValueError(f"Disallowed executable: {executable}")
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        shell=False,
        check=False,
    )
    result.check_returncode()
    return result.stdout
