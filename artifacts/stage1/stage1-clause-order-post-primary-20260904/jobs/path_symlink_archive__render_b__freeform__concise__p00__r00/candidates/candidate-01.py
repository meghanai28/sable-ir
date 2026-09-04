import os
import tarfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.abspath(os.path.realpath(dest_path))
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            validated_members = []
            link_targets = {}
            
            for member in members:
                member_name = member.name
                
                if os.path.isabs(member_name):
                    return False
                
                if member_name.startswith('/') or member_name.startswith('\\'):
                    return False
                
                extracted_path = os.path.join(dest_path, member_name)
                normalized_path = os.path.abspath(os.path.realpath(extracted_path))
                
                if not normalized_path.startswith(dest_path + os.sep) and normalized_path != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        return False
                    
                    member_parent = os.path.dirname(normalized_path)
                    target_path = os.path.join(member_parent, link_target)
                    normalized_target = os.path.abspath(os.path.realpath(target_path))
                    
                    if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                        return False
                    
                    link_targets[member_name] = normalized_target
                else:
                    link_targets[member_name] = None
                
                validated_members.append(member)
            
            for member in validated_members:
                member_name = member.name
                extracted_path = os.path.join(dest_path, member_name)
                normalized_path = os.path.abspath(os.path.realpath(extracted_path))
                
                if not normalized_path.startswith(dest_path + os.sep) and normalized_path != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    normalized_target = link_targets[member_name]
                    if normalized_target is None:
                        return False
                    
                    if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                        return False
                
                if member.isdir():
                    os.makedirs(normalized_path, exist_ok=True)
                elif member.isfile():
                    parent_dir = os.path.dirname(normalized_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    with tf.extractfile(member) as f:
                        if f is None:
                            return False
                        with open(normalized_path, 'wb') as out:
                            out.write(f.read())
                elif member.issym():
                    normalized_target = link_targets[member_name]
                    parent_dir = os.path.dirname(normalized_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    relative_target = os.path.relpath(normalized_target, parent_dir)
                    os.symlink(relative_target, normalized_path)
                elif member.islnk():
                    normalized_target = link_targets[member_name]
                    parent_dir = os.path.dirname(normalized_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    if os.path.exists(normalized_target):
                        os.link(normalized_target, normalized_path)
                    else:
                        os.symlink(os.path.relpath(normalized_target, parent_dir), normalized_path)
            
            return True
            
    except (tarfile.TarError, OSError, IOError, ValueError):
        return False
