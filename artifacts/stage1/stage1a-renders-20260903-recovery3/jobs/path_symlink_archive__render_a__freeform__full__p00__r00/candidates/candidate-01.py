import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.normpath(os.path.abspath(dest_path))
    
    try:
        os.makedirs(dest_path, exist_ok=True)
    except (OSError, IOError):
        return False
    
    try:
        tar = tarfile.open(tar_path, 'r')
    except (tarfile.TarError, OSError, IOError):
        return False
    
    try:
        members = tar.getmembers()
    except (tarfile.TarError, OSError, IOError):
        tar.close()
        return False
    
    validated_members = []
    
    for member in members:
        if member.issym() or member.islnk():
            tar.close()
            return False
        
        if not member.isfile() and not member.isdir():
            continue
        
        name = member.name
        
        while name.startswith('/') or name.startswith('\\'):
            name = name[1:]
        
        if len(name) >= 2 and name[1] == ':':
            name = name[2:]
            while name.startswith('/') or name.startswith('\\'):
                name = name[1:]
        
        member_path = os.path.normpath(os.path.join(dest_path, name))
        
        try:
            common = os.path.commonpath([dest_path, member_path])
        except ValueError:
            tar.close()
            return False
        
        if common != dest_path:
            tar.close()
            return False
        
        if member_path == dest_path and member.isfile():
            tar.close()
            return False
        
        validated_members.append(member)
    
    for member in validated_members:
        try:
            if member.isdir():
                dir_path = os.path.normpath(os.path.join(dest_path, member.name))
                os.makedirs(dir_path, exist_ok=True)
            elif member.isfile():
                file_path = os.path.normpath(os.path.join(dest_path, member.name))
                parent_dir = os.path.dirname(file_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
                
                source = tar.extractfile(member)
                if source is None:
                    tar.close()
                    return False
                
                with open(file_path, 'wb') as target:
                    while True:
                        chunk = source.read(65536)
                        if not chunk:
                            break
                        target.write(chunk)
                source.close()
        except (OSError, IOError, tarfile.TarError):
            tar.close()
            return False
    
    tar.close()
    return True
