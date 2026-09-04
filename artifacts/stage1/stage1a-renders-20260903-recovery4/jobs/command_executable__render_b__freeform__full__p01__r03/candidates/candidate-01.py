import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf" and executable != "/bin/echo":
        raise ValueError("Executable not allowed: " + executable)
    
    cmd = [executable] + list(arguments)
    
    result = subprocess.run(
        cmd,
        shell=False,
        capture_output=True
    )
    
    return result.stdout.decode("utf-8")
