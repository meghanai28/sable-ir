import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.normpath(os.path.abspath(dest_path))
    
    try:
        os.makedirs(dest_path, exist_ok=True)
    except (OSError, PermissionError):
        return False
    
    try:
        archive = tarfile.open(tar_path, 'r')
    except (tarfile.TarError, OSError, PermissionError):
        return False
    
    try:
        members = archive.getmembers()
    except (tarfile.TarError, OSError):
        archive.close()
        return False
    
    validated_members = []
    
    for member in members:
        if member.issym() or member.islnk():
            archive.close()
            return False
        
        if not member.isfile() and not member.isdir():
            continue
        
        member_name = member.name
        
        while member_name.startswith('/') or member_name.startswith('\\'):
            member_name = member_name[1:]
        
        if len(member_name) >= 2 and member_name[1] == ':':
            member_name = member_name[2:]
            while member_name.startswith('/') or member_name.startswith('\\'):
                member_name = member_name[1:]
        
        member_name = member_name.lstrip('/\\')
        
        try:
            normalized_member_path = os.path.normpath(os.path.join(dest_path, member_name))
        except (ValueError, OSError):
            archive.close()
            return False
        
        try:
            common = os.path.commonpath([dest_path, normalized_member_path])
        except ValueError:
            archive.close()
            return False
        
        if common != dest_path:
            archive.close()
            return False
        
        if normalized_member_path == dest_path and not member.isdir():
            archive.close()
            return False
        
        validated_members.append(member)
    
    for member in validated_members:
        try:
            if member.isdir():
                member_dir_path = os.path.normpath(os.path.join(dest_path, member.name.lstrip('/\\')))
                os.makedirs(member_dir_path, exist_ok=True)
            else:
                member_file_path = os.path.normpath(os.path.join(dest_path, member.name.lstrip('/\\')))
                parent_dir = os.path.dirname(member_file_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
                
                source = archive.extractfile(member)
                if source is None:
                    archive.close()
                    return False
                
                try:
                    with open(member_file_path, 'wb') as target:
                        while True:
                            chunk = source.read(8192)
                            if not chunk:
                                break
                            target.write(chunk)
                finally:
                    source.close()
        except (OSError, PermissionError, tarfile.TarError):
            archive.close()
            return False
    
    archive.close()
    return True
