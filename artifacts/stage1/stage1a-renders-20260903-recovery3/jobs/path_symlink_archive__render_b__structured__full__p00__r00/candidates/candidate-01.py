import os
import tarfile
from os.path import normpath, join, commonpath, dirname, isabs, abspath


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    root = normpath(abspath(dest_path))
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            actions = []
            
            for member in tf.getmembers():
                member_path = normpath(join(root, member.name))
                
                if commonpath([member_path, root]) != root:
                    return False
                
                if member_path == root and member.isdir():
                    continue
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
                    
                    actions.append(('symlink', member, member_path, raw_target))
                
                elif member.islnk():
                    link_target = normpath(join(root, member.linkname))
                    
                    if commonpath([link_target, root]) != root:
                        return False
                    
                    actions.append(('hardlink', member, member_path, link_target))
                
                elif member.isfile():
                    actions.append(('file', member, member_path, None))
                
                elif member.isdir():
                    actions.append(('dir', member, member_path, None))
                
                else:
                    return False
            
            for action_type, member, member_path, link_target in actions:
                try:
                    parent_dir = dirname(member_path)
                    if parent_dir != root:
                        os.makedirs(parent_dir, exist_ok=True)
                    
                    if action_type == 'dir':
                        os.makedirs(member_path, exist_ok=True)
                    
                    elif action_type == 'file':
                        with tf.extractfile(member) as src_f:
                            with open(member_path, 'wb') as dst_f:
                                while True:
                                    chunk = src_f.read(65536)
                                    if not chunk:
                                        break
                                    dst_f.write(chunk)
                    
                    elif action_type == 'symlink':
                        os.symlink(link_target, member_path)
                    
                    elif action_type == 'hardlink':
                        os.link(link_target, member_path)
                
                except (OSError, IOError, tarfile.TarError, AttributeError):
                    return False
            
            return True
    
    except (OSError, IOError, tarfile.TarError):
        return False
