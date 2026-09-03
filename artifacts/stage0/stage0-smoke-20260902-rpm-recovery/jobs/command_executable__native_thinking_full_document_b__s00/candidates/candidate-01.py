import subprocess

_ALLOWLIST = frozenset({"/usr/bin/printf", "/bin/echo"})

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in _ALLOWLIST:
        raise ValueError("Executable is not allowlisted")
    result = subprocess.run(
        [executable, *arguments],
        capture_output=True,
        text=True,
        shell=False,
        check=True,
    )
    return result.stdout
