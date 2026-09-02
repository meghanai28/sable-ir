import subprocess


def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
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
