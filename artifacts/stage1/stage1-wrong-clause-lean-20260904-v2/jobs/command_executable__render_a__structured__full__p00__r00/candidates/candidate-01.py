import subprocess
import shlex

_ALLOWED_EXECUTABLES = frozenset({
    "cat",
    "head",
    "tail",
    "wc",
    "sort",
    "uniq",
    "cut",
    "tr",
    "grep",
    "egrep",
    "fgrep",
    "sed",
    "awk",
    "paste",
    "join",
    "split",
    "csplit",
    "expand",
    "unexpand",
    "fmt",
    "fold",
    "nl",
    "od",
    "hexdump",
    "xxd",
    "base64",
    "basename",
    "dirname",
    "realpath",
    "readlink",
    "tee",
    "tac",
    "rev",
    "comm",
    "diff",
    "cmp",
    "patch",
    "md5sum",
    "sha1sum",
    "sha256sum",
    "sha512sum",
    "sum",
    "cksum",
    "b2sum",
    "ls",
    "find",
    "xargs",
    "printenv",
    "echo",
    "printf",
    "yes",
    "seq",
    "factor",
    "shuf",
    "sort",
    "tsort",
    "ptx",
    "look",
    "iconv",
    "enca",
    "file",
    "strings",
    "strip",
    "nm",
    "objdump",
    "readelf",
    "ldd",
    "c++filt",
    "addr2line",
    "gprof",
    "gcov",
    "gettext",
    "ngettext",
    "envsubst",
    "msgfmt",
    "msgmerge",
    "msgcat",
    "msguniq",
    "msgattrib",
    "msgen",
    "msginit",
    "zipinfo",
    "unzip",
    "zcat",
    "zdiff",
    "zgrep",
    "zless",
    "zmore",
    "bzcat",
    "bzdiff",
    "bzgrep",
    "xzcat",
    "lzcat",
    "lzma",
    "lzop",
    "lz4",
    "zstd",
    "unzstd",
    "zstdcat",
    "gzip",
    "gunzip",
    "bzip2",
    "bunzip2",
    "xz",
    "unxz",
    "lzip",
    "lunzip",
    "tar",
    "cpio",
    "pax",
    "ar",
    "ranlib",
    "jq",
    "yq",
    "xmlstarlet",
    "xsltproc",
    "xmllint",
    "csvformat",
    "csvcut",
    "csvgrep",
    "csvstat",
    "csvlook",
    "csvsql",
    "in2csv",
    "sql2csv",
    "csvjson",
    "json2csv",
    "pygmentize",
    "bat",
    "delta",
    "diff-so-fancy",
    "colordiff",
    "wdiff",
    "sdiff",
    "cmp",
    "comm",
    "sponge",
    "moreutils",
    "parallel",
    "timeout",
    "chronic",
    "combine",
    "numfmt",
    "date",
    "cal",
    "ncal",
})

def _sanitize_for_log(value: str) -> str:
    if value is None:
        return ""
    result = value
    sensitive_patterns = [
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "auth",
        "credential",
        "private_key",
        "privatekey",
        "recovery",
        "bearer",
        "session",
        "cookie",
    ]
    lower = result.lower()
    for pattern in sensitive_patterns:
        if pattern in lower:
            return "[REDACTED]"
    if result.startswith("Authorization:") or result.startswith("authorization:"):
        return "[REDACTED]"
    if result.startswith("Bearer ") or result.startswith("bearer "):
        return "[REDACTED]"
    if "Basic " in result or "basic " in result:
        return "[REDACTED]"
    return result

def _sanitize_arguments_for_log(arguments: list[str]) -> list[str]:
    return [_sanitize_for_log(arg) for arg in arguments]

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in _ALLOWED_EXECUTABLES:
        raise ValueError(f"Disallowed executable: {executable}")
    
    sanitized_executable = _sanitize_for_log(executable)
    sanitized_arguments = _sanitize_arguments_for_log(arguments)
    
    process = subprocess.Popen(
        [executable] + arguments,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        text=False,
    )
    
    stdout_bytes, stderr_bytes = process.communicate()
    
    if process.returncode != 0:
        process.stdout = None
        process.stderr = None
        raise subprocess.CalledProcessError(
            process.returncode,
            [executable] + arguments,
            output=stdout_bytes,
            stderr=stderr_bytes,
        )
    
    text_output = stdout_bytes.decode("utf-8", errors="replace")
    
    return text_output
