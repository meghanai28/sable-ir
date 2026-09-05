import os
import tarfile
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security validations.
    
    Validates all archive members and their targets before extraction.
    Rejects symbolic links and hard links.
    Ensures all extracted content remains within dest_path.
    
    Returns True only if extraction completes successfully.
    Returns False if validation or extraction fails, without writing outside dest_path.
    """
    try:
        # Create dest_path if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file in read-only mode
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Check for symbolic links
                if member.issym():
                    raise ValueError(f"Symbolic link detected: {member.name}")
                
                # Check for hard links
                if member.islnk():
                    raise ValueError(f"Hard link detected: {member.name}")
                
                # Calculate the target path for the member
                target_path = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Ensure the target is within dest_path (prevent path traversal)
                # Use os.path.commonpath to verify the path is within dest_path
                common = os.path.commonpath([dest_path, target_path])
                if common != dest_path:
                    raise ValueError(f"Path traversal detected for: {member.name}")
                
                # For directories, check if the directory path exists within dest_path
                # This is a basic check; full validation happens during extraction
                if member.isdir():
                    # Ensure no parent directories of the member exist outside dest_path
                    # This is implicitly handled by the commonpath check above,
                    # but we also ensure the member name doesn't start with ..
                    if member.name.startswith('..') or member.name.startswith('/'):
                        raise ValueError(f"Invalid path structure: {member.name}")
            
            # Now perform the extraction with safety checks
            for member in tar:
                # Double-check before extracting
                target_path = os.path.normpath(os.path.join(dest_path, member.name))
                common = os.path.commonpath([dest_path, target_path])
                if common != dest_path:
                    raise ValueError(f"Path traversal detected during extraction: {member.name}")
                
                # Extract the member
                if member.isdir():
                    member.dirname = target_path
                    tar.extract(member, path=dest_path)
                else:
                    tar.extract(member, path=dest_path)
            
            return True
            
    except Exception as e:
        return False
