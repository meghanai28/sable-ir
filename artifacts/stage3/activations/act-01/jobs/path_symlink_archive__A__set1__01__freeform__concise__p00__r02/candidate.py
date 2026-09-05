import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict security checks.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive should be extracted.
        
    Returns:
        True if extraction completes successfully without violating security constraints.
        False if any validation or extraction fails.
    """
    try:
        # Normalize dest_path to absolute and remove trailing slashes
        dest_path = os.path.abspath(dest_path)
        
        # Security check: Ensure dest_path is within the root directory
        if not dest_path.startswith(os.sep) and dest_path != '.':
            # If it's not an absolute path or is '.', treat as root
            dest_path = os.path.abspath('.')
        
        # Ensure dest_path doesn't escape root
        if not dest_path.startswith(os.sep):
            dest_path = os.path.abspath('.')
            
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members
            members = tar.getnames()
            
            # Validate all members before extraction
            for member in members:
                # Skip directories (ends with /)
                if member.endswith('/'):
                    continue
                
                # Calculate the target path for this member
                member_dir = os.path.dirname(member)
                member_file = os.path.basename(member)
                
                # Construct the full path
                if member_dir:
                    target_path = os.path.join(dest_path, member_dir, member_file)
                else:
                    target_path = os.path.join(dest_path, member_file)
                
                # Resolve the path to check for symlinks or hard links
                # We need to check if the member is a symlink or hard link
                try:
                    # Get the member info
                    info = tar.getmember(member)
                    
                    # Check for symlinks and hard links
                    if info.issym() or info.islnk():
                        # Resolve the target
                        target = info.linkname
                        target_resolved = os.path.normpath(os.path.join(dest_path, target))
                        
                        # Check if the target escapes the destination
                        if not target_resolved.startswith(dest_path) and not target_resolved == dest_path:
                            return False
                        
                        # Additional check: ensure the target doesn't have .. that escapes
                        # This is covered by the above check but being explicit
                        if '..' in target_resolved.split(os.sep):
                            return False
                    
                    # Check if the member is a hard link
                    if info.islnk() and info.linkname:
                        # Similar check for hard links
                        target_resolved = os.path.normpath(os.path.join(dest_path, info.linkname))
                        if not target_resolved.startswith(dest_path) and not target_resolved == dest_path:
                            return False
                    
                    # Check if the member itself would escape the destination
                    # This handles cases where the member name itself has ..
                    member_resolved = os.path.normpath(os.path.join(dest_path, member))
                    if not member_resolved.startswith(dest_path) and not member_resolved == dest_path:
                        return False
                        
                except (tarfile.TarError, ValueError):
                    return False
            
            # If all validations pass, perform the extraction
            for member in members:
                if member.endswith('/'):
                    continue
                
                # Extract the member
                try:
                    tar.extract(member, path=dest_path)
                except (tarfile.TarError, ValueError) as e:
                    return False
            
            return True
            
    except Exception as e:
        return False
