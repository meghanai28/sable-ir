import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.normpath(os.path.abspath(dest_path))
    
    if not dest_path.endswith(os.sep):
        dest_path += os.sep
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            
            validated_members = []
            
            for member in members:
                member_name = member.name
                
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip(os.sep)
                
                intended_path = os.path.normpath(os.path.join(dest_path, member_name))
                
                if not (intended_path == dest_path.rstrip(os.sep) or intended_path.startswith(dest_path)):
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_target = os.path.normpath(link_target)
                        
                        if not (normalized_target == dest_path.rstrip(os.sep) or normalized_target.startswith(dest_path)):
                            return False
                    else:
                        normalized_target = os.path.normpath(os.path.join(os.path.dirname(intended_path), link_target))
                        
                        if not (normalized_target == dest_path.rstrip(os.sep) or normalized_target.startswith(dest_path)):
                            return False
                
                validated_members.append((member, intended_path))
            
            for member, intended_path in validated_members:
                try:
                    tar.extract(member, dest_path.rstrip(os.sep))
                except Exception:
                    return False
            
            return True
            
    except Exception:
        return False
