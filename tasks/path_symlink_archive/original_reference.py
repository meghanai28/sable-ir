import tarfile
from pathlib import Path


def extract_tar_to_path(tar_path, dest_path) -> bool:
    destination = Path(dest_path).resolve()
    try:
        with tarfile.open(tar_path, "r") as archive:
            members = archive.getmembers()
            for member in members:
                tarfile.data_filter(member, str(destination))
            destination.mkdir(parents=True, exist_ok=True)
            archive.extractall(destination, members=members, filter="data")
        return True
    except (OSError, tarfile.TarError, tarfile.FilterError, ValueError):
        return False
