import os
import tarfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        trust_anchor = os.path.realpath(dest_path)
        trust_anchor = os.path.abspath(trust_anchor)
        strict_prefix = trust_anchor + os.sep
        
        archive = tarfile.open(tar_path, 'r:*')
    except Exception:
        return False
    
    try:
        for member in archive.getmembers():
            if member.issym() or member.islnk():
                archive.close()
                return False
            
            if not member.isreg() and not member.isdir():
                archive.close()
                return False
            
            member_name = member.name
            
            candidate_path = os.path.normpath(os.path.join(trust_anchor, member_name))
            
            if not candidate_path.startswith(strict_prefix):
                archive.close()
                return False
            
            if candidate_path == trust_anchor:
                archive.close()
                return False
            
            if member.isdir():
                os.makedirs(candidate_path, exist_ok=True)
            else:
                parent_dir = os.path.dirname(candidate_path)
                if not parent_dir.startswith(strict_prefix) and parent_dir != trust_anchor:
                    archive.close()
                    return False
                os.makedirs(parent_dir, exist_ok=True)
                
                file_obj = archive.extractfile(member)
                if file_obj is None:
                    archive.close()
                    return False
                
                with open(candidate_path, 'wb') as f:
                    while True:
                        chunk = file_obj.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                file_obj.close()
        
        archive.close()
        return True
    
    except Exception:
        try:
            archive.close()
        except Exception:
            pass
        return False
