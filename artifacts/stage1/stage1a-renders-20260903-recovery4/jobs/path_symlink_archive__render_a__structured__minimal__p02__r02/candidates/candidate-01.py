import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.realpath(dest_path))
    except (OSError, ValueError):
        return False

    if not os.path.isdir(dest_path):
        try:
            os.makedirs(dest_path, exist_ok=True)
        except OSError:
            return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            for member in members:
                if member.issym() or member.islnk():
                    return False
                
                if not (member.isfile() or member.isdir()):
                    return False
                
                member_name = member.name
                
                if os.path.isabs(member_name):
                    return False
                
                normalized = os.path.normpath(member_name)
                
                if normalized.startswith('..') or normalized == '..':
                    return False
                
                final_path = os.path.join(dest_path, normalized)
                final_path = os.path.abspath(os.path.realpath(final_path))
                
                if not final_path.startswith(dest_path + os.sep) and final_path != dest_path:
                    return False
                
                if member.isfile():
                    parent_dir = os.path.dirname(final_path)
                    try:
                        os.makedirs(parent_dir, exist_ok=True)
                    except OSError:
                        return False
                    
                    try:
                        with tf.extractfile(member) as source:
                            if source is None:
                                return False
                            with open(final_path, 'wb') as target:
                                while True:
                                    chunk = source.read(65536)
                                    if not chunk:
                                        break
                                    target.write(chunk)
                    except (OSError, IOError, tarfile.TarError):
                        return False
                    
                    try:
                        os.utime(final_path, (member.mtime, member.mtime))
                    except OSError:
                        pass
                    
                    try:
                        os.chmod(final_path, member.mode)
                    except OSError:
                        pass
                
                elif member.isdir():
                    try:
                        os.makedirs(final_path, exist_ok=True)
                    except OSError:
                        return False
                    
                    try:
                        os.utime(final_path, (member.mtime, member.mtime))
                    except OSError:
                        pass
                    
                    try:
                        os.chmod(final_path, member.mode)
                    except OSError:
                        pass
        
        return True
    
    except (tarfile.TarError, OSError, IOError):
        return False
