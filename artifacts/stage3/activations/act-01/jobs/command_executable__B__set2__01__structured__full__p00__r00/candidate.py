def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ['/usr/bin/printf', '/bin/echo']:
        raise ValueError("Executable is disallowed")
    import subprocess
    result = subprocess.run([executable] + arguments, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Process failed with return code {result.returncode}")
    return result.stdout
