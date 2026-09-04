import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError("Executable not allowed: only /usr/bin/printf is permitted")
    
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        shell=False,
        check=False,
    )
    
    result.check_returncode()
    
    return result.stdout
