import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.normpath(os.path.abspath(dest_path))
    
    try:
        os.makedirs(dest_path, exist_ok=True)
    except (OSError, IOError):
        return False
    
    try:
        archive = tarfile.open(tar_path, 'r')
    except (tarfile.TarError, OSError, IOError):
        return False
    
    try:
        members = archive.getmembers()
    except (tarfile.TarError, OSError, IOError):
        archive.close()
        return False
    
    validated_members = []
    
    for member in members:
        if member.issym() or member.islnk():
            archive.close()
            return False
        
        if not member.isfile() and not member.isdir():
            archive.close()
            return False
        
        sanitized_name = member.name.lstrip('/\\')
        if os.name == 'nt':
            if len(sanitized_name) >= 2 and sanitized_name[1] == ':':
                sanitized_name = sanitized_name[2:].lstrip('/\\')
        
        member_path = os.path.normpath(os.path.join(dest_path, sanitized_name))
        
        try:
            common = os.path.commonpath([dest_path, member_path])
        except ValueError:
            archive.close()
            return False
        
        if common != dest_path:
            archive.close()
            return False
        
        if member_path == dest_path and not member.isdir():
            archive.close()
            return False
        
        validated_members.append(member)
    
    for member in validated_members:
        sanitized_name = member.name.lstrip('/\\')
        if os.name == 'nt':
            if len(sanitized_name) >= 2 and sanitized_name[1] == ':':
                sanitized_name = sanitized_name[2:].lstrip('/\\')
        
        member_path = os.path.normpath(os.path.join(dest_path, sanitized_name))
        
        if member.isdir():
            try:
                os.makedirs(member_path, exist_ok=True)
            except (OSError, IOError):
                archive.close()
                return False
        elif member.isfile():
            parent_dir = os.path.dirname(member_path)
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except (OSError, IOError):
                archive.close()
                return False
            
            try:
                file_obj = archive.extractfile(member)
                if file_obj is None:
                    archive.close()
                    return False
                
                with open(member_path, 'wb') as f:
                    while True:
                        chunk = file_obj.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                file_obj.close()
            except (OSError, IOError, tarfile.TarError):
                archive.close()
                return False
    
    archive.close()
    return True
