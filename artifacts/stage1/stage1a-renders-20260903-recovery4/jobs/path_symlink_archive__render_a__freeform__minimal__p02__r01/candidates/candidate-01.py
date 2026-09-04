import os
import tarfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.normpath(dest_path))
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    return False
                
                member_name = member.name.lstrip('/')
                output_path = os.path.abspath(os.path.normpath(os.path.join(dest_path, member_name)))
                
                if not output_path.startswith(dest_path + os.sep) and output_path != dest_path:
                    return False
                
                if member.isdir():
                    os.makedirs(output_path, exist_ok=True)
                elif member.isfile():
                    parent_dir = os.path.dirname(output_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
                    with tar.extractfile(member) as source:
                        if source is None:
                            return False
                        with open(output_path, 'wb') as target:
                            target.write(source.read())
        return True
    except Exception:
        return False
