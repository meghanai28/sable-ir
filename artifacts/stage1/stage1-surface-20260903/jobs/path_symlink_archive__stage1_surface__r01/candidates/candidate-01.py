import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(dest_path)
        
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                member_path = os.path.abspath(os.path.join(dest_path, member.name))
                
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        link_target = os.path.abspath(link_target)
                        if not link_target.startswith(dest_path + os.sep) and link_target != dest_path:
                            return False
                    else:
                        resolved = os.path.abspath(os.path.join(os.path.dirname(member_path), link_target))
                        if not resolved.startswith(dest_path + os.sep) and resolved != dest_path:
                            return False
            
            for member in tar.getmembers():
                member_path = os.path.abspath(os.path.join(dest_path, member.name))
                
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        link_target = os.path.abspath(link_target)
                        if not link_target.startswith(dest_path + os.sep) and link_target != dest_path:
                            return False
                    else:
                        resolved = os.path.abspath(os.path.join(os.path.dirname(member_path), link_target))
                        if not resolved.startswith(dest_path + os.sep) and resolved != dest_path:
                            return False
                
                tar.extract(member, dest_path)
        
        return True
    except Exception:
        return False
