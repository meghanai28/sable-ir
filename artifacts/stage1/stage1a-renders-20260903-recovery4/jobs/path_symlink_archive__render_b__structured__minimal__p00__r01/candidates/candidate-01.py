import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.normpath(os.path.abspath(dest_path))
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            validated_members = []
            for member in members:
                member_path = member.name
                
                if os.path.isabs(member_path):
                    member_path = member_path.lstrip('/')
                    if not member_path:
                        continue
                
                extracted_path = os.path.normpath(os.path.join(dest_path, member_path))
                
                if not extracted_path.startswith(dest_path + os.sep) and extracted_path != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    if member.issym():
                        link_target = member.linkname
                    else:
                        link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_target = os.path.normpath(link_target)
                    else:
                        normalized_target = os.path.normpath(os.path.join(os.path.dirname(extracted_path), link_target))
                    
                    if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                        return False
                
                validated_members.append(member)
            
            for member in validated_members:
                try:
                    tf.extract(member, path=dest_path)
                except (OSError, tarfile.TarError):
                    return False
            
            return True
            
    except (OSError, tarfile.TarError):
        return False
