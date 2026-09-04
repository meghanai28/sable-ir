import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_abs = os.path.normpath(os.path.abspath(dest_path))
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            validated_members = []
            
            for member in members:
                member_name = member.name
                
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        continue
                
                intended_path = os.path.normpath(os.path.join(dest_abs, member_name))
                
                if not intended_path.startswith(dest_abs + os.sep) and intended_path != dest_abs:
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    
                    if link_target is None:
                        return False
                    
                    if os.path.isabs(link_target):
                        normalized_target = os.path.normpath(link_target)
                    else:
                        parent_dir = os.path.dirname(intended_path)
                        normalized_target = os.path.normpath(os.path.join(parent_dir, link_target))
                    
                    if not normalized_target.startswith(dest_abs + os.sep) and normalized_target != dest_abs:
                        return False
                
                validated_members.append(member)
            
            for member in validated_members:
                try:
                    tf.extract(member, path=dest_abs)
                except Exception:
                    return False
            
            return True
            
    except Exception:
        return False
