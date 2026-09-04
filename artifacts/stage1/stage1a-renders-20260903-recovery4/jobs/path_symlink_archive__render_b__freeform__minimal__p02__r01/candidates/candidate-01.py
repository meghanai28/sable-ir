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
                member_dest = os.path.join(dest_path, member.name)
                normalized_member_dest = os.path.abspath(os.path.normpath(member_dest))
                
                if not normalized_member_dest.startswith(dest_path + os.sep) and normalized_member_dest != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    if member.issym():
                        link_target = member.linkname
                    else:
                        link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_link_target = os.path.abspath(os.path.normpath(link_target))
                    else:
                        link_target_dir = os.path.dirname(normalized_member_dest)
                        normalized_link_target = os.path.abspath(os.path.normpath(os.path.join(link_target_dir, link_target)))
                    
                    if not normalized_link_target.startswith(dest_path + os.sep) and normalized_link_target != dest_path:
                        return False
                
                validated_members.append(member)
            
            for member in validated_members:
                member_dest = os.path.join(dest_path, member.name)
                normalized_member_dest = os.path.abspath(os.path.normpath(member_dest))
                
                if not normalized_member_dest.startswith(dest_path + os.sep) and normalized_member_dest != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    if member.issym():
                        link_target = member.linkname
                    else:
                        link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_link_target = os.path.abspath(os.path.normpath(link_target))
                    else:
                        link_target_dir = os.path.dirname(normalized_member_dest)
                        normalized_link_target = os.path.abspath(os.path.normpath(os.path.join(link_target_dir, link_target)))
                    
                    if not normalized_link_target.startswith(dest_path + os.sep) and normalized_link_target != dest_path:
                        return False
            
            for member in validated_members:
                tar.extract(member, path=dest_path)
            
            return True
            
    except (tarfile.TarError, OSError, IOError):
        return False
