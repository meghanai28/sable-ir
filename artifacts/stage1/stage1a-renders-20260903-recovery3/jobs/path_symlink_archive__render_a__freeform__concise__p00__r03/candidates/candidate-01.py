import os
import tarfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    abs_dest = os.path.abspath(dest_path)
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf.getmembers():
                if member.issym() or member.islnk():
                    return False
                
                member_path = os.path.join(abs_dest, member.name)
                normalized_member_path = os.path.abspath(member_path)
                
                if not normalized_member_path.startswith(abs_dest + os.sep) and normalized_member_path != abs_dest:
                    return False
                
                if member.isdir():
                    os.makedirs(normalized_member_path, exist_ok=True)
                elif member.isfile():
                    parent_dir = os.path.dirname(normalized_member_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    with tf.extractfile(member) as source:
                        if source is None:
                            return False
                        with open(normalized_member_path, 'wb') as target:
                            while True:
                                chunk = source.read(8192)
                                if not chunk:
                                    break
                                target.write(chunk)
                else:
                    return False
                    
        return True
    except Exception:
        return False
