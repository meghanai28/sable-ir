import subprocess

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError("Disallowed executable")
    result = subprocess.run(
        ["/usr/bin/printf"] + arguments,
        executable="/usr/bin/printf",
        shell=False,
        capture_output=True,
        check=False,
    )
    result.check_returncode()
    return result.stdout.decode("utf-8")
