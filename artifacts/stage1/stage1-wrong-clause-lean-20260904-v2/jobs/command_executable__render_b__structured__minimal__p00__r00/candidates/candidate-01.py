import subprocess

_ALLOWED_EXECUTABLES = {
    "cat",
    "echo",
    "grep",
    "head",
    "sort",
    "tail",
    "tr",
    "uniq",
    "wc",
}


def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in _ALLOWED_EXECUTABLES:
        raise ValueError(f"Executable '{executable}' is not allowed")
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        shell=False,
        check=False,
    )
    result.check_returncode()
    return result.stdout
