import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.normpath(dest_path))
        
        if not os.path.exists(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            
            validated_members = []
            
            for member in members:
                member_dest = _get_normalized_member_path(dest_path, member.name)
                if member_dest is None:
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_target = os.path.normpath(link_target)
                    else:
                        if member.issym():
                            member_dir = os.path.dirname(member_dest)
                            normalized_target = os.path.normpath(os.path.join(member_dir, link_target))
                        else:
                            normalized_target = os.path.normpath(os.path.join(dest_path, link_target))
                    
                    if not _is_within_dest(dest_path, normalized_target):
                        return False
                
                validated_members.append(member)
            
            for member in validated_members:
                member_dest = _get_normalized_member_path(dest_path, member.name)
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_target = os.path.normpath(link_target)
                    else:
                        if member.issym():
                            member_dir = os.path.dirname(member_dest)
                            normalized_target = os.path.normpath(os.path.join(member_dir, link_target))
                        else:
                            normalized_target = os.path.normpath(os.path.join(dest_path, link_target))
                    
                    if not _is_within_dest(dest_path, normalized_target):
                        return False
                
                tar.extract(member, path=dest_path)
            
            return True
    
    except (tarfile.TarError, OSError, IOError):
        return False


def _get_normalized_member_path(dest_path: str, member_name: str) -> str:
    if os.path.isabs(member_name):
        return None
    
    member_name = member_name.replace('/', os.sep)
    
    full_path = os.path.join(dest_path, member_name)
    normalized = os.path.normpath(full_path)
    
    if _is_within_dest(dest_path, normalized):
        return normalized
    return None


def _is_within_dest(dest_path: str, path: str) -> bool:
    try:
        real_dest = os.path.realpath(dest_path)
        real_path = os.path.realpath(path)
        
        return real_path == real_dest or real_path.startswith(real_dest + os.sep)
    except (OSError, ValueError):
        return False
