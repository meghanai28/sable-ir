import os
import tarfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        trust_anchor = os.path.abspath(os.path.realpath(dest_path))
        strict_prefix = trust_anchor + os.sep
        
        if not os.path.exists(trust_anchor):
            os.makedirs(trust_anchor, exist_ok=True)
        
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    return False
                
                if not (member.isfile() or member.isdir()):
                    return False
                
                member_name = member.name
                
                candidate_path = os.path.normpath(os.path.join(trust_anchor, member_name))
                
                if not candidate_path.startswith(strict_prefix):
                    return False
                
                if candidate_path == trust_anchor:
                    return False
                
                if member.isdir():
                    os.makedirs(candidate_path, exist_ok=True)
                else:
                    parent_dir = os.path.dirname(candidate_path)
                    if not parent_dir.startswith(strict_prefix) and parent_dir != trust_anchor:
                        return False
                    os.makedirs(parent_dir, exist_ok=True)
                    
                    file_obj = tar.extractfile(member)
                    if file_obj is None:
                        return False
                    
                    with open(candidate_path, 'wb') as f:
                        while True:
                            chunk = file_obj.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                    file_obj.close()
        
        return True
    
    except Exception:
        return False
