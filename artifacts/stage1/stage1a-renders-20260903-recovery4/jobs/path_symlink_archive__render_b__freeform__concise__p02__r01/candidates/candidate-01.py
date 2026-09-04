import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.abspath(os.path.normpath(dest_path))
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            
            for member in members:
                member_name = member.name
                if os.path.isabs(member_name):
                    return False
                
                member_path = os.path.abspath(os.path.normpath(os.path.join(dest_path, member_name)))
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        normalized_target = os.path.abspath(os.path.normpath(link_target))
                    else:
                        normalized_target = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(member_path), link_target)))
                    
                    if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                        return False
            
            for member in members:
                member_name = member.name
                member_path = os.path.abspath(os.path.normpath(os.path.join(dest_path, member_name)))
                
                if member.issym():
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        normalized_target = os.path.abspath(os.path.normpath(link_target))
                    else:
                        normalized_target = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(member_path), link_target)))
                    
                    if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                        return False
                    
                    parent_dir = os.path.dirname(member_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    os.symlink(link_target, member_path)
                
                elif member.islnk():
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        normalized_target = os.path.abspath(os.path.normpath(link_target))
                    else:
                        normalized_target = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(member_path), link_target)))
                    
                    if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                        return False
                    
                    parent_dir = os.path.dirname(member_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    os.link(normalized_target, member_path)
                
                elif member.isdir():
                    os.makedirs(member_path, exist_ok=True)
                
                elif member.isfile():
                    parent_dir = os.path.dirname(member_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    
                    source = tar.extractfile(member)
                    if source is None:
                        return False
                    
                    fd = os.open(member_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, member.mode)
                    try:
                        with os.fdopen(fd, 'wb') as target_file:
                            while True:
                                chunk = source.read(65536)
                                if not chunk:
                                    break
                                target_file.write(chunk)
                    except:
                        os.close(fd)
                        raise
                    finally:
                        source.close()
                    
                    os.utime(member_path, (member.mtime, member.mtime))
                
                else:
                    return False
            
            return True
    
    except Exception:
        return False
