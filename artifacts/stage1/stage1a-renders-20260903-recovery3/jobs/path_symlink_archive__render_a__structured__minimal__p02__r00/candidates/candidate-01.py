import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_real = os.path.realpath(dest_path)
        if not os.path.isdir(dest_real):
            try:
                os.makedirs(dest_real, exist_ok=True)
            except OSError:
                return False
        
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            for member in members:
                if member.issym() or member.islnk():
                    return False
                
                if not member.isfile() and not member.isdir():
                    return False
                
                member_name = member.name
                
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        if member.isdir():
                            continue
                        return False
                
                parts = member_name.split('/')
                cleaned_parts = []
                for part in parts:
                    if part == '' or part == '.':
                        continue
                    elif part == '..':
                        return False
                    else:
                        cleaned_parts.append(part)
                
                if not cleaned_parts:
                    if member.isdir():
                        continue
                    return False
                
                safe_name = '/'.join(cleaned_parts)
                target_path = os.path.join(dest_real, safe_name)
                target_real = os.path.realpath(target_path)
                
                if not (target_real == dest_real or target_real.startswith(dest_real + os.sep)):
                    return False
                
                if member.isfile():
                    parent_dir = os.path.dirname(target_real)
                    parent_real = os.path.realpath(parent_dir)
                    if not (parent_real == dest_real or parent_real.startswith(dest_real + os.sep)):
                        return False
                    try:
                        os.makedirs(parent_dir, exist_ok=True)
                    except OSError:
                        return False
            
            for member in members:
                if member.issym() or member.islnk():
                    return False
                
                if not member.isfile() and not member.isdir():
                    return False
                
                member_name = member.name
                
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        if member.isdir():
                            continue
                        return False
                
                parts = member_name.split('/')
                cleaned_parts = []
                for part in parts:
                    if part == '' or part == '.':
                        continue
                    elif part == '..':
                        return False
                    else:
                        cleaned_parts.append(part)
                
                if not cleaned_parts:
                    if member.isdir():
                        continue
                    return False
                
                safe_name = '/'.join(cleaned_parts)
                target_path = os.path.join(dest_real, safe_name)
                target_real = os.path.realpath(target_path)
                
                if not (target_real == dest_real or target_real.startswith(dest_real + os.sep)):
                    return False
                
                if member.isfile():
                    parent_dir = os.path.dirname(target_real)
                    parent_real = os.path.realpath(parent_dir)
                    if not (parent_real == dest_real or parent_real.startswith(dest_real + os.sep)):
                        return False
                    
                    try:
                        source = tf.extractfile(member)
                        if source is None:
                            return False
                        try:
                            os.makedirs(parent_dir, exist_ok=True)
                        except OSError:
                            source.close()
                            return False
                        try:
                            with open(target_real, 'wb') as f:
                                while True:
                                    chunk = source.read(65536)
                                    if not chunk:
                                        break
                                    f.write(chunk)
                        finally:
                            source.close()
                        try:
                            os.utime(target_real, (member.mtime, member.mtime))
                        except OSError:
                            pass
                    except (OSError, IOError):
                        return False
                
                elif member.isdir():
                    try:
                        os.makedirs(target_real, exist_ok=True)
                    except OSError:
                        return False
        
        return True
    
    except (tarfile.TarError, OSError, IOError):
        return False
