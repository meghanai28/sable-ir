import os
import tarfile
from pathlib import Path

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest = Path(dest_path).resolve()
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members_to_extract = []
            
            for member in tf.getmembers():
                if member.issym() or member.islnk():
                    return False
                
                member_path = Path(member.name)
                if member_path.is_absolute():
                    member_path = member_path.relative_to('/')
                
                target_path = dest / member_path
                target_path = target_path.resolve()
                
                try:
                    target_path.relative_to(dest)
                except ValueError:
                    return False
                
                members_to_extract.append(member)
            
            for member in members_to_extract:
                member_path = Path(member.name)
                if member_path.is_absolute():
                    member_path = member_path.relative_to('/')
                
                target_path = (dest / member_path).resolve()
                
                try:
                    target_path.relative_to(dest)
                except ValueError:
                    return False
                
                tf.extract(member, path=str(dest))
                
                extracted_path = dest / member_path
                extracted_resolved = extracted_path.resolve()
                try:
                    extracted_resolved.relative_to(dest)
                except ValueError:
                    return False
        
        return True
    
    except Exception:
        return False
