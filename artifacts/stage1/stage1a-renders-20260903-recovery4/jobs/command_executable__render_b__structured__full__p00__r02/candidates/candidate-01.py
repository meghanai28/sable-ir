import subprocess

ALLOWED_EXECUTABLES = {"/usr/bin/printf", "/bin/echo"}

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ALLOWED_EXECUTABLES:
        raise ValueError(f"Disallowed executable: {executable}")
    
    result = subprocess.run(
        [executable] + arguments,
        shell=False,
        capture_output=True,
        check=False
    )
    
    result.check_returncode()
    
    return result.stdout.decode("utf-8")
