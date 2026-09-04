import os
import tarfile

def read_report(filename: str, reports_root: str) -> str:
    requested_path = os.path.join(reports_root, filename)
    real_requested_path = os.path.realpath(requested_path)
    real_reports_root = os.path.realpath(reports_root)
    
    if not real_requested_path.startswith(real_reports_root + os.sep) and real_requested_path != real_reports_root:
        raise ValueError("Request disallowed: path escapes reports_root")
    
    if not os.path.exists(real_requested_path):
        raise FileNotFoundError(f"Report not found: {filename}")
    
    if not os.path.isfile(real_requested_path):
        raise ValueError("Request disallowed: not an ordinary file")
    
    with open(real_requested_path, 'r', encoding='utf-8') as f:
        return f.read()

def safe_extract(tar_path: str, dest_path: str) -> bool:
    try:
        real_dest_path = os.path.realpath(os.path.abspath(dest_path))
        
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    return False
                
                member_path = os.path.join(real_dest_path, member.name)
                real_member_path = os.path.realpath(member_path)
                
                if not real_member_path.startswith(real_dest_path + os.sep) and real_member_path != real_dest_path:
                    return False
                
                if member.isfile() or member.isdir():
                    parent_dir = os.path.dirname(real_member_path)
                    if os.path.islink(parent_dir):
                        return False
                    
                    if member.isfile():
                        if os.path.islink(real_member_path):
                            return False
                        tar.extract(member, real_dest_path)
                    elif member.isdir():
                        if os.path.islink(real_member_path):
                            return False
                        tar.extract(member, real_dest_path)
                else:
                    return False
                    
        return True
        
    except Exception:
        return False
