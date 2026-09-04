import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    allowed_executables = {"/usr/bin/printf", "/bin/echo"}
    if executable not in allowed_executables:
        raise ValueError(f"Disallowed executable: {executable}")
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        shell=False,
        check=True,
    )
    return result.stdout.decode("utf-8")
