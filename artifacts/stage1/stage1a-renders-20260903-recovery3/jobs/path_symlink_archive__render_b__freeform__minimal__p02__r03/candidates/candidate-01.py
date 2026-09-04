import os
import tarfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.abspath(os.path.normpath(dest_path))
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            
            validated_members = []
            
            for member in members:
                member_path = member.name
                
                if os.path.isabs(member_path):
                    member_path = member_path.lstrip('/')
                    if os.path.isabs(member_path):
                        member_path = member_path[1:]
                
                full_path = os.path.join(dest_path, member_path)
                normalized_path = os.path.abspath(os.path.normpath(full_path))
                
                if not normalized_path.startswith(dest_path + os.sep) and normalized_path != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    if member.issym():
                        link_target = member.linkname
                    else:
                        link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_target = os.path.abspath(os.path.normpath(link_target))
                        if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                            return False
                    else:
                        target_dir = os.path.dirname(normalized_path)
                        full_target = os.path.join(target_dir, link_target)
                        normalized_target = os.path.abspath(os.path.normpath(full_target))
                        if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                            return False
                
                validated_members.append(member)
            
            for member in validated_members:
                member_path = member.name
                
                if os.path.isabs(member_path):
                    member_path = member_path.lstrip('/')
                    if os.path.isabs(member_path):
                        member_path = member_path[1:]
                
                full_path = os.path.join(dest_path, member_path)
                normalized_path = os.path.abspath(os.path.normpath(full_path))
                
                if member.issym() or member.islnk():
                    if member.issym():
                        link_target = member.linkname
                    else:
                        link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_target = os.path.abspath(os.path.normpath(link_target))
                    else:
                        target_dir = os.path.dirname(normalized_path)
                        full_target = os.path.join(target_dir, link_target)
                        normalized_target = os.path.abspath(os.path.normpath(full_target))
                    
                    if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                        return False
                    
                    if member.islnk() and not os.path.exists(normalized_target):
                        pass
                
                tar.extract(member, dest_path)
            
            return True
            
    except (tarfile.TarError, OSError, IOError):
        return False
