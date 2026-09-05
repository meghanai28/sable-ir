def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "/usr/bin/printf":
        raise ValueError("Executable is disallowed")
    
    process = __import__("subprocess").Popen(
        [executable] + arguments,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False
    )
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(f"Process failed with return code {process.returncode}: {stderr.decode('utf-8', errors='replace')}")
    
    return stdout.decode('utf-8', errors='replace')
