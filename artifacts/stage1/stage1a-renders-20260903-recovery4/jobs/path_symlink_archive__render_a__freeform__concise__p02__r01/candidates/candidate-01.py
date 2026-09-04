import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.normpath(dest_path))
        
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    return False
                
                if not (member.isfile() or member.isdir()):
                    return False
                
                member_path = os.path.join(dest_path, member.name)
                member_path = os.path.abspath(os.path.normpath(member_path))
                
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
                
                if member.isdir():
                    os.makedirs(member_path, exist_ok=True)
                elif member.isfile():
                    parent_dir = os.path.dirname(member_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    tar.extract(member, dest_path)
        
        return True
    except Exception:
        return False
