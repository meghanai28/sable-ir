import os
import tarfile
from pathlib import Path

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_real = os.path.realpath(dest_path)
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            for member in members:
                member_name = member.name
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                if member_name.startswith('..'):
                    return False
                
                intended_path = os.path.join(dest_real, member_name)
                intended_real = os.path.realpath(intended_path)
                
                if not intended_real.startswith(dest_real + os.sep) and intended_real != dest_real:
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if link_target is None:
                        return False
                    
                    if os.path.isabs(link_target):
                        normalized_link = os.path.normpath(link_target)
                    else:
                        parent_dir = os.path.dirname(intended_real)
                        normalized_link = os.path.realpath(os.path.join(parent_dir, link_target))
                    
                    if not normalized_link.startswith(dest_real + os.sep) and normalized_link != dest_real:
                        return False
            
            for member in members:
                member_name = member.name
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                
                intended_path = os.path.join(dest_real, member_name)
                intended_real = os.path.realpath(intended_path)
                
                if not intended_real.startswith(dest_real + os.sep) and intended_real != dest_real:
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if link_target is None:
                        return False
                    
                    if os.path.isabs(link_target):
                        normalized_link = os.path.normpath(link_target)
                    else:
                        parent_dir = os.path.dirname(intended_real)
                        normalized_link = os.path.realpath(os.path.join(parent_dir, link_target))
                    
                    if not normalized_link.startswith(dest_real + os.sep) and normalized_link != dest_real:
                        return False
            
            for member in members:
                tf.extract(member, path=dest_real)
            
            return True
            
    except (tarfile.TarError, OSError, ValueError):
        return False
