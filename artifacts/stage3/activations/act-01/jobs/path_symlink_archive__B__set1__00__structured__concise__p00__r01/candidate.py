import os
import tarfile
import shutil
import stat


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory, ensuring no files
    are written outside dest_path. Returns True on complete success, False otherwise.
    """
    try:
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        
        # Resolve the absolute path for dest_path
        dest_path_resolved = os.path.abspath(dest_path)
        
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Skip directories to avoid creating them unless necessary, but we must validate all
                # Actually, we need to extract everything, so we process all members
                
                # Resolve the member's destination path
                member_dest = os.path.join(dest_path_resolved, member.name)
                member_dest_resolved = os.path.abspath(member_dest)
                
                # Validate that the member_dest_resolved is within dest_path_resolved
                # We need to handle cases where the path might be a prefix or same
                if not member_dest_resolved.startswith(dest_path_resolved + os.sep) and member_dest_resolved != dest_path_resolved:
                    raise ValueError(f"Member {member.name} would extract outside dest_path")
                
                # Additional check for symbolic links and hard links
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    link_target_resolved = os.path.abspath(link_target)
                    if not link_target_resolved.startswith(dest_path_resolved + os.sep) and link_target_resolved != dest_path_resolved:
                        raise ValueError(f"Symbolic/Hard link target {link_target} would point outside dest_path")
                
                # Extract the member
                tar.extract(member, dest_path_resolved)
        
        return True
    
    except Exception:
        return False
