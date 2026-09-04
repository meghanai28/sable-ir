import os
import tarfile
from os.path import normpath, join, dirname, commonpath, isabs, abspath, exists

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    root = normpath(abspath(dest_path))
    
    if not root.endswith(os.sep):
        root = root + os.sep
    
    actions = []
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf.getmembers():
                member_path = normpath(join(root, member.name))
                
                if commonpath([member_path, root]) != root.rstrip(os.sep):
                    return False
                
                if member_path == root.rstrip(os.sep) and member.type not in (tarfile.DIRTYPE,):
                    return False
                
                if member.issym():
                    raw_target = member.linkname
                    if isabs(raw_target):
                        link_target = normpath(raw_target)
                    else:
                        link_target = normpath(join(dirname(member_path), raw_target))
                    
                    if commonpath([link_target, root]) != root.rstrip(os.sep):
                        return False
                    
                    actions.append(('symlink', member_path, member.linkname, member))
                
                elif member.islnk():
                    link_target = normpath(join(root, member.linkname))
                    
                    if commonpath([link_target, root]) != root.rstrip(os.sep):
                        return False
                    
                    actions.append(('hardlink', member_path, link_target, member))
                
                elif member.isdir():
                    actions.append(('dir', member_path, None, member))
                
                elif member.isfile():
                    actions.append(('file', member_path, None, member))
                
                else:
                    return False
            
            for action_type, member_path, link_target, member in actions:
                parent_dir = dirname(member_path)
                if parent_dir and not exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)
                
                if action_type == 'dir':
                    os.makedirs(member_path, exist_ok=True)
                
                elif action_type == 'file':
                    with tf.extractfile(member) as src:
                        if src is None:
                            return False
                        with open(member_path, 'wb') as dst:
                            while True:
                                chunk = src.read(8192)
                                if not chunk:
                                    break
                                dst.write(chunk)
                
                elif action_type == 'symlink':
                    if exists(member_path):
                        os.remove(member_path)
                    os.symlink(link_target, member_path)
                
                elif action_type == 'hardlink':
                    if exists(member_path):
                        os.remove(member_path)
                    os.link(link_target, member_path)
    
    except (OSError, tarfile.TarError, ValueError, TypeError):
        return False
    
    return True
