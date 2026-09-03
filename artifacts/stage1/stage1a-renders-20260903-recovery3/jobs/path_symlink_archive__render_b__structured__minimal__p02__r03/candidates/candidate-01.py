import os
import tarfile
from typing import Optional

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_abs = os.path.normpath(os.path.abspath(dest_path))
        if not dest_abs.endswith(os.sep):
            dest_abs += os.sep
        
        if not os.path.exists(dest_abs):
            try:
                os.makedirs(dest_abs, exist_ok=True)
            except OSError:
                return False
        
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
                
                if not (intended_path == dest_abs or intended_path.startswith(dest_abs)):
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    
                    if link_target:
                        if os.path.isabs(link_target):
                            normalized_target = os.path.normpath(link_target)
                            if not (normalized_target == dest_abs or normalized_target.startswith(dest_abs)):
                                return False
                        else:
                            link_dir = os.path.dirname(intended_path)
                            normalized_target = os.path.normpath(os.path.join(link_dir, link_target))
                            if not (normalized_target == dest_abs or normalized_target.startswith(dest_abs)):
                                return False
                
                validated_members.append((member, intended_path))
            
            for member, intended_path in validated_members:
                try:
                    if member.isdir():
                        os.makedirs(intended_path, exist_ok=True)
                        continue
                    
                    parent_dir = os.path.dirname(intended_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
                    
                    if member.isfile():
                        with tf.extractfile(member) as fobj:
                            if fobj is None:
                                return False
                            with open(intended_path, 'wb') as outf:
                                while True:
                                    chunk = fobj.read(65536)
                                    if not chunk:
                                        break
                                    outf.write(chunk)
                        os.chmod(intended_path, member.mode)
                    
                    elif member.issym():
                        link_target = member.linkname
                        if os.path.isabs(link_target):
                            link_target = link_target.lstrip('/')
                            link_target = os.path.join(dest_abs, link_target)
                        os.symlink(link_target, intended_path)
                    
                    elif member.islnk():
                        link_target = member.linkname
                        if os.path.isabs(link_target):
                            link_target = link_target.lstrip('/')
                            link_target = os.path.join(dest_abs, link_target)
                        else:
                            link_dir = os.path.dirname(intended_path)
                            link_target = os.path.normpath(os.path.join(link_dir, link_target))
                        os.link(link_target, intended_path)
                    
                    else:
                        return False
                        
                except (OSError, IOError, tarfile.TarError):
                    return False
            
            return True
            
    except (OSError, IOError, tarfile.TarError):
        return False
