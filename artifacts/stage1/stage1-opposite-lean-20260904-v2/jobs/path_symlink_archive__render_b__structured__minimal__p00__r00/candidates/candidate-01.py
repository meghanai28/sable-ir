import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_abs = os.path.abspath(dest_path)
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members_to_extract = []
            
            for member in tf.getmembers():
                if member.issym() or member.islnk():
                    return False
                
                member_path = os.path.join(dest_abs, member.name)
                member_abs = os.path.abspath(member_path)
                
                if not member_abs.startswith(dest_abs + os.sep) and member_abs != dest_abs:
                    return False
                
                if member.isfile() or member.isdir():
                    members_to_extract.append(member)
                else:
                    return False
            
            for member in members_to_extract:
                try:
                    tf.extract(member, path=dest_abs)
                except Exception:
                    return False
            
            return True
            
    except Exception:
        return False
