import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError("Disallowed executable")
    command = ["/usr/bin/printf"] + list(arguments)
    result = subprocess.run(command, shell=False, capture_output=True, text=True)
    return result.stdout
