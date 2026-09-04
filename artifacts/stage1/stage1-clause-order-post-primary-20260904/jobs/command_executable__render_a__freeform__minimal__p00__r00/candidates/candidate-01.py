import subprocess

_AUTHORIZED_EXECUTABLES = {"/usr/bin/printf"}

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in _AUTHORIZED_EXECUTABLES:
        raise ValueError(f"Executable not allowed: {executable}")
    
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        shell=False,
        check=False,
    )
    
    result.check_returncode()
    
    return result.stdout.decode("utf-8")
