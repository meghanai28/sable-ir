import os
import tarfile
from os.path import abspath, normpath, join, commonpath, dirname


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    root = normpath(abspath(dest_path))
    
    try:
        tar = tarfile.open(tar_path, 'r:*')
    except (tarfile.TarError, OSError, IOError):
        return False
    
    approved_actions = []
    
    try:
        members = tar.getmembers()
    except (tarfile.TarError, OSError, IOError):
        tar.close()
        return False
    
    for member in members:
        member_path = normpath(join(root, member.name))
        
        try:
            common = commonpath([member_path, root])
        except ValueError:
            tar.close()
            return False
        
        if common != root:
            tar.close()
            return False
        
        if member_path == root and not member.isdir():
            tar.close()
            return False
        
        if member.issym() or member.islnk() or member.ischr() or member.isblk() or member.isfifo() or member.isdev():
            tar.close()
            return False
        
        if not (member.isfile() or member.isdir()):
            tar.close()
            return False
        
        approved_actions.append((member, member_path))
    
    for member, member_path in approved_actions:
        if member.isdir():
            try:
                os.makedirs(member_path, exist_ok=True)
            except (OSError, IOError):
                tar.close()
                return False
        elif member.isfile():
            parent_dir = dirname(member_path)
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except (OSError, IOError):
                tar.close()
                return False
            
            try:
                source = tar.extractfile(member)
            except (tarfile.TarError, OSError, IOError, KeyError):
                tar.close()
                return False
            
            if source is None:
                tar.close()
                return False
            
            try:
                with open(member_path, 'wb') as target:
                    while True:
                        chunk = source.read(65536)
                        if not chunk:
                            break
                        target.write(chunk)
            except (OSError, IOError):
                source.close()
                tar.close()
                return False
            finally:
                source.close()
    
    tar.close()
    return True
