import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        abs_dest = os.path.normpath(os.path.abspath(dest_path))
        if not os.path.exists(abs_dest):
            os.makedirs(abs_dest, exist_ok=True)
        
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            
            validated_paths = {}
            validated_targets = {}
            
            for member in members:
                member_name = member.name
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        continue
                
                abs_member_path = os.path.normpath(os.path.join(abs_dest, member_name))
                
                if abs_member_path == abs_dest or not _is_strictly_inside(abs_member_path, abs_dest):
                    return False
                
                validated_paths[member] = abs_member_path
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    
                    if member.issym():
                        if os.path.isabs(link_target):
                            abs_link_target = os.path.normpath(link_target)
                        else:
                            member_dir = os.path.dirname(abs_member_path)
                            abs_link_target = os.path.normpath(os.path.join(member_dir, link_target))
                    else:
                        if os.path.isabs(link_target):
                            link_target = link_target.lstrip('/')
                        abs_link_target = os.path.normpath(os.path.join(abs_dest, link_target))
                    
                    if abs_link_target == abs_dest or not _is_strictly_inside(abs_link_target, abs_dest):
                        return False
                    
                    validated_targets[member] = abs_link_target
            
            for member in members:
                if member not in validated_paths:
                    continue
                
                abs_member_path = validated_paths[member]
                member_dir = os.path.dirname(abs_member_path)
                
                if member.isdir():
                    os.makedirs(abs_member_path, exist_ok=True)
                    mode = member.mode
                    if mode:
                        os.chmod(abs_member_path, mode)
                elif member.isfile():
                    os.makedirs(member_dir, exist_ok=True)
                    with tar.extractfile(member) as f:
                        if f is None:
                            return False
                        data = f.read()
                    with open(abs_member_path, 'wb') as out:
                        out.write(data)
                    mode = member.mode
                    if mode:
                        os.chmod(abs_member_path, mode)
                elif member.issym():
                    os.makedirs(member_dir, exist_ok=True)
                    target = member.linkname
                    if os.path.exists(abs_member_path) or os.path.islink(abs_member_path):
                        os.remove(abs_member_path)
                    os.symlink(target, abs_member_path)
                elif member.islnk():
                    os.makedirs(member_dir, exist_ok=True)
                    abs_link_target = validated_targets[member]
                    if os.path.exists(abs_member_path) or os.path.islink(abs_member_path):
                        os.remove(abs_member_path)
                    os.link(abs_link_target, abs_member_path)
                elif member.ischr() or member.isblk() or member.isfifo() or member.isdev():
                    os.makedirs(member_dir, exist_ok=True)
                    mode = member.mode
                    if member.ischr() or member.isblk():
                        os.mknod(abs_member_path, mode, os.makedev(member.devmajor, member.devminor))
                    elif member.isfifo():
                        os.mkfifo(abs_member_path, mode)
                    else:
                        continue
                    if mode:
                        os.chmod(abs_member_path, mode)
            
            return True
            
    except Exception:
        return False

def _is_strictly_inside(path: str, dest: str) -> bool:
    path_with_sep = path + os.sep
    dest_with_sep = dest + os.sep
    return path_with_sep.startswith(dest_with_sep)
