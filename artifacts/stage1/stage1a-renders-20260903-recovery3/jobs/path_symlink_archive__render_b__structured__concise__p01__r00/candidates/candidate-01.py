import os
import tarfile
from typing import Optional


def _normalize_path(path: str) -> Optional[str]:
    try:
        return os.path.abspath(os.path.normpath(path))
    except (ValueError, OSError):
        return None


def _is_within_base(target: str, base: str) -> bool:
    return target == base or target.startswith(base + os.sep)


def _validate_member(member: tarfile.TarInfo, base: str, tar: tarfile.TarFile) -> bool:
    member_name = member.name
    if not member_name:
        return False
    if os.path.isabs(member_name):
        return False
    if '..' in member_name.split('/') or '..' in member_name.split('\\'):
        return False
    normalized_member = _normalize_path(os.path.join(base, member_name))
    if normalized_member is None:
        return False
    if not _is_within_base(normalized_member, base):
        return False
    if member.issym() or member.islnk():
        link_target = member.linkname
        if not link_target:
            return False
        if os.path.isabs(link_target):
            return False
        if '..' in link_target.split('/') or '..' in link_target.split('\\'):
            return False
        normalized_link_target = _normalize_path(os.path.join(os.path.dirname(normalized_member), link_target))
        if normalized_link_target is None:
            return False
        if not _is_within_base(normalized_link_target, base):
            return False
    return True


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    base = _normalize_path(dest_path)
    if base is None:
        return False
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            for member in members:
                if not _validate_member(member, base, tar):
                    return False
            for member in members:
                try:
                    tar.extract(member, path=base)
                except (tarfile.TarError, OSError, IOError):
                    return False
            return True
    except (tarfile.TarError, OSError, IOError):
        return False
