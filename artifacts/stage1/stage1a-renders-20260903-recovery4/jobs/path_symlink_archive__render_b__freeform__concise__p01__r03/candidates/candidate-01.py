import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.normpath(os.path.abspath(dest_path))
        if not os.path.isdir(dest_path):
            return False
        
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            
            validated_paths = {}
            link_targets = {}
            hard_link_targets = {}
            
            for member in members:
                member_name = member.name
                
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        return False
                
                if '..' in member_name.split(os.sep) or member_name.startswith('..'):
                    parts = member_name.split(os.sep)
                    normalized_parts = []
                    for part in parts:
                        if part == '..':
                            if normalized_parts:
                                normalized_parts.pop()
                            else:
                                return False
                        elif part and part != '.':
                            normalized_parts.append(part)
                    member_name = os.sep.join(normalized_parts)
                
                abs_extract_path = os.path.normpath(os.path.join(dest_path, member_name))
                
                if abs_extract_path == dest_path:
                    if member.issym() or member.islnk() or member.isfile() or member.isdir() or member.ischr() or member.isblk() or member.isfifo():
                        if not member.isdir():
                            return False
                    abs_extract_path = dest_path
                else:
                    if not (abs_extract_path == dest_path or abs_extract_path.startswith(dest_path + os.sep)):
                        return False
                
                validated_paths[member] = abs_extract_path
                
                if member.issym():
                    link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        link_target = link_target.lstrip('/')
                        if not link_target:
                            return False
                        abs_link_target = os.path.normpath(os.path.join(dest_path, link_target))
                    else:
                        member_dir = os.path.dirname(abs_extract_path)
                        abs_link_target = os.path.normpath(os.path.join(member_dir, link_target))
                    
                    if '..' in member.linkname.split(os.sep) or member.linkname.startswith('..'):
                        parts = member.linkname.split(os.sep)
                        normalized_parts = []
                        for part in parts:
                            if part == '..':
                                if normalized_parts:
                                    normalized_parts.pop()
                                else:
                                    return False
                            elif part and part != '.':
                                normalized_parts.append(part)
                        rel_target = os.sep.join(normalized_parts)
                        if os.path.isabs(member.linkname):
                            abs_link_target = os.path.normpath(os.path.join(dest_path, rel_target))
                        else:
                            member_dir = os.path.dirname(abs_extract_path)
                            abs_link_target = os.path.normpath(os.path.join(member_dir, rel_target))
                    
                    if abs_link_target == dest_path:
                        pass
                    elif not (abs_link_target == dest_path or abs_link_target.startswith(dest_path + os.sep)):
                        return False
                    
                    link_targets[member] = abs_link_target
                
                elif member.islnk():
                    link_target_name = member.linkname
                    
                    if os.path.isabs(link_target_name):
                        link_target_name = link_target_name.lstrip('/')
                        if not link_target_name:
                            return False
                    
                    target_member_name = link_target_name
                    if '..' in target_member_name.split(os.sep) or target_member_name.startswith('..'):
                        parts = target_member_name.split(os.sep)
                        normalized_parts = []
                        for part in parts:
                            if part == '..':
                                if normalized_parts:
                                    normalized_parts.pop()
                                else:
                                    return False
                            elif part and part != '.':
                                normalized_parts.append(part)
                        target_member_name = os.sep.join(normalized_parts)
                    
                    found_target = False
                    for m in members:
                        if m.name == link_target_name or m.name == target_member_name:
                            if m in validated_paths:
                                target_path = validated_paths[m]
                                if target_path == dest_path:
                                    if not m.isdir():
                                        return False
                                elif not (target_path == dest_path or target_path.startswith(dest_path + os.sep)):
                                    return False
                                hard_link_targets[member] = target_path
                                found_target = True
                                break
                    
                    if not found_target:
                        if os.path.isabs(member.linkname):
                            candidate = os.path.normpath(os.path.join(dest_path, member.linkname.lstrip('/')))
                        else:
                            candidate = os.path.normpath(os.path.join(dest_path, member.linkname))
                        
                        if '..' in member.linkname.split(os.sep) or member.linkname.startswith('..'):
                            parts = member.linkname.split(os.sep)
                            normalized_parts = []
                            for part in parts:
                                if part == '..':
                                    if normalized_parts:
                                        normalized_parts.pop()
                                    else:
                                        return False
                                elif part and part != '.':
                                    normalized_parts.append(part)
                            rel_target = os.sep.join(normalized_parts)
                            if os.path.isabs(member.linkname):
                                candidate = os.path.normpath(os.path.join(dest_path, rel_target))
                            else:
                                candidate = os.path.normpath(os.path.join(dest_path, rel_target))
                        
                        if candidate == dest_path:
                            pass
                        elif not (candidate == dest_path or candidate.startswith(dest_path + os.sep)):
                            return False
                        hard_link_targets[member] = candidate
            
            for member in members:
                abs_path = validated_paths[member]
                
                if member.issym():
                    target = link_targets[member]
                    if target == dest_path:
                        pass
                    elif not (target == dest_path or target.startswith(dest_path + os.sep)):
                        return False
                
                elif member.islnk():
                    target = hard_link_targets[member]
                    if target == dest_path:
                        pass
                    elif not (target == dest_path or target.startswith(dest_path + os.sep)):
                        return False
                
                elif member.isdir():
                    pass
                
                elif member.isfile() or member.ischr() or member.isblk() or member.isfifo():
                    parent_dir = os.path.dirname(abs_path)
                    if not (parent_dir == dest_path or parent_dir.startswith(dest_path + os.sep)):
                        return False
            
            for member in members:
                abs_path = validated_paths[member]
                
                if member.issym():
                    target = link_targets[member]
                    if target == dest_path:
                        target = dest_path
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    if os.path.exists(abs_path) or os.path.islink(abs_path):
                        os.remove(abs_path)
                    os.symlink(target, abs_path)
                
                elif member.islnk():
                    target = hard_link_targets[member]
                    if target == dest_path:
                        target = dest_path
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    if os.path.exists(abs_path) or os.path.islink(abs_path):
                        os.remove(abs_path)
                    os.link(target, abs_path)
                
                elif member.isdir():
                    os.makedirs(abs_path, exist_ok=True)
                
                else:
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    with tar.extractfile(member) as f:
                        if f is not None:
                            with open(abs_path, 'wb') as out:
                                while True:
                                    chunk = f.read(8192)
                                    if not chunk:
                                        break
                                    out.write(chunk)
            
            return True
    
    except Exception:
        return False
