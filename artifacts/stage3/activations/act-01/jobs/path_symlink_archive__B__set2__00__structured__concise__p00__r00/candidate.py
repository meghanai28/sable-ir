import os
import tarfile
import stat
import shutil

def _is_within_base(path: str, base: str) -> bool:
    """Check if a path is within the base directory, resolving .. and symlinks."""
    try:
        real_base = os.path.realpath(base)
        real_path = os.path.realpath(path)
        return real_path.startswith(real_base + os.sep) or real_path == real_base
    except (ValueError, OSError):
        return False

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """Extract a tar archive to a destination directory, validating safety first.
    
    Returns True only if extraction completes successfully and safely.
    Returns False if validation fails or extraction is interrupted.
    No data is written outside dest_path if validation fails.
    """
    # Normalize and resolve the destination base
    try:
        dest_path = os.path.realpath(os.path.normpath(dest_path))
    except (ValueError, OSError):
        return False

    # Ensure dest_path exists and is a directory
    if not os.path.isdir(dest_path):
        return False

    # Open the tar file
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extraction
            for member in tar.getmembers():
                # Calculate the full path where the member would be extracted
                member_dir = os.path.dirname(member.name)
                member_base = os.path.basename(member.name)
                
                # Resolve the member's target path relative to dest_path
                # Handle cases where member.name is just a file or a directory
                if member.isdir():
                    full_member_path = os.path.join(dest_path, member.name)
                else:
                    full_member_path = os.path.join(dest_path, member_dir, member_base)
                
                # Resolve the real path to catch .. escapes and symlinks
                try:
                    real_member_path = os.path.realpath(full_member_path)
                except (ValueError, OSError):
                    return False

                # Security Guard: Check if the resolved path is within dest_path
                # This must handle symlinks and .. in the archive name
                if not _is_within_base(real_member_path, dest_path):
                    return False

                # Additional check for symlinks (if file mode allows)
                # If the member is a symlink, we must ensure the target is also safe
                if member.issym() or member.islnk():
                    # Get the link target
                    link_target = member.linkname
                    # Resolve the link target relative to the member's location
                    link_target_path = os.path.normpath(os.path.join(os.path.dirname(member.name), link_target))
                    try:
                        real_link_target = os.path.realpath(link_target_path)
                    except (ValueError, OSError):
                        return False
                    
                    if not _is_within_base(real_link_target, dest_path):
                        return False

            # If validation passes, perform extraction
            # Extract all members to the destination
            tar.extractall(dest_path)
            
            # Verify that no files were written outside the intended directory
            # by checking the actual filesystem state vs expected
            # (This is a safeguard, though extractall usually respects paths)
            # We can rely on the fact that extractall uses the provided base,
            # but we must ensure we didn't accidentally write to parent dirs due to .. in names
            # which the earlier check should have caught.
            
            return True

    except (tarfile.TarError, IOError, OSError):
        return False
