import os
import tarfile
from typing import Set

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_abs = os.path.normpath(os.path.abspath(dest_path))
        
        if not dest_abs.endswith(os.sep):
            dest_abs = dest_abs + os.sep
        
        try:
            tf = tarfile.open(tar_path, 'r:*')
        except (tarfile.TarError, OSError, IOError):
            return False
        
        members = tf.getmembers()
        
        validated_members = []
        created_dirs: Set[str] = set()
        
        for member in members:
            member_name = member.name
            
            if os.path.isabs(member_name):
                member_name = member_name.lstrip('/')
                if os.name == 'nt':
                    member_name = member_name.lstrip('\\')
                    if len(member_name) >= 2 and member_name[1] == ':':
                        member_name = member_name[2:].lstrip('/\\')
            
            member_name = member_name.replace('/', os.sep)
            
            intended_path = os.path.normpath(os.path.join(dest_abs, member_name))
            
            if not intended_path.startswith(dest_abs):
                tf.close()
                return False
            
            if member.issym() or member.islnk():
                if member.issym():
                    link_target = member.linkname
                else:
                    link_target = member.linkname
                
                if os.path.isabs(link_target):
                    normalized_link = os.path.normpath(link_target)
                else:
                    link_parent = os.path.dirname(intended_path)
                    normalized_link = os.path.normpath(os.path.join(link_parent, link_target))
                
                if not normalized_link.startswith(dest_abs):
                    tf.close()
                    return False
            
            validated_members.append((member, intended_path))
        
        for member, intended_path in validated_members:
            if member.isdir():
                os.makedirs(intended_path, exist_ok=True)
                created_dirs.add(intended_path)
            elif member.isfile():
                parent_dir = os.path.dirname(intended_path)
                if parent_dir not in created_dirs:
                    os.makedirs(parent_dir, exist_ok=True)
                    created_dirs.add(parent_dir)
                
                source = tf.extractfile(member)
                if source is None:
                    tf.close()
                    return False
                
                try:
                    with open(intended_path, 'wb') as f:
                        while True:
                            chunk = source.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                except (OSError, IOError):
                    source.close()
                    tf.close()
                    return False
                finally:
                    source.close()
                
                try:
                    os.chmod(intended_path, member.mode)
                except (OSError, IOError):
                    pass
            elif member.issym():
                parent_dir = os.path.dirname(intended_path)
                if parent_dir not in created_dirs:
                    os.makedirs(parent_dir, exist_ok=True)
                    created_dirs.add(parent_dir)
                
                try:
                    if os.path.lexists(intended_path):
                        os.remove(intended_path)
                    os.symlink(member.linkname, intended_path)
                except (OSError, IOError):
                    tf.close()
                    return False
            elif member.islnk():
                parent_dir = os.path.dirname(intended_path)
                if parent_dir not in created_dirs:
                    os.makedirs(parent_dir, exist_ok=True)
                    created_dirs.add(parent_dir)
                
                link_target = member.linkname
                if os.path.isabs(link_target):
                    normalized_link_target = os.path.normpath(link_target)
                else:
                    link_parent = os.path.dirname(intended_path)
                    normalized_link_target = os.path.normpath(os.path.join(link_parent, link_target))
                
                if not normalized_link_target.startswith(dest_abs):
                    tf.close()
                    return False
                
                try:
                    if os.path.lexists(intended_path):
                        os.remove(intended_path)
                    os.link(normalized_link_target, intended_path)
                except (OSError, IOError):
                    tf.close()
                    return False
            else:
                tf.close()
                return False
        
        tf.close()
        return True
        
    except Exception:
        return False
