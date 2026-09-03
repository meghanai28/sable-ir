import os
import tarfile


def _normalize_path(path: str) -> str:
    return os.path.normpath(path).replace(os.sep, '/')


def _is_safe_link_target(link_target: str, dest_path: str) -> bool:
    normalized_target = _normalize_path(link_target)
    if os.path.isabs(normalized_target):
        return False
    resolved = os.path.join(dest_path, normalized_target)
    resolved = os.path.normpath(resolved)
    dest_normalized = os.path.normpath(os.path.abspath(dest_path))
    return resolved.startswith(dest_normalized + os.sep) or resolved == dest_normalized


def _get_member_extract_path(member: tarfile.TarInfo, dest_path: str) -> str:
    member_name = _normalize_path(member.name)
    if os.path.isabs(member_name):
        member_name = member_name.lstrip('/')
    extract_path = os.path.join(dest_path, member_name)
    extract_path = os.path.normpath(extract_path)
    return extract_path


def _is_safe_member_path(member: tarfile.TarInfo, dest_path: str) -> bool:
    extract_path = _get_member_extract_path(member, dest_path)
    dest_normalized = os.path.normpath(os.path.abspath(dest_path))
    return extract_path.startswith(dest_normalized + os.sep) or extract_path == dest_normalized


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_normalized = os.path.normpath(os.path.abspath(dest_path))
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            for member in members:
                if not _is_safe_member_path(member, dest_path):
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if not _is_safe_link_target(link_target, dest_path):
                        return False
            
            for member in members:
                extract_path = _get_member_extract_path(member, dest_path)
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if not _is_safe_link_target(link_target, dest_path):
                        return False
                    if member.issym():
                        os.symlink(link_target, extract_path)
                    else:
                        os.link(os.path.join(dest_path, _normalize_path(link_target)), extract_path)
                else:
                    tf.extract(member, dest_path)
            
            return True
    
    except (tarfile.TarError, OSError, IOError):
        return False
