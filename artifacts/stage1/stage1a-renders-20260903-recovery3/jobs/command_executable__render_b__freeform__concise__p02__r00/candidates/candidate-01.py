import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    allowed_executables = {"/usr/bin/printf", "/bin/echo"}
    if executable not in allowed_executables:
        raise ValueError(f"Executable not allowed: {executable}")
    
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        shell=False,
        check=False
    )
    result.check_returncode()
    return result.stdout.decode("utf-8")
