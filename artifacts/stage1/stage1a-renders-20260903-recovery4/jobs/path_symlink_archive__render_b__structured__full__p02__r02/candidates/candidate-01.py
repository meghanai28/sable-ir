import os
import tarfile
import errno

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    safe_dest = os.path.normpath(os.path.abspath(dest_path))
    safe_dest_prefix = safe_dest + os.sep
    
    def is_inside_safe(path: str) -> bool:
        return path == safe_dest or path.startswith(safe_dest_prefix)
    
    def sanitize_member_name(name: str) -> str:
        sanitized = name.lstrip('/\\')
        if os.name == 'nt' or hasattr(os, 'name'):
            if len(sanitized) >= 2 and sanitized[1] == ':':
                if sanitized[0].isalpha():
                    sanitized = sanitized[2:].lstrip('/\\')
        while sanitized.startswith('..'):
            parts = sanitized.split(os.sep)
            if parts[0] == '..':
                sanitized = os.sep.join(parts[1:])
            else:
                break
            sanitized = sanitized.lstrip('/\\')
        return sanitized
    
    try:
        tf = tarfile.open(tar_path, 'r:*')
    except Exception:
        return False
    
    try:
        members = tf.getmembers()
    except Exception:
        tf.close()
        return False
    
    validated_manifest = {}
    symlink_members = {}
    hardlink_members = {}
    regular_members = []
    dir_members = []
    
    for member in members:
        sanitized_name = sanitize_member_name(member.name)
        extract_path = os.path.normpath(os.path.join(safe_dest, sanitized_name))
        
        if not is_inside_safe(extract_path):
            tf.close()
            return False
        
        if member.issym():
            link_target = member.linkname
            parent_dir = os.path.dirname(extract_path)
            resolved_target = os.path.normpath(os.path.join(parent_dir, link_target))
            if not is_inside_safe(resolved_target):
                tf.close()
                return False
            symlink_members[member] = {
                'extract_path': extract_path,
                'link_target': link_target,
                'resolved_target': resolved_target
            }
        elif member.islnk():
            sanitized_link_name = sanitize_member_name(member.linkname)
            target_path = os.path.normpath(os.path.join(safe_dest, sanitized_link_name))
            if not is_inside_safe(target_path):
                tf.close()
                return False
            hardlink_members[member] = {
                'extract_path': extract_path,
                'target_path': target_path
            }
        elif member.isdir():
            dir_members.append({
                'member': member,
                'extract_path': extract_path
            })
        elif member.isfile() or member.isreg():
            regular_members.append({
                'member': member,
                'extract_path': extract_path
            })
        else:
            tf.close()
            return False
    
    for member in hardlink_members:
        target_path = hardlink_members[member]['target_path']
        target_is_symlink = False
        for sym_member, sym_info in symlink_members.items():
            if sym_info['extract_path'] == target_path:
                target_is_symlink = True
                break
        if target_is_symlink:
            tf.close()
            return False
    
    written_paths = set()
    
    def mkdir_nofollow(path: str) -> bool:
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception:
            return False
    
    def write_file_nofollow(member, extract_path: str) -> bool:
        parent = os.path.dirname(extract_path)
        if not mkdir_nofollow(parent):
            return False
        
        try:
            fd = os.open(extract_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o666)
        except OSError as e:
            if e.errno == errno.EEXIST:
                try:
                    fd = os.open(extract_path, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
                except OSError:
                    return False
            else:
                return False
        
        try:
            f = os.fdopen(fd, 'wb')
            with tf.extractfile(member) as src:
                if src is None:
                    f.close()
                    return False
                while True:
                    chunk = src.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            f.close()
            written_paths.add(extract_path)
            return True
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            return False
    
    def create_symlink_nofollow(link_target: str, extract_path: str) -> bool:
        parent = os.path.dirname(extract_path)
        if not mkdir_nofollow(parent):
            return False
        
        try:
            os.symlink(link_target, extract_path)
            return True
        except OSError as e:
            if e.errno == errno.EEXIST:
                try:
                    os.remove(extract_path)
                    os.symlink(link_target, extract_path)
                    return True
                except Exception:
                    return False
            return False
    
    def create_hardlink_nofollow(target_path: str, extract_path: str) -> bool:
        parent = os.path.dirname(extract_path)
        if not mkdir_nofollow(parent):
            return False
        
        try:
            os.link(target_path, extract_path)
            return True
        except OSError as e:
            if e.errno == errno.EEXIST:
                try:
                    os.remove(extract_path)
                    os.link(target_path, extract_path)
                    return True
                except Exception:
                    return False
            return False
    
    for item in dir_members:
        if not mkdir_nofollow(item['extract_path']):
            tf.close()
            return False
    
    for item in regular_members:
        if not write_file_nofollow(item['member'], item['extract_path']):
            tf.close()
            return False
    
    for member, info in symlink_members.items():
        if not create_symlink_nofollow(info['link_target'], info['extract_path']):
            tf.close()
            return False
    
    for member, info in hardlink_members.items():
        target_path = info['target_path']
        if target_path not in written_paths:
            if not os.path.exists(target_path) or os.path.islink(target_path):
                tf.close()
                return False
        
        if not create_hardlink_nofollow(target_path, info['extract_path']):
            tf.close()
            return False
    
    tf.close()
    return True
