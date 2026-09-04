import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError("Disallowed executable")
    
    cmd = ["/usr/bin/printf"] + arguments
    
    result = subprocess.run(
        cmd,
        shell=False,
        capture_output=True,
        text=True,
        check=True
    )
    
    return result.stdout
