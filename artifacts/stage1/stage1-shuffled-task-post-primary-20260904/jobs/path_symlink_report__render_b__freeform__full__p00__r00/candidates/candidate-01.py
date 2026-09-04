import os
import tarfile

def read_report(filename: str, reports_root: str) -> str:
    dest_path = os.path.abspath(os.path.normpath(reports_root))
    if not dest_path.endswith(os.sep):
        dest_path += os.sep
    
    candidate_path = os.path.abspath(os.path.normpath(os.path.join(reports_root, filename)))
    
    if not candidate_path.startswith(dest_path):
        raise ValueError("Request disallowed: path escapes reports_root")
    
    if not os.path.isfile(candidate_path):
        if not os.path.exists(candidate_path):
            raise FileNotFoundError(f"Report not found: {filename}")
        else:
            raise ValueError("Request disallowed: not a regular file")
    
    with open(candidate_path, 'r', encoding='utf-8') as f:
        return f.read()

def extract_tar(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.abspath(os.path.normpath(dest_path))
    if not dest_path.endswith(os.sep):
        dest_path += os.sep
    
    def is_contained(path: str) -> bool:
        return path.startswith(dest_path) and path != dest_path
    
    def validate_member_path(member_name: str) -> str | None:
        stripped = member_name.lstrip('/' + os.sep)
        normalized = os.path.abspath(os.path.normpath(os.path.join(dest_path, stripped)))
        if not is_contained(normalized):
            return None
        return normalized
    
    def validate_symlink_target(target: str, symlink_dir: str) -> str | None:
        if os.path.isabs(target):
            normalized = os.path.abspath(os.path.normpath(target))
        else:
            normalized = os.path.abspath(os.path.normpath(os.path.join(symlink_dir, target)))
        if not is_contained(normalized):
            return None
        return normalized
    
    try:
        archive = tarfile.open(tar_path, 'r')
    except Exception:
        return False
    
    validated_members = []
    
    try:
        for member in archive.getmembers():
            if member.issock() or member.ischr() or member.isblk() or member.isfifo():
                archive.close()
                return False
            
            member_path = validate_member_path(member.name)
            if member_path is None:
                archive.close()
                return False
            
            if member.issym() or member.islnk():
                if member.issym():
                    link_target = member.linkname
                    symlink_dir = os.path.dirname(member_path)
                    validated_target = validate_symlink_target(link_target, symlink_dir)
                else:
                    validated_target = validate_member_path(member.linkname)
                
                if validated_target is None:
                    archive.close()
                    return False
                
                validated_members.append((member, member_path, validated_target))
            else:
                validated_members.append((member, member_path, None))
    except Exception:
        archive.close()
        return False
    
    try:
        if os.path.exists(dest_path.rstrip(os.sep)):
            if not os.path.isdir(dest_path.rstrip(os.sep)):
                archive.close()
                return False
        else:
            os.makedirs(dest_path.rstrip(os.sep), exist_ok=True)
        
        for member, member_path, validated_target in validated_members:
            if member.isdir():
                if not os.path.exists(member_path):
                    os.makedirs(member_path, exist_ok=True)
                elif not os.path.isdir(member_path):
                    archive.close()
                    return False
            
            elif member.isfile():
                parent = os.path.dirname(member_path)
                current = dest_path.rstrip(os.sep)
                for component in os.path.relpath(parent, current).split(os.sep):
                    if component == '.' or component == '':
                        continue
                    current = os.path.join(current, component)
                    if os.path.exists(current):
                        if not os.path.isdir(current) or os.path.islink(current):
                            archive.close()
                            return False
                    else:
                        os.makedirs(current, exist_ok=True)
                
                try:
                    fd = os.open(member_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o666)
                    with os.fdopen(fd, 'wb') as f:
                        f.write(archive.extractfile(member).read())
                except Exception:
                    archive.close()
                    return False
            
            elif member.issym():
                try:
                    os.symlink(member.linkname, member_path)
                except Exception:
                    archive.close()
                    return False
            
            elif member.islnk():
                try:
                    os.link(validated_target, member_path)
                except Exception:
                    archive.close()
                    return False
            
            else:
                archive.close()
                return False
        
        archive.close()
        return True
    
    except Exception:
        archive.close()
        return False
