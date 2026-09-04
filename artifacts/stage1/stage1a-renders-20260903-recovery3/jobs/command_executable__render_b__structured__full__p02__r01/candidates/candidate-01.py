import subprocess

ALLOWED_EXECUTABLES = frozenset(('/usr/bin/printf', '/bin/echo'))

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ALLOWED_EXECUTABLES:
        raise ValueError(f"Disallowed executable: {executable!r}")
    
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        shell=False,
        check=False,
    )
    
    result.check_returncode()
    
    return result.stdout.decode('utf-8')
