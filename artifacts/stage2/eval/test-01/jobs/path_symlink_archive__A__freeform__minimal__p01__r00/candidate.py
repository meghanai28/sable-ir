import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security validation.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Resolve and normalize the destination path
        dest_path_resolved = os.path.realpath(dest_path)
        
        # Ensure the destination directory exists
        os.makedirs(dest_path_resolved, exist_ok=True)
        
        # Open the tar archive
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members and validate them before extraction
            members = tar.getmembers()
            
            for member in members:
                # Check for symbolic links
                if member.issym() or member.islnk():
                    raise ValueError(f"Security violation: Symbolic link or hard link detected: {member.name}")
                
                # Check for hard links pointing outside destination
                if member.linkname:
                    link_path = os.path.join(dest_path_resolved, member.name)
                    if not os.path.isabs(member.linkname):
                        link_path = os.path.normpath(os.path.join(dest_path_resolved, member.name))
                    if os.path.realpath(link_path) != dest_path_resolved:
                        raise ValueError(f"Security violation: Hard link points outside destination: {member.name}")
                
                # Normalize the member path to check for escape attempts
                member_dir = os.path.dirname(member.name)
                if member_dir:
                    member_dir_resolved = os.path.normpath(os.path.join(dest_path_resolved, member_dir))
                    if not member_dir_resolved.startswith(dest_path_resolved):
                        raise ValueError(f"Security violation: Archive member path escapes destination: {member.name}")
                else:
                    if not dest_path_resolved.startswith(os.path.realpath(tar_path)):
                        raise ValueError(f"Security violation: Archive member path escapes destination: {member.name}")
            
            # Perform extraction with strict options
            for member in members:
                if member.isdir():
                    os.makedirs(os.path.join(dest_path_resolved, member.name), exist_ok=True)
                else:
                    if member.isdir():
                        continue
                    dest_path_member = os.path.join(dest_path_resolved, member.name)
                    if not os.path.exists(os.path.dirname(dest_path_member)):
                        os.makedirs(os.path.dirname(dest_path_member), exist_ok=True)
                    tar.extract(member, dest_path_resolved)
            
            return True
            
    except Exception as e:
        return False
