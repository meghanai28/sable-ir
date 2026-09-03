import os
import tarfile
from typing import Optional

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        abs_dest = os.path.normpath(os.path.abspath(dest_path))
        if not abs_dest.endswith(os.sep):
            abs_dest += os.sep
        
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            
            validated_paths = {}
            link_targets = {}
            
            for member in members:
                member_abs_path = os.path.normpath(os.path.join(abs_dest, member.name))
                if not member_abs_path.startswith(abs_dest):
                    return False
                
                member_dir = os.path.dirname(member_abs_path)
                
                if member.issym() or member.islnk():
                    if member.issym():
                        if os.path.isabs(member.linkname):
                            link_target = os.path.normpath(os.path.join(abs_dest, member.linkname.lstrip('/')))
                        else:
                            link_target = os.path.normpath(os.path.join(member_dir, member.linkname))
                    else:
                        if os.path.isabs(member.linkname):
                            link_target = os.path.normpath(os.path.join(abs_dest, member.linkname.lstrip('/')))
                        else:
                            hardlink_src_name = member.linkname
                            if hardlink_src_name in validated_paths:
                                link_target = validated_paths[hardlink_src_name]
                            else:
                                link_target = os.path.normpath(os.path.join(abs_dest, hardlink_src_name))
                    
                    if not link_target.startswith(abs_dest):
                        return False
                    
                    link_targets[member.name] = link_target
                
                validated_paths[member.name] = member_abs_path
            
            for member_name, target in link_targets.items():
                if not target.startswith(abs_dest):
                    return False
            
            for member in members:
                member_abs_path = validated_paths[member.name]
                
                if member.issym():
                    target = link_targets[member.name]
                    os.makedirs(os.path.dirname(member_abs_path), exist_ok=True)
                    os.symlink(target, member_abs_path)
                elif member.islnk():
                    target = link_targets[member.name]
                    if not os.path.exists(target):
                        continue
                    os.makedirs(os.path.dirname(member_abs_path), exist_ok=True)
                    os.link(target, member_abs_path)
                elif member.isdir():
                    os.makedirs(member_abs_path, exist_ok=True)
                elif member.isfile():
                    os.makedirs(os.path.dirname(member_abs_path), exist_ok=True)
                    with tar.extractfile(member) as f:
                        if f is None:
                            return False
                        with open(member_abs_path, 'wb') as out:
                            while True:
                                chunk = f.read(8192)
                                if not chunk:
                                    break
                                out.write(chunk)
                else:
                    return False
            
            return True
    
    except Exception:
        return False
