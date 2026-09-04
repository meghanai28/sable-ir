import os
import tarfile
from os.path import abspath, normpath, join, dirname, commonpath, isabs


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    root = normpath(abspath(dest_path))
    
    if not root.endswith(os.sep):
        root += os.sep
    
    root = normpath(root)
    
    approved_actions = []
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf.getmembers():
                member_path = normpath(join(root, member.name))
                
                if commonpath([member_path, root]) != root:
                    return False
                
                if member_path == root and member.isdir():
                    pass
                elif member_path == root:
                    return False
                
                if member.issym():
                    raw_target = member.linkname
                    if isabs(raw_target):
                        link_target = normpath(raw_target)
                    else:
                        link_target = normpath(join(dirname(member_path), raw_target))
                    
                    if commonpath([link_target, root]) != root:
                        return False
                    
                    approved_actions.append(('symlink', member, member_path, raw_target))
                
                elif member.islnk():
                    link_target = normpath(join(root, member.linkname))
                    
                    if commonpath([link_target, root]) != root:
                        return False
                    
                    approved_actions.append(('hardlink', member, member_path, link_target))
                
                elif member.isfile():
                    approved_actions.append(('file', member, member_path, None))
                
                elif member.isdir():
                    approved_actions.append(('dir', member, member_path, None))
                
                else:
                    return False
            
            for action_type, member, safe_path, target in approved_actions:
                parent_dir = dirname(safe_path)
                
                if action_type == 'dir':
                    os.makedirs(safe_path, exist_ok=True)
                
                elif action_type == 'file':
                    os.makedirs(parent_dir, exist_ok=True)
                    with tf.extractfile(member) as src:
                        if src is None:
                            return False
                        with open(safe_path, 'wb') as dst:
                            while True:
                                chunk = src.read(8192)
                                if not chunk:
                                    break
                                dst.write(chunk)
                
                elif action_type == 'symlink':
                    os.makedirs(parent_dir, exist_ok=True)
                    if os.path.exists(safe_path) or os.path.islink(safe_path):
                        os.remove(safe_path)
                    os.symlink(target, safe_path)
                
                elif action_type == 'hardlink':
                    os.makedirs(parent_dir, exist_ok=True)
                    if os.path.exists(safe_path) or os.path.islink(safe_path):
                        os.remove(safe_path)
                    os.link(target, safe_path)
    
    except (OSError, tarfile.TarError, ValueError, TypeError):
        return False
    
    return True
