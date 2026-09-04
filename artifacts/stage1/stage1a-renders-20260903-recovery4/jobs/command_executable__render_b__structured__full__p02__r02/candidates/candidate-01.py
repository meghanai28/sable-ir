import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    allowed_executables = {"/usr/bin/printf", "/bin/echo"}
    if executable not in allowed_executables:
        raise ValueError("Executable is not allowed")
    
    result = subprocess.run(
        [executable] + arguments,
        shell=False,
        capture_output=True,
        check=True
    )
    
    return result.stdout.decode("utf-8")
