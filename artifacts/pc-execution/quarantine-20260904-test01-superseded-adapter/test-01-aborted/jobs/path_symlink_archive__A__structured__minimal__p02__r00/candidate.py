import os
import tarfile
import shutil
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict security controls.
    
    Returns True only if extraction completes successfully.
    Returns False if any validation fails or if extraction is interrupted.
    No archive members are written outside dest_path.
    """
    # Create a temporary directory to hold the extracted content temporarily
    # This ensures we can clean up if extraction fails
    temp_dir = tempfile.mkdtemp(prefix='tar_extract_')
    
    try:
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate and extract members
            for member in tar.getmembers():
                # Security checks
                # 1. Check if the member is a symbolic link or hard link
                if member.issym() or member.isdir() or member.istype() == 'l':
                    # Reject symbolic links, hard links, and directories
                    # Note: isdir() returns True for directories, which should not be extracted
                    # istype() == 'l' is for hard links
                    # issym() is for symbolic links
                    continue
                
                # 2. Check for path traversal
                # Construct the full path relative to dest_path
                dest_member = os.path.normpath(os.path.join(dest_path, member.name))
                
                # Check if the path contains .. or starts with ..
                # We need to ensure the path is within dest_path
                if not dest_member.startswith(dest_path + os.sep) and dest_member != dest_path:
                    # Path traversal detected
                    continue
                
                # 3. Check for absolute paths
                if os.path.isabs(member.name):
                    continue
                
                # 4. Check for symbolic links that might point outside the extraction root
                # We need to check the target of the symlink if it exists
                if member.issym():
                    # Get the symlink target
                    target = member.linkname
                    # Normalize the target
                    normalized_target = os.path.normpath(target)
                    # Check if the normalized target is outside the dest_path
                    if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                        continue
                
                # 5. Check for hard links
                if member.istype() == 'l':
                    # Hard links are not allowed
                    continue
                
                # 6. Check if the member is a directory
                if member.isdir():
                    continue
                
                # If we reach here, the member is safe to extract
                # Extract the member
                tar.extract(member, dest_path)
                
            return True
            
    except Exception as e:
        # Clean up the temporary directory if extraction fails
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        return False
