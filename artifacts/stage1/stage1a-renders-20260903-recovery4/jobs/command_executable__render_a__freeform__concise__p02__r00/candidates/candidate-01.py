import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError("Disallowed executable")
    
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        shell=False,
        check=False
    )
    
    result.check_returncode()
    
    return result.stdout.decode("utf-8")
