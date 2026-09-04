import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf" and executable != "/bin/echo":
        raise ValueError("Disallowed executable")
    
    result = subprocess.run(
        [executable] + arguments,
        stdout=subprocess.PIPE,
        check=False
    )
    
    result.check_returncode()
    
    return result.stdout.decode()
