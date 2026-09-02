import subprocess


def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in {"/usr/bin/printf", "/bin/echo"}:
        raise ValueError("executable is not permitted")
    result = subprocess.run(
        [executable, *arguments],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
        timeout=5,
    )
    return result.stdout
