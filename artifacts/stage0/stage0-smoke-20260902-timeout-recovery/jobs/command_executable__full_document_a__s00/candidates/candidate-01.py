import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError(f"Disallowed executable: {executable}")
    
    result = subprocess.run(
        [executable] + list(arguments),
        capture_output=True,
        text=True,
        shell=False
    )
    result.check_returncode()
    return result.stdout
