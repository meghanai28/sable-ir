import os
import tarfile
from pathlib import Path


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.realpath(os.path.abspath(dest_path))
        
        if not os.path.isdir(dest_path):
            return False
        
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            validated_members = []
            symlink_targets = {}
            
            for member in members:
                member_name = member.name
                
                if os.path.isabs(member_name):
                    return False
                
                if '..' in member_name.split(os.sep) or member_name.startswith('..'):
                    if '..' in member_name.split(os.sep):
                        parts = member_name.split(os.sep)
                        if '..' in parts:
                            return False
                
                normalized_member = os.path.normpath(member_name)
                if normalized_member.startswith('..') or os.path.isabs(normalized_member):
                    return False
                
                extract_path = os.path.realpath(os.path.join(dest_path, normalized_member))
                
                if not extract_path.startswith(dest_path + os.sep) and extract_path != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        resolved_target = os.path.realpath(link_target)
                        if not resolved_target.startswith(dest_path + os.sep) and resolved_target != dest_path:
                            return False
                    else:
                        target_dir = os.path.dirname(extract_path)
                        resolved_target = os.path.realpath(os.path.join(target_dir, link_target))
                        if not resolved_target.startswith(dest_path + os.sep) and resolved_target != dest_path:
                            return False
                    
                    if member.issym():
                        symlink_targets[extract_path] = resolved_target
                
                validated_members.append(member)
            
            for member in validated_members:
                member_name = member.name
                normalized_member = os.path.normpath(member_name)
                extract_path = os.path.realpath(os.path.join(dest_path, normalized_member))
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        resolved_target = os.path.realpath(link_target)
                    else:
                        target_dir = os.path.dirname(extract_path)
                        resolved_target = os.path.realpath(os.path.join(target_dir, link_target))
                    
                    if not resolved_target.startswith(dest_path + os.sep) and resolved_target != dest_path:
                        return False
                
                if member.isdir():
                    target = extract_path
                else:
                    parent = os.path.dirname(extract_path)
                    if not parent.startswith(dest_path + os.sep) and parent != dest_path:
                        return False
            
            for member in validated_members:
                member_name = member.name
                normalized_member = os.path.normpath(member_name)
                extract_path = os.path.realpath(os.path.join(dest_path, normalized_member))
                
                if member.issym():
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        final_target = link_target
                    else:
                        final_target = link_target
                    
                    parent_dir = os.path.dirname(extract_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    
                    if os.path.exists(extract_path) or os.path.islink(extract_path):
                        os.remove(extract_path)
                    
                    os.symlink(final_target, extract_path)
                
                elif member.islnk():
                    link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_target = os.path.normpath(link_target)
                        target_path = os.path.realpath(os.path.join(dest_path, normalized_target.lstrip(os.sep)))
                    else:
                        target_dir = os.path.dirname(extract_path)
                        target_path = os.path.realpath(os.path.join(target_dir, link_target))
                    
                    if not target_path.startswith(dest_path + os.sep) and target_path != dest_path:
                        return False
                    
                    parent_dir = os.path.dirname(extract_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    
                    if os.path.exists(extract_path) or os.path.islink(extract_path):
                        os.remove(extract_path)
                    
                    os.link(target_path, extract_path)
                
                elif member.isdir():
                    os.makedirs(extract_path, exist_ok=True)
                    mode = member.mode
                    if mode:
                        os.chmod(extract_path, mode)
                
                elif member.isfile() or member.isreg():
                    parent_dir = os.path.dirname(extract_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    
                    if os.path.exists(extract_path) or os.path.islink(extract_path):
                        os.remove(extract_path)
                    
                    with tf.extractfile(member) as fobj:
                        if fobj is None:
                            return False
                        with open(extract_path, 'wb') as outf:
                            while True:
                                chunk = fobj.read(65536)
                                if not chunk:
                                    break
                                outf.write(chunk)
                    
                    mode = member.mode
                    if mode:
                        os.chmod(extract_path, mode)
                
                elif member.ischr() or member.isblk() or member.isfifo() or member.isdev():
                    return False
                
                else:
                    return False
            
            return True
            
    except (tarfile.TarError, OSError, IOError, ValueError, KeyError):
        return False
    except Exception:
        return False
