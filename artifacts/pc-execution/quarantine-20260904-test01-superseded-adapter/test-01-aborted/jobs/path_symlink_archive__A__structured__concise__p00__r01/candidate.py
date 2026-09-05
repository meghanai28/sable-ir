import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path, rejecting any symbolic or hard links.
    Returns True only if all members pass validation and extraction succeeds.
    """
    try:
        # Ensure dest_path exists and is a directory
        if not os.path.isdir(dest_path):
            os.makedirs(dest_path, exist_ok=True)

        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Reject symbolic links and hard links
                if member.issym() or member.islnk():
                    return False
                
                # Resolve the full path to check for directory traversal
                # Use member.name which is the path relative to the archive root
                # We need to check if the resolved path escapes dest_path
                # Construct the intended destination path for this member
                dest_member_path = os.path.join(dest_path, member.name)
                
                # Normalize the path to resolve .. and .
                # We must ensure the normalized path is still within dest_path
                # Use os.path.normpath to handle .. components
                normalized_dest = os.path.normpath(dest_member_path)
                
                # Ensure the normalized path is under dest_path
                # This handles cases like ../../../etc/passwd
                if not normalized_dest.startswith(os.path.normpath(dest_path) + os.sep) and normalized_dest != os.path.normpath(dest_path):
                    return False
                
                # Additional check: ensure no path components outside dest_path after normalization
                # by verifying the relative path from dest_path is empty or starts with it
                if not normalized_dest.startswith(dest_path):
                    return False

            # Extract members one by one to avoid partial writes if validation fails mid-stream
            # But since we validated all members above, we can proceed safely
            for member in tar:
                # Extract the member
                member.extract(dest_path)
            
            return True

    except Exception:
        return False
