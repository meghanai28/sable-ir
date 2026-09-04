import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    allowed_executable = "/usr/bin/printf"
    if executable != allowed_executable:
        raise ValueError(f"Executable '{executable}' is not allowed. Only '{allowed_executable}' is permitted.")
    
    result = subprocess.run(
        [allowed_executable] + arguments,
        capture_output=True,
        text=True,
        shell=False
    )
    
    result.check_returncode()
    
    return result.stdout
