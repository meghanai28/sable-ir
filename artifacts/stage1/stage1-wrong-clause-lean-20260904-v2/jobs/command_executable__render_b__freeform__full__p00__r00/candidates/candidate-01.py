import subprocess

_ALLOWED_EXECUTABLES = {
    "cat",
    "head",
    "tail",
    "grep",
    "sed",
    "awk",
    "cut",
    "sort",
    "uniq",
    "wc",
    "tr",
    "fold",
    "fmt",
    "nl",
    "od",
    "hexdump",
    "base64",
    "rev",
    "tac",
    "paste",
    "join",
    "split",
    "csplit",
    "expand",
    "unexpand",
    "col",
    "column",
    "strings",
    "diff",
    "comm",
    "patch",
}

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in _ALLOWED_EXECUTABLES:
        raise ValueError(f"Executable '{executable}' is not allowed")
    
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=False,
        shell=False,
    )
    
    result.check_returncode()
    
    return result.stdout.decode("utf-8", errors="replace")
