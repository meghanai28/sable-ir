import os
import tarfile
import zipfile
import io


def read_report(filename: str, reports_root: str) -> str:
    target_path = os.path.normpath(os.path.join(reports_root, filename))
    
    reports_root_norm = os.path.normpath(os.path.abspath(reports_root))
    target_path = os.path.abspath(target_path)
    
    if not target_path.startswith(reports_root_norm + os.sep) and target_path != reports_root_norm:
        raise ValueError("Request disallowed: path escapes reports_root")
    
    if os.path.islink(target_path) or not os.path.exists(target_path):
        if not os.path.exists(target_path):
            raise FileNotFoundError(f"File not found: {target_path}")
    
    if tarfile.is_tarfile(target_path):
        return _read_from_archive(target_path, reports_root_norm)
    
    if zipfile.is_zipfile(target_path):
        return _read_from_zip(target_path, reports_root_norm)
    
    with open(target_path, 'r', encoding='utf-8') as f:
        return f.read()


def _is_safe_member(member_path: str, dest_dir: str) -> bool:
    member_abs = os.path.abspath(os.path.join(dest_dir, member_path))
    member_abs = os.path.normpath(member_abs)
    dest_dir_norm = os.path.normpath(os.path.abspath(dest_dir))
    return member_abs.startswith(dest_dir_norm + os.sep) or member_abs == dest_dir_norm


def _read_from_archive(archive_path: str, reports_root_norm: str) -> str:
    with tarfile.open(archive_path, 'r:*') as tf:
        for member in tf.getmembers():
            if member.issym() or member.islnk():
                link_target = member.linkname
                if link_target.startswith('/'):
                    resolved = os.path.normpath(link_target)
                else:
                    member_dir = os.path.dirname(member.name)
                    resolved = os.path.normpath(os.path.join(member_dir, link_target))
                if not _is_safe_member(resolved, reports_root_norm):
                    raise ValueError("Request disallowed: unsafe link target in archive")
            elif member.isdev() or not (member.isfile() or member.isdir()):
                raise ValueError("Request disallowed: special device or unsupported entry in archive")
            
            if not _is_safe_member(member.name, reports_root_norm):
                raise ValueError("Request disallowed: unsafe member path in archive")
        
        for member in tf.getmembers():
            if member.isfile():
                f = tf.extractfile(member)
                if f is not None:
                    content = f.read().decode('utf-8')
                    f.close()
                    return content
        
        raise FileNotFoundError("No regular file found in archive")


def _read_from_zip(archive_path: str, reports_root_norm: str) -> str:
    with zipfile.ZipFile(archive_path, 'r') as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            
            name = info.filename
            if name.startswith('/'):
                name = name[1:]
            
            if '..' in name.split('/') or '..' in name.split('\\'):
                parts = name.replace('\\', '/').split('/')
                resolved = []
                for part in parts:
                    if part == '..':
                        if resolved:
                            resolved.pop()
                    elif part and part != '.':
                        resolved.append(part)
                name = '/'.join(resolved)
            
            if not _is_safe_member(name, reports_root_norm):
                raise ValueError("Request disallowed: unsafe member path in archive")
        
        for info in zf.infolist():
            if not info.is_dir():
                with zf.open(info) as f:
                    content = f.read().decode('utf-8')
                    return content
        
        raise FileNotFoundError("No regular file found in archive")
