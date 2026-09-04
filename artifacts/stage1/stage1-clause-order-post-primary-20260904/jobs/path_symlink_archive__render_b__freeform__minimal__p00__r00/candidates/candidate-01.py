import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.abspath(os.path.normpath(dest_path))
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            validated_paths = {}
            link_targets = {}
            
            for member in members:
                member_name = member.name
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        continue
                
                extraction_path = os.path.abspath(os.path.normpath(os.path.join(dest_path, member_name)))
                
                if extraction_path == dest_path:
                    return False
                
                if not extraction_path.startswith(dest_path + os.sep) and extraction_path != dest_path:
                    return False
                
                validated_paths[member] = extraction_path
                
                if member.issym() or member.islnk():
                    link_name = member.linkname
                    
                    if member.issym():
                        parent_dir = os.path.dirname(extraction_path)
                        normalized_target = os.path.abspath(os.path.normpath(os.path.join(parent_dir, link_name)))
                    else:
                        if os.path.isabs(link_name):
                            link_name = link_name.lstrip('/')
                        normalized_target = os.path.abspath(os.path.normpath(os.path.join(dest_path, link_name)))
                    
                    if normalized_target == dest_path:
                        return False
                    
                    if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                        return False
                    
                    link_targets[member] = normalized_target
            
            for member in members:
                if member not in validated_paths:
                    continue
                
                extraction_path = validated_paths[member]
                member_dir = os.path.dirname(extraction_path)
                
                if member_dir and not os.path.exists(member_dir):
                    os.makedirs(member_dir, exist_ok=True)
                
                if member.issym():
                    target = link_targets[member]
                    if os.path.exists(extraction_path):
                        os.remove(extraction_path)
                    os.symlink(target, extraction_path)
                elif member.islnk():
                    target = link_targets[member]
                    if os.path.exists(extraction_path):
                        os.remove(extraction_path)
                    if os.path.exists(target):
                        os.link(target, extraction_path)
                    else:
                        tf.extract(member, path=dest_path)
                elif member.isdir():
                    os.makedirs(extraction_path, exist_ok=True)
                else:
                    tf.extract(member, path=dest_path)
            
            return True
            
    except (tarfile.TarError, OSError, IOError):
        return False
