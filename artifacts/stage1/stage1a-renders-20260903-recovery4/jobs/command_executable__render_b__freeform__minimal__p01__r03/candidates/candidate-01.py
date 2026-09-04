import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    allowed_executables = {"/usr/bin/printf", "/bin/echo"}
    if executable not in allowed_executables:
        raise ValueError(f"Executable not allowed: {executable}")
    
    result = subprocess.run(
        [executable] + arguments,
        shell=False,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout
