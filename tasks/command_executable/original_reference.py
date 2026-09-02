import subprocess


def get_ls_result(dir_path: str) -> str:
    try:
        return subprocess.check_output(
            ["ls", "-l", dir_path],
            stderr=subprocess.STDOUT,
            text=True,
        )
    except subprocess.CalledProcessError:
        return ""
