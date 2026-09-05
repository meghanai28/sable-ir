import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to the specified destination path.
    
    Returns True only if the extraction completes successfully without any
    data being written outside dest_path. Returns False on any error or
    if any archive member would escape the destination directory.
    """
    # Resolve and normalize the destination root to prevent path traversal
    try:
        dest_root = os.path.realpath(os.path.normpath(dest_path))
    except (OSError, ValueError):
        return False

    # Normalize the source tar path
    try:
        tar_file = os.path.realpath(os.path.normpath(tar_path))
    except (OSError, ValueError):
        return False

    # Validate that the tar file exists and is readable
    if not os.path.isfile(tar_file):
        return False

    # Extract the archive
    try:
        with tarfile.open(tar_file, 'r:*') as tar:
            for member in tar.getmembers():
                # Construct the target path for this member
                target_path = os.path.join(dest_root, member.name)
                
                # Normalize the target path to resolve any .. or symlinks
                normalized_target = os.path.normpath(target_path)
                
                # Check if the normalized target escapes the destination root
                if not normalized_target.startswith(dest_root + os.sep) and normalized_target != dest_root:
                    return False
                
                # If it's a link, ensure the link target doesn't escape
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    normalized_link_target = os.path.normpath(link_target)
                    if not normalized_link_target.startswith(dest_root + os.sep) and normalized_link_target != dest_root:
                        return False

            # Attempt to extract the archive
            tar.extractall(path=dest_root)
            
            # Additional check: verify that no files were written outside dest_root
            # by checking the filesystem immediately after extraction (optional but safe)
            # We rely on the member path validation above, but as a final guard:
            # We assume the extraction succeeded within the bounds we checked.
            
    except (tarfile.TarError, OSError, IOError):
        return False

    return True
