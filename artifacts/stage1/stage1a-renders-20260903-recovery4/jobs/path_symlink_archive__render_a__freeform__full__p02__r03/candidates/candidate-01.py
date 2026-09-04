import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    resolved_dest = os.path.abspath(os.path.normpath(dest_path))
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            
            for member in members:
                if member.issym() or member.islnk():
                    return False
                
                if member.isfile() or member.isdir():
                    candidate_path = os.path.join(resolved_dest, member.name)
                    normalized_path = os.path.abspath(os.path.normpath(candidate_path))
                    
                    try:
                        common = os.path.commonpath([resolved_dest, normalized_path])
                    except ValueError:
                        return False
                    
                    if common != resolved_dest:
                        return False
                    
                    if normalized_path == resolved_dest and not member.isdir():
                        return False
                    
                    if member.isdir():
                        os.makedirs(normalized_path, exist_ok=True)
                    elif member.isfile():
                        parent_dir = os.path.dirname(normalized_path)
                        os.makedirs(parent_dir, exist_ok=True)
                        
                        with open(normalized_path, 'wb') as out_file:
                            with tar.extractfile(member) as in_file:
                                while True:
                                    chunk = in_file.read(65536)
                                    if not chunk:
                                        break
                                    out_file.write(chunk)
                else:
                    return False
                    
    except Exception:
        return False
    
    return True
