import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_real = os.path.realpath(dest_path)
        if not os.path.isdir(dest_real):
            try:
                os.makedirs(dest_real, exist_ok=True)
            except OSError:
                return False
        
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf.getmembers():
                if member.issym() or member.islnk():
                    return False
                
                member_name = member.name
                if member_name.startswith('/') or member_name.startswith('\\'):
                    member_name = member_name.lstrip('/\\')
                
                parts = member_name.split('/')
                clean_parts = []
                for part in parts:
                    if part == '' or part == '.':
                        continue
                    elif part == '..':
                        if clean_parts:
                            clean_parts.pop()
                    else:
                        clean_parts.append(part)
                
                if not clean_parts:
                    if member.isdir():
                        continue
                    else:
                        return False
                
                safe_name = '/'.join(clean_parts)
                target_path = os.path.join(dest_real, safe_name)
                target_real = os.path.realpath(target_path)
                
                if not target_real.startswith(dest_real + os.sep) and target_real != dest_real:
                    return False
                
                if member.isfile():
                    parent_dir = os.path.dirname(target_real)
                    try:
                        os.makedirs(parent_dir, exist_ok=True)
                    except OSError:
                        return False
                    
                    try:
                        with tf.extractfile(member) as fsrc:
                            if fsrc is None:
                                return False
                            with open(target_real, 'wb') as fdst:
                                while True:
                                    chunk = fsrc.read(65536)
                                    if not chunk:
                                        break
                                    fdst.write(chunk)
                        
                        mode = member.mode
                        if mode is not None:
                            try:
                                os.chmod(target_real, stat.S_IMODE(mode))
                            except OSError:
                                pass
                    except (OSError, IOError, tarfile.ExtractError):
                        return False
                    
                elif member.isdir():
                    try:
                        os.makedirs(target_real, exist_ok=True)
                        mode = member.mode
                        if mode is not None:
                            try:
                                os.chmod(target_real, stat.S_IMODE(mode))
                            except OSError:
                                pass
                    except OSError:
                        return False
                else:
                    return False
        
        return True
    
    except (tarfile.TarError, OSError, IOError):
        return False
