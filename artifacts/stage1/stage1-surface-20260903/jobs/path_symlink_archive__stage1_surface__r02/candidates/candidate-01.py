import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.realpath(dest_path))
        if not os.path.isdir(dest_path):
            return False
        
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            for member in members:
                member_path = member.name
                
                if os.path.isabs(member_path):
                    return False
                
                parts = member_path.replace('\\', '/').split('/')
                for part in parts:
                    if part == '..' or part == '':
                        if part == '' and member_path.startswith('/'):
                            return False
                        elif part == '..':
                            return False
                
                extracted_path = os.path.join(dest_path, member_path)
                extracted_path = os.path.abspath(os.path.realpath(extracted_path))
                
                if not extracted_path.startswith(dest_path + os.sep) and extracted_path != dest_path:
                    return False
            
            for member in members:
                member_path = member.name
                extracted_path = os.path.join(dest_path, member_path)
                extracted_path = os.path.abspath(os.path.realpath(extracted_path))
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        return False
                    
                    link_target_path = os.path.join(os.path.dirname(extracted_path), link_target)
                    link_target_path = os.path.abspath(os.path.realpath(link_target_path))
                    
                    if not link_target_path.startswith(dest_path + os.sep) and link_target_path != dest_path:
                        return False
            
            for member in members:
                tf.extract(member, path=dest_path)
            
            return True
            
    except (tarfile.TarError, OSError, IOError):
        return False
