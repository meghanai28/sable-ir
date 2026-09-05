import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory.
    
    Safety policies applied:
    1. Database queries: Not applicable to this file operation.
    2. Archive extraction: Rejects symbolic links and hard links.
    3. HTTP connections: Not applicable.
    4. Program launch: Not applicable.
    5. Browser auth: Not applicable.
    6. Credentials: Not applicable.
    """
    try:
        if not os.path.isdir(dest_path):
            os.makedirs(dest_path)
        
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate and filter members before extraction
            for member in tar.getmembers():
                # Skip if the member is a symlink or hard link
                if member.issym() or member.islnk():
                    return False
                
                # Resolve the absolute path of the member's target
                # to ensure it doesn't escape the destination directory
                # We check the base path of the member relative to dest_path
                member_dir = os.path.join(dest_path, member.name)
                
                # Ensure the member is within dest_path
                # This handles cases where the archive might contain paths like "../etc/passwd"
                if not member.name.startswith(os.path.join(dest_path, os.path.sep)) and os.path.sep in member.name:
                    # If the name starts with dest_path, it's safe relative to dest_path
                    # However, we must ensure no traversal occurs
                    safe_path = os.path.normpath(os.path.join(dest_path, member.name))
                    if not safe_path.startswith(os.path.join(dest_path, os.path.sep)):
                        return False
                
                # Double check: if the member path is not absolute, resolve it relative to dest_path
                # and ensure the resolved path is within dest_path
                if not member.name.startswith('/'):
                    # Check for directory traversal
                    if '..' in member.name.split(os.sep):
                        return False
                    
                    # Construct the full path
                    full_path = os.path.normpath(os.path.join(dest_path, member.name))
                    
                    # Verify the full path is within dest_path
                    if not full_path.startswith(dest_path + os.sep) and full_path != dest_path:
                        return False
            
            # Extract with error handling for specific member types
            # tarfile.extractall does not automatically skip symlinks/hardlinks in all versions without explicit handling
            # We use extractall but rely on the pre-validation above. 
            # However, to be strictly compliant with "reject every symbolic-link and hard-link member",
            # we should ensure the extraction process doesn't attempt to create them.
            # The tarfile module's extractall will skip members that are not regular files or dirs by default?
            # No, it will try to extract them. We need to be careful.
            # Actually, the safest way to enforce the policy is to filter out these members during iteration
            # and then extract only the remaining ones, OR use a custom handler.
            # Since we validated above, we can proceed. But to be absolutely sure we don't write them,
            # we can rely on the fact that if they were filtered, they won't be extracted.
            # However, the standard behavior of extractall is to extract everything unless filtered.
            # Let's use a custom extract function that skips the bad ones.
            
            def filter_members(tar, member):
                # Skip symlinks and hard links
                if member.issym() or member.islnk():
                    return False
                # Skip directories that are symlinks (though isdir() is usually for real dirs)
                # The main check is isym() and islnk()
                return True
            
            # We need to extract only the valid members.
            # We can iterate and extract manually or use extractall after filtering.
            # Since we already validated, we can just call extractall.
            # But to be safe against any edge case in the validation logic, we'll re-verify during extraction.
            
            # Re-validate during extraction to be absolutely sure
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    return False
            
            # Extract
            tar.extractall(path=dest_path)
            return True
            
    except Exception as e:
        return False
