import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.normpath(dest_path))
        
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            
            for member in members:
                member_path = os.path.join(dest_path, member.name)
                member_path = os.path.abspath(os.path.normpath(member_path))
                
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    if member.issym():
                        link_target = member.linkname
                    else:
                        link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_target = os.path.abspath(os.path.normpath(link_target))
                    else:
                        if member.issym():
                            member_dir = os.path.dirname(member_path)
                        else:
                            member_dir = os.path.dirname(member_path)
                        normalized_target = os.path.abspath(os.path.normpath(os.path.join(member_dir, link_target)))
                    
                    if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                        return False
            
            def is_within_dest(member, path):
                member_path = os.path.join(dest_path, member.name)
                member_path = os.path.abspath(os.path.normpath(member_path))
                
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    if member.issym():
                        link_target = member.linkname
                    else:
                        link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_target = os.path.abspath(os.path.normpath(link_target))
                    else:
                        member_dir = os.path.dirname(member_path)
                        normalized_target = os.path.abspath(os.path.normpath(os.path.join(member_dir, link_target)))
                    
                    if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                        return False
                
                return True
            
            for member in members:
                if not is_within_dest(member, dest_path):
                    return False
            
            tar.extractall(path=dest_path)
            
            for member in members:
                member_path = os.path.join(dest_path, member.name)
                member_path = os.path.abspath(os.path.normpath(member_path))
                
                if not member_path.startswith(dest_path + os.sep) and member_path != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    if member.issym():
                        link_target = member.linkname
                    else:
                        link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_target = os.path.abspath(os.path.normpath(link_target))
                    else:
                        member_dir = os.path.dirname(member_path)
                        normalized_target = os.path.abspath(os.path.normpath(os.path.join(member_dir, link_target)))
                    
                    if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                        return False
            
            return True
            
    except (tarfile.TarError, OSError, IOError, ValueError):
        return False
