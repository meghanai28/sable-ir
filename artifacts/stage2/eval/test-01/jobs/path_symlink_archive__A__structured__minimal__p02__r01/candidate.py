import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to the specified destination path.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive should be extracted.
        
    Returns:
        True if extraction completes successfully, False otherwise.
        
    Raises:
        ValueError: If the destination path or any archive member would escape the destination directory.
        FileNotFoundError: If the tar archive file does not exist.
    """
    # Normalize the destination path to an absolute path without resolving symlinks yet
    dest_path = os.path.normpath(dest_path)
    
    # Ensure the destination exists as a directory
    if not os.path.isdir(dest_path):
        raise ValueError(f"Destination path must be a directory: {dest_path}")
    
    # Resolve the absolute path of the destination
    resolved_dest = os.path.abspath(dest_path)
    
    # Open the tar file
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Iterate through all members in the archive
            for member in tar.getmembers():
                # Skip symbolic links and hard links as per the plan
                if member.type == tarfile.SYMTYPE or member.type == tarfile.LINKTYPE:
                    continue
                
                # Resolve the member's path relative to the archive root
                member_dir = os.path.dirname(member.name)
                member_file = os.path.basename(member.name)
                
                # Construct the full path for the member
                if member_dir:
                    full_member_path = os.path.join(resolved_dest, member_dir)
                else:
                    full_member_path = resolved_dest
                
                # Normalize the path to handle .. segments
                full_member_path = os.path.normpath(full_member_path)
                
                # Check if the resolved path escapes the destination directory
                # We use abspath to ensure we have a canonical path for comparison
                # and resolve the directory part to check for .. escapes
                if not full_member_path.startswith(resolved_dest + os.sep) and full_member_path != resolved_dest:
                    raise ValueError(f"Archive member would escape destination: {member.name}")
                
                # Extract the member
                tar.extract(member, dest_path)
                
    except Exception as e:
        raise ValueError(f"Extraction failed: {str(e)}")
    
    return True
