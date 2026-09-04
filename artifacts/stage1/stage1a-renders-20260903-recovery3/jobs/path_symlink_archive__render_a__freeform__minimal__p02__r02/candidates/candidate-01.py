import os
import tarfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.normpath(dest_path))
        
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    return False
                
                member_name = member.name.lstrip('/').lstrip('\\')
                if member_name.startswith('..'):
                    return False
                
                output_path = os.path.abspath(os.path.normpath(os.path.join(dest_path, member_name)))
                
                if not output_path.startswith(dest_path + os.sep) and output_path != dest_path:
                    return False
                
                if member.isfile():
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(tar.extractfile(member).read())
                elif member.isdir():
                    os.makedirs(output_path, exist_ok=True)
                    
        return True
    except Exception:
        return False
