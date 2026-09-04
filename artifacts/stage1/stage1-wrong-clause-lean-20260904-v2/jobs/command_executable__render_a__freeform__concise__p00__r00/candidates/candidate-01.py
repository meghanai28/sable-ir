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
    "rev",
    "tac",
    "paste",
    "join",
    "split",
    "csplit",
    "expand",
    "unexpand",
    "comm",
    "diff",
    "patch",
    "strings",
    "iconv",
    "base64",
    "md5sum",
    "sha1sum",
    "sha256sum",
    "sha512sum",
    "sum",
    "cksum",
    "b2sum",
    "seq",
    "yes",
    "echo",
    "printf",
    "tee",
    "xargs",
    "find",
    "locate",
    "updatedb",
    "spell",
    "look",
    "col",
    "column",
    "hexdump",
    "od",
    "dd",
}


def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in _ALLOWED_EXECUTABLES:
        raise ValueError(f"Disallowed executable: {executable}")
    result = subprocess.run(
        [executable, *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    result.check_returncode()
    return result.stdout
