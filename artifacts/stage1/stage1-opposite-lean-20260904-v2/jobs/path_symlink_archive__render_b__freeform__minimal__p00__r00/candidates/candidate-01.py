import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        abs_dest = os.path.abspath(dest_path)
        os.makedirs(abs_dest, exist_ok=True)
        
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf.getmembers():
                if member.issym() or member.islnk():
                    return False
                
                member_path = os.path.join(abs_dest, member.name)
                normalized_path = os.path.normpath(member_path)
                
                if not normalized_path.startswith(abs_dest + os.sep) and normalized_path != abs_dest:
                    return False
                
                if member.isfile():
                    try:
                        if os.path.islink(normalized_path) or os.path.islink(os.path.dirname(normalized_path)):
                            return False
                        
                        parent_dir = os.path.dirname(normalized_path)
                        if parent_dir:
                            os.makedirs(parent_dir, exist_ok=True)
                            if os.path.islink(parent_dir):
                                return False
                        
                        with tf.extractfile(member) as src, open(normalized_path, 'wb') as dst:
                            if src is None:
                                return False
                            dst.write(src.read())
                    except (OSError, IOError):
                        return False
                elif member.isdir():
                    try:
                        if os.path.islink(normalized_path):
                            return False
                        
                        os.makedirs(normalized_path, exist_ok=True)
                    except (OSError, IOError):
                        return False
                else:
                    return False
        
        return True
    except (OSError, IOError, tarfile.TarError):
        return False
