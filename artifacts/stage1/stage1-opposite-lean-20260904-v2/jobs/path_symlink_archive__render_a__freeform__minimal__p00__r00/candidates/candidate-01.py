import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.abspath(dest_path)
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            validated_members = []
            validated_links = []
            
            for member in members:
                member_name = member.name
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if member_name == '':
                        return False
                
                extraction_path = os.path.join(dest_path, member_name)
                normalized_extraction_path = os.path.normpath(extraction_path)
                
                if not normalized_extraction_path.startswith(dest_path + os.sep) and normalized_extraction_path != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        normalized_link_target = os.path.normpath(link_target)
                        if not normalized_link_target.startswith(dest_path + os.sep) and normalized_link_target != dest_path:
                            return False
                    else:
                        member_parent = os.path.dirname(normalized_extraction_path)
                        resolved_target = os.path.normpath(os.path.join(member_parent, link_target))
                        if not resolved_target.startswith(dest_path + os.sep) and resolved_target != dest_path:
                            return False
                    
                    validated_links.append((member, normalized_extraction_path))
                else:
                    validated_members.append((member, normalized_extraction_path))
            
            for member, extraction_path in validated_members + validated_links:
                parent_dir = os.path.dirname(extraction_path)
                if parent_dir and not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)
            
            for member, extraction_path in validated_members:
                if member.isdir():
                    if not os.path.exists(extraction_path):
                        os.makedirs(extraction_path, exist_ok=True)
                elif member.isfile():
                    with tf.extractfile(member) as f:
                        if f is None:
                            return False
                        with open(extraction_path, 'wb') as out_f:
                            out_f.write(f.read())
                    os.chmod(extraction_path, member.mode)
            
            for member, extraction_path in validated_links:
                if member.issym():
                    os.symlink(member.linkname, extraction_path)
                elif member.islnk():
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        normalized_link_target = os.path.normpath(link_target)
                    else:
                        member_parent = os.path.dirname(extraction_path)
                        normalized_link_target = os.path.normpath(os.path.join(member_parent, link_target))
                    
                    if os.path.exists(normalized_link_target):
                        if os.name == 'nt':
                            if os.path.isdir(normalized_link_target):
                                import ctypes
                                ctypes.windll.kernel32.CreateHardLinkW(extraction_path, normalized_link_target, None)
                            else:
                                import ctypes
                                ctypes.windll.kernel32.CreateHardLinkW(extraction_path, normalized_link_target, None)
                        else:
                            os.link(normalized_link_target, extraction_path)
                    else:
                        return False
            
            return True
            
    except (tarfile.TarError, OSError, IOError, ValueError):
        return False
