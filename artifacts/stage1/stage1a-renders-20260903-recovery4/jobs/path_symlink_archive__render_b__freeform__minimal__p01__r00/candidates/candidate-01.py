import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.normpath(dest_path))
        
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            
            for member in members:
                member_name = member.name
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        member_name = '.'
                
                extract_path = os.path.abspath(os.path.normpath(os.path.join(dest_path, member_name)))
                
                if not extract_path.startswith(dest_path + os.sep) and extract_path != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_target = os.path.abspath(os.path.normpath(link_target))
                        if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                            return False
                    else:
                        if member.issym():
                            normalized_target = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(extract_path), link_target)))
                        else:
                            normalized_target = os.path.abspath(os.path.normpath(os.path.join(dest_path, link_target)))
                        
                        if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                            return False
            
            def is_within_dest(member, path):
                member_name = member.name
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        member_name = '.'
                
                extract_path = os.path.abspath(os.path.normpath(os.path.join(dest_path, member_name)))
                
                if not extract_path.startswith(dest_path + os.sep) and extract_path != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_target = os.path.abspath(os.path.normpath(link_target))
                        if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                            return False
                    else:
                        if member.issym():
                            normalized_target = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(extract_path), link_target)))
                        else:
                            normalized_target = os.path.abspath(os.path.normpath(os.path.join(dest_path, link_target)))
                        
                        if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                            return False
                
                return True
            
            for member in members:
                if not is_within_dest(member, dest_path):
                    return False
            
            tar.extractall(path=dest_path)
            
            return True
            
    except (tarfile.TarError, OSError, IOError, ValueError):
        return False
