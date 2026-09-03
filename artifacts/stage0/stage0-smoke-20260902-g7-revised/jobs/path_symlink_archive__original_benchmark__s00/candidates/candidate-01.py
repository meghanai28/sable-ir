import tarfile
import os


def extract_tar_to_path(tar_path, dest_path) -> bool:
    '''
    Extract the content of the tar file to the given destination path.
    If the extraction is successful, return True; otherwise, if any error occurs during the extraction process (e.g. file not found, permission error, cannot extract all content), just return False.

    Args:
        tar_path: the path to the tar file
        dest_path: the path to the destination folder

    Returns:
        True if the extraction is successful; otherwise, False
    '''
    try:
        # Check if tar file exists
        if not os.path.isfile(tar_path):
            return False
        
        # Create destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open and extract the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Security check: prevent path traversal attacks
            for member in tar.getmembers():
                member_path = os.path.join(dest_path, member.name)
                # Resolve to absolute paths to check for traversal
                abs_dest = os.path.abspath(dest_path)
                abs_member = os.path.abspath(member_path)
                # Check if the member path is within the destination directory
                if not abs_member.startswith(abs_dest + os.sep) and abs_member != abs_dest:
                    return False
            
            tar.extractall(path=dest_path)
        
        return True
        
    except (tarfile.TarError, FileNotFoundError, PermissionError, OSError, IOError):
        return False
    except Exception:
        return False
