import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.realpath(dest_path))
        if not os.path.isdir(dest_path):
            return False
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            validated_members = []
            for member in members:
                member_name = member.name
                if member_name.startswith('/') or member_name.startswith('\\'):
                    member_name = member_name[1:]
                if '..' in member_name.split('/'):
                    return False
                
                normalized_member_path = os.path.normpath(os.path.join(dest_path, member_name))
                try:
                    real_member_path = os.path.realpath(normalized_member_path)
                except (OSError, ValueError):
                    return False
                
                if not (real_member_path == dest_path or real_member_path.startswith(dest_path + os.sep)):
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if link_target.startswith('/') or link_target.startswith('\\'):
                        if member.issym():
                            resolved_link_target = os.path.normpath(os.path.join(dest_path, link_target))
                        else:
                            resolved_link_target = os.path.normpath(os.path.join(os.path.dirname(normalized_member_path), link_target))
                    else:
                        resolved_link_target = os.path.normpath(os.path.join(os.path.dirname(normalized_member_path), link_target))
                    
                    try:
                        real_link_target = os.path.realpath(resolved_link_target)
                    except (OSError, ValueError):
                        return False
                    
                    if not (real_link_target == dest_path or real_link_target.startswith(dest_path + os.sep)):
                        return False
                
                validated_members.append(member)
            
            for member in validated_members:
                member_name = member.name
                if member_name.startswith('/') or member_name.startswith('\\'):
                    member_name = member_name[1:]
                
                normalized_member_path = os.path.normpath(os.path.join(dest_path, member_name))
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if link_target.startswith('/') or link_target.startswith('\\'):
                        if member.issym():
                            resolved_link_target = os.path.normpath(os.path.join(dest_path, link_target))
                        else:
                            resolved_link_target = os.path.normpath(os.path.join(os.path.dirname(normalized_member_path), link_target))
                    else:
                        resolved_link_target = os.path.normpath(os.path.join(os.path.dirname(normalized_member_path), link_target))
                    
                    try:
                        os.makedirs(os.path.dirname(normalized_member_path), exist_ok=True)
                    except (OSError, ValueError):
                        return False
                    
                    if member.issym():
                        try:
                            if os.path.exists(normalized_member_path) or os.path.islink(normalized_member_path):
                                os.remove(normalized_member_path)
                            os.symlink(resolved_link_target, normalized_member_path)
                        except (OSError, ValueError):
                            return False
                    else:
                        try:
                            if os.path.exists(normalized_member_path) or os.path.islink(normalized_member_path):
                                os.remove(normalized_member_path)
                            source_path = resolved_link_target
                            if link_target.startswith('/') or link_target.startswith('\\'):
                                source_path = os.path.normpath(os.path.join(dest_path, link_target))
                            else:
                                source_path = os.path.normpath(os.path.join(os.path.dirname(normalized_member_path), link_target))
                            os.link(source_path, normalized_member_path)
                        except (OSError, ValueError):
                            return False
                
                elif member.isdir():
                    try:
                        os.makedirs(normalized_member_path, exist_ok=True)
                    except (OSError, ValueError):
                        return False
                
                elif member.isfile():
                    try:
                        os.makedirs(os.path.dirname(normalized_member_path), exist_ok=True)
                    except (OSError, ValueError):
                        return False
                    
                    try:
                        with tf.extractfile(member) as fobj:
                            if fobj is None:
                                return False
                            with open(normalized_member_path, 'wb') as outfile:
                                while True:
                                    chunk = fobj.read(65536)
                                    if not chunk:
                                        break
                                    outfile.write(chunk)
                        os.chmod(normalized_member_path, member.mode)
                    except (OSError, ValueError, TypeError):
                        return False
                
                else:
                    return False
            
            return True
    
    except (tarfile.TarError, OSError, ValueError):
        return False
