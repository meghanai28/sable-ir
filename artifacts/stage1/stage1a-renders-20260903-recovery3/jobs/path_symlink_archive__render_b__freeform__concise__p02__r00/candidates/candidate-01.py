import os
import tarfile
from typing import Optional


def _normalize_path(path: str) -> str:
    return os.path.normpath(path)


def _is_path_inside(path: str, dest_path: str) -> bool:
    normalized = _normalize_path(path)
    dest_normalized = _normalize_path(dest_path)
    if not normalized.startswith(dest_normalized):
        return False
    if len(normalized) == len(dest_normalized):
        return True
    next_char = normalized[len(dest_normalized)]
    return next_char == os.sep


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.abspath(dest_path)
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            
            for member in members:
                member_name = member.name
                if os.path.isabs(member_name):
                    return False
                
                member_path = os.path.join(dest_path, member_name)
                member_path = os.path.abspath(member_path)
                normalized_member = _normalize_path(member_path)
                
                if not _is_path_inside(normalized_member, dest_path):
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_target = _normalize_path(link_target)
                        if not _is_path_inside(normalized_target, dest_path):
                            return False
                    else:
                        if member.issym():
                            target_base = os.path.dirname(normalized_member)
                        else:
                            target_base = dest_path
                        
                        resolved_target = os.path.join(target_base, link_target)
                        resolved_target = os.path.abspath(resolved_target)
                        normalized_target = _normalize_path(resolved_target)
                        
                        if not _is_path_inside(normalized_target, dest_path):
                            return False
            
            for member in members:
                member_name = member.name
                member_path = os.path.join(dest_path, member_name)
                member_path = os.path.abspath(member_path)
                
                if member.isdir():
                    os.makedirs(member_path, exist_ok=True)
                elif member.isfile():
                    parent_dir = os.path.dirname(member_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    
                    source = tar.extractfile(member)
                    if source is None:
                        return False
                    
                    with open(member_path, 'wb') as f:
                        while True:
                            chunk = source.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                elif member.issym():
                    link_target = member.linkname
                    parent_dir = os.path.dirname(member_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    os.symlink(link_target, member_path)
                elif member.islnk():
                    link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_target = _normalize_path(link_target)
                        if not _is_path_inside(normalized_target, dest_path):
                            return False
                        target_path = normalized_target
                    else:
                        target_base = os.path.dirname(member_path)
                        resolved_target = os.path.join(target_base, link_target)
                        target_path = os.path.abspath(resolved_target)
                    
                    parent_dir = os.path.dirname(member_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    os.link(target_path, member_path)
            
            return True
            
    except (tarfile.TarError, OSError, IOError):
        return False
