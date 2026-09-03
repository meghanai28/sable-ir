import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.realpath(dest_path)
    
    if not os.path.exists(dest_path):
        try:
            os.makedirs(dest_path)
        except OSError:
            return False
    
    if not os.path.isdir(dest_path):
        return False
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            
            for member in members:
                if member.issym() or member.islnk():
                    return False
                
                member_name = member.name
                
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        if member.isfile() or member.isdir():
                            return False
                        continue
                
                parts = member_name.split('/')
                safe_parts = []
                for part in parts:
                    if part == '' or part == '.':
                        continue
                    elif part == '..':
                        return False
                    else:
                        safe_parts.append(part)
                
                safe_name = '/'.join(safe_parts)
                if not safe_name and (member.isfile() or member.isdir()):
                    return False
                
                target_path = os.path.realpath(os.path.join(dest_path, safe_name))
                
                if not target_path.startswith(dest_path + os.sep) and target_path != dest_path:
                    return False
                
                if member.isfile():
                    parent_dir = os.path.dirname(target_path)
                    try:
                        os.makedirs(parent_dir, exist_ok=True)
                    except OSError:
                        return False
                elif member.isdir():
                    try:
                        os.makedirs(target_path, exist_ok=True)
                    except OSError:
                        return False
                elif not member.isfile() and not member.isdir():
                    return False
            
            for member in members:
                if member.issym() or member.islnk():
                    return False
                
                member_name = member.name
                
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        continue
                
                parts = member_name.split('/')
                safe_parts = []
                for part in parts:
                    if part == '' or part == '.':
                        continue
                    elif part == '..':
                        return False
                    else:
                        safe_parts.append(part)
                
                safe_name = '/'.join(safe_parts)
                if not safe_name:
                    continue
                
                target_path = os.path.realpath(os.path.join(dest_path, safe_name))
                
                if member.isfile():
                    try:
                        with tar.extractfile(member) as fobj:
                            if fobj is None:
                                return False
                            data = fobj.read()
                        with open(target_path, 'wb') as out:
                            out.write(data)
                        os.chmod(target_path, member.mode)
                    except Exception:
                        return False
                elif member.isdir():
                    try:
                        os.makedirs(target_path, exist_ok=True)
                        os.chmod(target_path, member.mode)
                    except Exception:
                        return False
        
        return True
    
    except Exception:
        return False
