import subprocess

__all__ = ["run_text_utility"]


def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError("Executable is not allowed")

    result = subprocess.run(
        [executable, *arguments],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )
    return result.stdout
