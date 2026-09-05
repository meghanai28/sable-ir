import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with security validation.
    
    Returns True only if all members are safely extracted within dest_path.
    Returns False if any member would escape dest_path or if extraction fails.
    No files are written outside dest_path if validation fails.
    """
    # Resolve and normalize the destination path to prevent directory traversal
    dest_path = os.path.realpath(dest_path)
    
    # Ensure dest_path exists as a directory; if not, create it
    if not os.path.isdir(dest_path):
        try:
            os.makedirs(dest_path, exist_ok=True)
        except OSError:
            return False
    
    # Open the tar file for reading
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the list of all members in the archive
            members = tar.getmembers()
            
            # Validate each member before extraction
            for member in members:
                # Check if the member name is absolute
                if member.name.startswith('/'):
                    return False
                
                # Construct the full path where the member would be extracted
                # We use os.path.join to handle the path components
                member_dest = os.path.join(dest_path, member.name)
                
                # Normalize the member destination path
                normalized_member_dest = os.path.normpath(member_dest)
                
                # Ensure the normalized path is still within the destination directory
                # This prevents directory traversal attacks like ../../etc/passwd
                if not normalized_member_dest.startswith(dest_path + os.sep) and normalized_member_dest != dest_path:
                    return False
                
                # Additional check: ensure no .. components would escape after normalization
                # The above check handles most cases, but we also verify the path structure
                parts = normalized_member_dest.split(os.sep)
                # Ensure we don't have any .. that would go above dest_path
                # Since we used normpath, this is mostly covered, but let's be explicit
                if '..' in parts:
                    return False
            
            # If all members are valid, extract them
            for member in members:
                # Extract the member
                tar.extract(member, dest_path)
            
            return True
            
    except (tarfile.TarError, OSError, IOError):
        return False
