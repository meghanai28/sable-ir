import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_abs = os.path.abspath(dest_path)
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            validated = []
            
            for member in members:
                member_name = member.name
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        continue
                
                member_path = os.path.join(dest_abs, member_name)
                member_norm = os.path.normpath(member_path)
                
                if not member_norm.startswith(dest_abs + os.sep) and member_norm != dest_abs:
                    return False
                
                if member.issym() or member.islnk():
                    if member.issym():
                        link_target = member.linkname
                    else:
                        link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        link_target = link_target.lstrip('/')
                        if not link_target:
                            return False
                        target_path = os.path.join(dest_abs, link_target)
                    else:
                        member_parent = os.path.dirname(member_norm)
                        target_path = os.path.join(member_parent, link_target)
                    
                    target_norm = os.path.normpath(target_path)
                    
                    if not target_norm.startswith(dest_abs + os.sep) and target_norm != dest_abs:
                        return False
                
                validated.append((member, member_norm))
            
            for member, extract_path in validated:
                if member.isdir():
                    os.makedirs(extract_path, exist_ok=True)
                elif member.isfile():
                    parent_dir = os.path.dirname(extract_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    with tf.extractfile(member) as f:
                        if f is None:
                            return False
                        with open(extract_path, 'wb') as out:
                            out.write(f.read())
                elif member.issym():
                    parent_dir = os.path.dirname(extract_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    os.symlink(member.linkname, extract_path)
                elif member.islnk():
                    parent_dir = os.path.dirname(extract_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    if os.path.isabs(member.linkname):
                        link_target = member.linkname.lstrip('/')
                        if not link_target:
                            return False
                        hardlink_source = os.path.join(dest_abs, link_target)
                    else:
                        member_parent = os.path.dirname(extract_path)
                        hardlink_source = os.path.join(member_parent, member.linkname)
                        hardlink_source = os.path.normpath(hardlink_source)
                    os.link(hardlink_source, extract_path)
            
            return True
    
    except (tarfile.TarError, OSError, IOError, ValueError):
        return False
