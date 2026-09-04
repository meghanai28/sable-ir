import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    allowed_path = "/usr/bin/printf"
    if executable != allowed_path:
        raise ValueError(f"Executable '{executable}' is not allowed. Only '{allowed_path}' is permitted.")
    
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        shell=False
    )
    
    result.check_returncode()
    return result.stdout
