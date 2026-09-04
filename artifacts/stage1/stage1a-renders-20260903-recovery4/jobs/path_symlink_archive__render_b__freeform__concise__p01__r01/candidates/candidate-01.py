import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.normpath(os.path.abspath(dest_path))
        if not os.path.exists(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            
            validated_paths = {}
            link_targets = {}
            
            for member in members:
                member_name = member.name
                if member_name.startswith('/') or member_name.startswith('..'):
                    return False
                
                abs_extract_path = os.path.normpath(os.path.abspath(os.path.join(dest_path, member_name)))
                
                if not _is_strictly_inside(abs_extract_path, dest_path):
                    return False
                
                validated_paths[member] = abs_extract_path
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    
                    if link_target.startswith('/'):
                        abs_link_target = os.path.normpath(os.path.abspath(link_target))
                    else:
                        member_dir = os.path.dirname(abs_extract_path)
                        abs_link_target = os.path.normpath(os.path.abspath(os.path.join(member_dir, link_target)))
                    
                    if not _is_strictly_inside(abs_link_target, dest_path):
                        return False
                    
                    link_targets[member] = abs_link_target
            
            for member in members:
                if member.islnk():
                    abs_link_target = link_targets[member]
                    referenced_member = None
                    for m in members:
                        m_path = os.path.normpath(os.path.abspath(os.path.join(dest_path, m.name)))
                        if m_path == abs_link_target:
                            referenced_member = m
                            break
                    
                    if referenced_member is None:
                        if not os.path.exists(abs_link_target):
                            return False
                        if not _is_strictly_inside(abs_link_target, dest_path):
                            return False
            
            for member in members:
                abs_extract_path = validated_paths[member]
                parent_dir = os.path.dirname(abs_extract_path)
                if not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)
                
                if member.issym():
                    abs_link_target = link_targets[member]
                    if os.path.lexists(abs_extract_path):
                        os.remove(abs_extract_path)
                    os.symlink(abs_link_target, abs_extract_path)
                elif member.islnk():
                    abs_link_target = link_targets[member]
                    if os.path.lexists(abs_extract_path):
                        os.remove(abs_extract_path)
                    os.link(abs_link_target, abs_extract_path)
                elif member.isdir():
                    if not os.path.exists(abs_extract_path):
                        os.makedirs(abs_extract_path, exist_ok=True)
                elif member.isfile():
                    with tar.extractfile(member) as f:
                        if f is None:
                            return False
                        with open(abs_extract_path, 'wb') as out_f:
                            out_f.write(f.read())
                else:
                    return False
            
            return True
    
    except Exception:
        return False


def _is_strictly_inside(path: str, dest: str) -> bool:
    return path == dest or (path.startswith(dest + os.sep))
