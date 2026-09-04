import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    abs_dest = os.path.abspath(os.path.normpath(dest_path))
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            validated_dirs = []
            validated_files = []
            validated_symlinks = []
            validated_hardlinks = []
            
            for member in members:
                member_name = member.name
                if member_name.startswith('/') or member_name.startswith('\\'):
                    member_name = member_name.lstrip('/\\')
                if os.path.isabs(member_name):
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if link_target.startswith('/') or link_target.startswith('\\'):
                        normalized_target = os.path.normpath(link_target)
                    else:
                        member_dir = os.path.dirname(member_name)
                        if member_dir:
                            combined = os.path.join(member_dir, link_target)
                        else:
                            combined = link_target
                        normalized_target = os.path.normpath(combined)
                    
                    if os.path.isabs(normalized_target):
                        resolved_target = os.path.abspath(os.path.normpath(os.path.join(abs_dest, normalized_target.lstrip('/\\'))))
                    else:
                        resolved_target = os.path.abspath(os.path.normpath(os.path.join(abs_dest, normalized_target)))
                    
                    if not (resolved_target == abs_dest or resolved_target.startswith(abs_dest + os.sep)):
                        return False
                    
                    member_path = os.path.abspath(os.path.normpath(os.path.join(abs_dest, member_name)))
                    if not (member_path == abs_dest or member_path.startswith(abs_dest + os.sep)):
                        return False
                    
                    if member.issym():
                        validated_symlinks.append((member_path, member))
                    else:
                        validated_hardlinks.append((member_path, member))
                
                elif member.isdir():
                    member_path = os.path.abspath(os.path.normpath(os.path.join(abs_dest, member_name)))
                    if not (member_path == abs_dest or member_path.startswith(abs_dest + os.sep)):
                        return False
                    validated_dirs.append((member_path, member))
                
                elif member.isfile() or member.isreg():
                    member_path = os.path.abspath(os.path.normpath(os.path.join(abs_dest, member_name)))
                    if not (member_path == abs_dest or member_path.startswith(abs_dest + os.sep)):
                        return False
                    validated_files.append((member_path, member))
                
                else:
                    continue
            
            for member_path, member in validated_dirs:
                try:
                    os.makedirs(member_path, exist_ok=True)
                    if hasattr(member, 'mode'):
                        os.chmod(member_path, member.mode)
                except (OSError, IOError):
                    return False
            
            for member_path, member in validated_files:
                try:
                    os.makedirs(os.path.dirname(member_path), exist_ok=True)
                    with tf.extractfile(member) as fobj:
                        if fobj is None:
                            return False
                        with open(member_path, 'wb') as out:
                            out.write(fobj.read())
                    if hasattr(member, 'mode'):
                        os.chmod(member_path, member.mode)
                except (OSError, IOError, AttributeError):
                    return False
            
            for member_path, member in validated_symlinks:
                try:
                    os.makedirs(os.path.dirname(member_path), exist_ok=True)
                    os.symlink(member.linkname, member_path)
                except (OSError, IOError):
                    return False
            
            for member_path, member in validated_hardlinks:
                try:
                    os.makedirs(os.path.dirname(member_path), exist_ok=True)
                    source_path = os.path.abspath(os.path.normpath(os.path.join(abs_dest, member.linkname)))
                    os.link(source_path, member_path)
                except (OSError, IOError):
                    return False
    
    except (tarfile.TarError, OSError, IOError):
        return False
    
    return True
