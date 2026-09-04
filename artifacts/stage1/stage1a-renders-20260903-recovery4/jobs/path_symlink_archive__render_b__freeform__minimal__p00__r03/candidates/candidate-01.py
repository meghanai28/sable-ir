import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        abs_dest = os.path.abspath(os.path.realpath(dest_path))
        
        if not os.path.exists(abs_dest):
            os.makedirs(abs_dest, exist_ok=True)
        
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            
            validated_members = []
            
            for member in members:
                member_name = member.name
                
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        continue
                
                member_name = member_name.replace('..', '__')
                
                extract_path = os.path.abspath(os.path.join(abs_dest, member_name))
                
                if not extract_path.startswith(abs_dest + os.sep) and extract_path != abs_dest:
                    return False
                
                if member.issym() or member.islnk():
                    if member.issym():
                        link_target = member.linkname
                    else:
                        link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        link_target = link_target.lstrip('/')
                        resolved_target = os.path.abspath(os.path.join(abs_dest, link_target))
                    else:
                        member_parent = os.path.dirname(extract_path)
                        resolved_target = os.path.abspath(os.path.join(member_parent, link_target))
                    
                    if not resolved_target.startswith(abs_dest + os.sep) and resolved_target != abs_dest:
                        return False
                
                validated_members.append((member, extract_path))
            
            for member, extract_path in validated_members:
                if member.isdir():
                    os.makedirs(extract_path, exist_ok=True)
                elif member.isfile():
                    parent_dir = os.path.dirname(extract_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
                    with tar.extractfile(member) as f:
                        if f is None:
                            return False
                        with open(extract_path, 'wb') as out:
                            out.write(f.read())
                elif member.issym() or member.islnk():
                    parent_dir = os.path.dirname(extract_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
                    
                    if member.issym():
                        link_target = member.linkname
                        if os.path.isabs(link_target):
                            link_target = link_target.lstrip('/')
                            link_target = os.path.relpath(os.path.join(abs_dest, link_target), parent_dir)
                    else:
                        link_target = member.linkname
                        if os.path.isabs(link_target):
                            link_target = link_target.lstrip('/')
                            link_target = os.path.relpath(os.path.join(abs_dest, link_target), parent_dir)
                    
                    if member.islnk():
                        try:
                            os.link(os.path.join(parent_dir, link_target) if not os.path.isabs(link_target) else link_target, extract_path)
                        except (OSError, FileNotFoundError):
                            return False
                    else:
                        os.symlink(link_target, extract_path)
            
            return True
            
    except (tarfile.TarError, OSError, ValueError, AttributeError):
        return False
