import os
import tarfile
import stat


def _normalize_member_path(member_name: str, dest_path: str) -> str | None:
    member_name = member_name.replace('/', os.sep)
    member_name = os.path.normpath(member_name)
    if os.path.isabs(member_name):
        member_name = member_name.lstrip(os.sep)
    full_path = os.path.join(dest_path, member_name)
    full_path = os.path.normpath(full_path)
    real_dest = os.path.realpath(dest_path)
    real_full = os.path.realpath(full_path)
    if not real_full.startswith(real_dest + os.sep) and real_full != real_dest:
        return None
    return full_path


def _is_safe_file_type(member: tarfile.TarInfo) -> bool:
    if member.issym() or member.islnk():
        return False
    if member.isreg() or member.isdir():
        return True
    return False


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(dest_path)
        os.makedirs(dest_path, exist_ok=True)
        real_dest = os.path.realpath(dest_path)
        
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            for member in members:
                if not _is_safe_file_type(member):
                    return False
                
                normalized_path = _normalize_member_path(member.name, real_dest)
                if normalized_path is None:
                    return False
                
                if member.isdir():
                    os.makedirs(normalized_path, exist_ok=True)
                elif member.isreg():
                    parent_dir = os.path.dirname(normalized_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    with tf.extractfile(member) as source:
                        if source is None:
                            return False
                        with open(normalized_path, 'wb') as target:
                            while True:
                                chunk = source.read(65536)
                                if not chunk:
                                    break
                                target.write(chunk)
                    mode = member.mode
                    if mode is not None:
                        os.chmod(normalized_path, stat.S_IMODE(mode))
        
        return True
    
    except Exception:
        return False
