import subprocess

_ALLOWED_EXECUTABLES = {
    "cat",
    "grep",
    "head",
    "tail",
    "sort",
    "uniq",
    "wc",
    "cut",
    "tr",
    "sed",
    "awk",
    "echo",
    "printf",
    "fold",
    "join",
    "paste",
    "split",
    "comm",
    "diff",
    "cmp",
    "nl",
    "od",
    "rev",
    "tac",
    "tee",
    "xargs",
    "find",
    "basename",
    "dirname",
    "seq",
    "shuf",
    "csplit",
    "expand",
    "unexpand",
    "fmt",
    "pr",
}

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in _ALLOWED_EXECUTABLES:
        raise ValueError(f"Executable '{executable}' is not allowed")
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout
