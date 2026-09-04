import subprocess
import shlex

ALLOWED_EXECUTABLES = {
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
    "tac",
    "rev",
    "paste",
    "join",
    "split",
    "csplit",
    "expand",
    "unexpand",
    "diff",
    "comm",
    "od",
    "hexdump",
    "base64",
    "basename",
    "dirname",
    "echo",
    "printf",
    "yes",
    "seq",
    "sha256sum",
    "md5sum",
    "sha1sum",
    "cksum",
    "sum",
    "tee",
    "xargs",
}


def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ALLOWED_EXECUTABLES:
        raise ValueError(f"Executable '{executable}' is not allowed")
    
    result = subprocess.run(
        [executable] + arguments,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout
