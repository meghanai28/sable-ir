import os
import tarfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        base_path = os.path.abspath(os.path.normpath(dest_path))
        os.makedirs(base_path, exist_ok=True)
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            validated_members = []
            
            for member in members:
                member_name = member.name
                if member_name.startswith('/') or member_name.startswith(os.sep):
                    member_name = member_name.lstrip('/').lstrip(os.sep)
                if not member_name:
                    return False
                
                normalized_member_name = os.path.normpath(member_name)
                if normalized_member_name.startswith('..'):
                    return False
                
                extract_path = os.path.normpath(os.path.join(base_path, normalized_member_name))
                
                if not extract_path.startswith(base_path + os.sep) and extract_path != base_path:
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if link_target.startswith('/'):
                        resolved_target = os.path.normpath(link_target)
                    else:
                        member_dir = os.path.dirname(extract_path)
                        resolved_target = os.path.normpath(os.path.join(member_dir, link_target))
                    
                    if not (resolved_target == base_path or resolved_target.startswith(base_path + os.sep)):
                        return False
                
                validated_members.append((member, extract_path))
            
            for member, extract_path in validated_members:
                try:
                    if member.isdir():
                        os.makedirs(extract_path, exist_ok=True)
                    elif member.isfile():
                        os.makedirs(os.path.dirname(extract_path), exist_ok=True)
                        with tf.extractfile(member) as fsrc:
                            if fsrc is None:
                                return False
                            with open(extract_path, 'wb') as fdst:
                                while True:
                                    chunk = fsrc.read(65536)
                                    if not chunk:
                                        break
                                    fdst.write(chunk)
                    elif member.issym() or member.islnk():
                        link_target = member.linkname
                        if link_target.startswith('/'):
                            resolved_target = os.path.normpath(link_target)
                        else:
                            member_dir = os.path.dirname(extract_path)
                            resolved_target = os.path.normpath(os.path.join(member_dir, link_target))
                        
                        if not (resolved_target == base_path or resolved_target.startswith(base_path + os.sep)):
                            return False
                        
                        if member.issym():
                            os.symlink(link_target, extract_path)
                        else:
                            os.link(resolved_target, extract_path)
                    else:
                        continue
                except (OSError, IOError, ValueError, tarfile.TarError):
                    return False
            
            return True
    except (OSError, IOError, ValueError, tarfile.TarError):
        return False
