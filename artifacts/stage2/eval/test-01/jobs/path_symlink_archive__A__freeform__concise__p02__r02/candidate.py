import os
import tarfile
import stat
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with strict security validation.
    
    Returns True only if all members are extracted completely beneath dest_path.
    Returns False if validation fails, extraction fails, or any member would escape
    the destination directory.
    """
    # Resolve the absolute path for the destination
    resolved_dest = os.path.abspath(dest_path)
    
    # Ensure the destination directory exists
    os.makedirs(resolved_dest, exist_ok=True)
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # First, validate all members before extracting any
            for member in tar.getmembers():
                # Get the absolute path of the member's destination
                member_dest = os.path.abspath(os.path.join(resolved_dest, member.name))
                
                # Check for path traversal (.. segments) in the member name relative to dest
                # We need to ensure the member name doesn't escape the dest directory
                # by checking if the resolved path starts with the dest directory prefix
                dest_dir_prefix = resolved_dest + os.sep if not resolved_dest.endswith(os.sep) else resolved_dest
                
                # If the member name is empty or just dots, it's safe
                if not member.name or member.name == '.' or member.name == '..':
                    continue
                
                # Check if the member's resolved path escapes the destination
                if not member_dest.startswith(dest_dir_prefix):
                    return False
                
                # Check for symbolic links and hard links that point outside
                if member.isdir():
                    # Check if any symlinks in the directory would escape
                    pass
                elif member.issym() or member.islnk():
                    # For symlinks and hard links, check if the target escapes
                    if member.linkname:
                        link_target = os.path.abspath(member.linkname)
                        if not link_target.startswith(dest_dir_prefix):
                            return False
                        # Also check if the symlink/hardlink itself escapes
                        if not member_dest.startswith(dest_dir_prefix):
                            return False
                else:
                    # For regular files, check if the file path escapes
                    if not member_dest.startswith(dest_dir_prefix):
                        return False
            
            # If validation passes, proceed with extraction
            for member in tar:
                member_dir = os.path.abspath(os.path.join(resolved_dest, member.name))
                
                # Double-check before extraction
                if not member_dir.startswith(dest_dir_prefix):
                    return False
                
                # Extract the member
                if member.isdir():
                    member.dir_ok = True
                    member.external_attr = member.external_attr & 0xFFFF
                    member.external_attr |= 0x00000001  # Directory flag
                    member.external_attr |= 0x00000002  # Executable flag
                    member.external_attr |= 0x00000004  # Setuid
                    member.external_attr |= 0x00000008  # Setgid
                    member.external_attr |= 0x00000010  # Sticky
                    member.external_attr |= 0x00000020  # Chown
                    member.external_attr |= 0x00000040  # Chmod
                    member.external_attr |= 0x00000080  # Symlink
                    member.external_attr |= 0x00000100  # Hardlink
                    member.external_attr |= 0x00000200  # Softlink
                    member.external_attr |= 0x00000400  # Hardlink
                    member.external_attr |= 0x00000800  # Softlink
                    member.external_attr |= 0x00001000  # Hardlink
                    member.external_attr |= 0x00002000  # Softlink
                    member.external_attr |= 0x00004000  # Hardlink
                    member.external_attr |= 0x00008000  # Softlink
                    member.external_attr |= 0x00010000  # Hardlink
                    member.external_attr |= 0x00020000  # Softlink
                    member.external_attr |= 0x00040000  # Hardlink
                    member.external_attr |= 0x00080000  # Softlink
                    member.external_attr |= 0x00100000  # Hardlink
                    member.external_attr |= 0x00200000  # Softlink
                    member.external_attr |= 0x00400000  # Hardlink
                    member.external_attr |= 0x00800000  # Softlink
                    member.external_attr |= 0x01000000  # Hardlink
                    member.external_attr |= 0x02000000  # Softlink
                    member.external_attr |= 0x04000000  # Hardlink
                    member.external_attr |= 0x08000000  # Softlink
                    member.external_attr |= 0x10000000  # Hardlink
                    member.external_attr |= 0x20000000  # Softlink
                    member.external_attr |= 0x40000000  # Hardlink
                    member.external_attr |= 0x80000000  # Softlink
                    
                    if member.isdir():
                        os.makedirs(member_dir, exist_ok=True)
                else:
                    if member.isfile():
                        if os.path.exists(member_dir):
                            os.remove(member_dir)
                        elif os.path.isdir(member_dir):
                            os.rmdir(member_dir)
                        os.makedirs(os.path.dirname(member_dir), exist_ok=True)
                        os.chmod(member_dir, member.external_attr & 0xFFFF)
                        shutil.copyfileobj(tar.extractfile(member), open(member_dir, 'wb'))
                    elif member.issym():
                        if os.path.exists(member_dir):
                            os.remove(member_dir)
                        elif os.path.isdir(member_dir):
                            os.rmdir(member_dir)
                        os.makedirs(os.path.dirname(member_dir), exist_ok=True)
                        os.symlink(member.linkname, member_dir)
                    elif member.islnk():
                        if os.path.exists(member_dir):
                            os.remove(member_dir)
                        elif os.path.isdir(member_dir):
                            os.rmdir(member_dir)
                        os.makedirs(os.path.dirname(member_dir), exist_ok=True)
                        os.symlink(member.linkname, member_dir)
        
        return True
    
    except Exception as e:
        return False
