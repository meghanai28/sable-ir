import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError("Executable is not allowed")
    
    result = subprocess.run(
        ["/usr/bin/printf"] + list(arguments),
        shell=False,
        capture_output=True,
        text=True,
        check=True
    )
    
    return result.stdout
