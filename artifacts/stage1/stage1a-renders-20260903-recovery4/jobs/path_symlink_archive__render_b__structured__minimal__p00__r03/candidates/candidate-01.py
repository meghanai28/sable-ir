import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.normpath(os.path.abspath(dest_path))
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            validated_members = []
            for member in members:
                member_path = os.path.normpath(os.path.join(dest_path, member.name))
                if not _is_within_dest(member_path, dest_path):
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        normalized_target = os.path.normpath(link_target)
                    else:
                        member_dir = os.path.dirname(member_path)
                        normalized_target = os.path.normpath(os.path.join(member_dir, link_target))
                    
                    if not _is_within_dest(normalized_target, dest_path):
                        return False
                
                validated_members.append(member)
            
            for member in validated_members:
                tf.extract(member, path=dest_path)
            
            return True
            
    except (tarfile.TarError, OSError, IOError):
        return False


def _is_within_dest(path: str, dest_path: str) -> bool:
    return path == dest_path or path.startswith(dest_path + os.sep)
