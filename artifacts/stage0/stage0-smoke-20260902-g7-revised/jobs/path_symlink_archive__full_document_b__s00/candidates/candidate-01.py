import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.abspath(os.path.normpath(dest_path))
    
    if not os.path.isdir(dest_path):
        return False
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            for member in members:
                member_path = member.name
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    normalized_target = os.path.normpath(link_target)
                    
                    if os.path.isabs(normalized_target):
                        return False
                    
                    resolved_target = os.path.normpath(os.path.join(dest_path, member_path, '..', normalized_target))
                    if not resolved_target.startswith(dest_path + os.sep) and resolved_target != dest_path:
                        return False
                
                full_member_path = os.path.normpath(os.path.join(dest_path, member_path))
                if not full_member_path.startswith(dest_path + os.sep) and full_member_path != dest_path:
                    return False
            
            for member in members:
                member_path = member.name
                full_member_path = os.path.normpath(os.path.join(dest_path, member_path))
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    normalized_target = os.path.normpath(link_target)
                    resolved_target = os.path.normpath(os.path.join(dest_path, member_path, '..', normalized_target))
                    
                    if not resolved_target.startswith(dest_path + os.sep) and resolved_target != dest_path:
                        return False
                
                if not full_member_path.startswith(dest_path + os.sep) and full_member_path != dest_path:
                    return False
            
            for member in members:
                tf.extract(member, dest_path)
            
            return True
            
    except (tarfile.TarError, OSError, IOError):
        return False
