import os
import tarfile
import stat


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        base_dir = os.path.abspath(os.path.realpath(dest_path))
        os.makedirs(base_dir, exist_ok=True)
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            validated_files = []
            validated_dirs = []
            validated_symlinks = []
            validated_hardlinks = []
            
            for member in members:
                member_name = member.name
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_target = os.path.normpath(link_target)
                    else:
                        member_dir = os.path.dirname(member_name)
                        if member_dir == '':
                            member_dir = '.'
                        combined = os.path.join(member_dir, link_target)
                        normalized_target = os.path.normpath(combined)
                    
                    if normalized_target.startswith('..') or normalized_target.startswith('/..'):
                        return False
                    
                    if os.path.isabs(normalized_target):
                        abs_target = normalized_target
                    else:
                        abs_target = os.path.join(base_dir, normalized_target)
                    
                    abs_target = os.path.abspath(abs_target)
                    
                    real_target = os.path.realpath(abs_target)
                    
                    if not real_target.startswith(base_dir + os.sep) and real_target != base_dir:
                        return False
                    
                    member_path = os.path.join(base_dir, member_name)
                    norm_member_path = os.path.normpath(member_path)
                    
                    if not norm_member_path.startswith(base_dir + os.sep) and norm_member_path != base_dir:
                        return False
                    
                    if member.issym():
                        validated_symlinks.append((norm_member_path, link_target))
                    else:
                        validated_hardlinks.append((norm_member_path, abs_target))
                
                elif member.isdir():
                    member_path = os.path.join(base_dir, member_name)
                    norm_member_path = os.path.normpath(member_path)
                    
                    if not norm_member_path.startswith(base_dir + os.sep) and norm_member_path != base_dir:
                        return False
                    
                    validated_dirs.append(norm_member_path)
                
                elif member.isfile() or member.isreg():
                    member_path = os.path.join(base_dir, member_name)
                    norm_member_path = os.path.normpath(member_path)
                    
                    if not norm_member_path.startswith(base_dir + os.sep) and norm_member_path != base_dir:
                        return False
                    
                    validated_files.append((norm_member_path, member))
                
                else:
                    continue
            
            for dir_path in validated_dirs:
                try:
                    os.makedirs(dir_path, exist_ok=True)
                except OSError:
                    return False
            
            for file_path, member in validated_files:
                try:
                    parent_dir = os.path.dirname(file_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
                    
                    f = tf.extractfile(member)
                    if f is None:
                        return False
                    
                    with open(file_path, 'wb') as out_f:
                        out_f.write(f.read())
                    
                    mode = member.mode
                    if mode:
                        os.chmod(file_path, mode)
                except (OSError, tarfile.TarError, IOError):
                    return False
            
            for link_path, target in validated_symlinks:
                try:
                    parent_dir = os.path.dirname(link_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
                    
                    if os.path.lexists(link_path):
                        os.remove(link_path)
                    
                    os.symlink(target, link_path)
                except OSError:
                    return False
            
            for link_path, target in validated_hardlinks:
                try:
                    parent_dir = os.path.dirname(link_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
                    
                    if os.path.lexists(link_path):
                        os.remove(link_path)
                    
                    os.link(target, link_path)
                except OSError:
                    return False
    
    except (tarfile.TarError, OSError, IOError):
        return False
    
    return True
