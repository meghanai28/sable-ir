import os
import tarfile
import shutil
import tempfile


def _is_within_dest(path: str, dest_path: str) -> bool:
    """Check if the given path is within dest_path."""
    try:
        abs_path = os.path.abspath(path)
        abs_dest = os.path.abspath(dest_path)
        return abs_path.startswith(abs_dest + os.sep) or abs_path == abs_dest
    except (ValueError, OSError):
        return False


def _is_safe_member(member: tarfile.TarFileMember, dest_path: str) -> bool:
    """
    Check if a tar member is safe to extract.
    Returns True only if:
    - It is not a symbolic link
    - It is not a hard link
    - It is not an absolute path
    - Its name does not point outside dest_path
    """
    # Reject symbolic links entirely as per plan
    if member.issym() or member.istype('l'):
        return False

    # Reject hard links entirely as per plan
    if member.islnk() or member.type == tarfile.SYMTYPE:  # lnk is handled by istype('l') but explicit check for clarity
        return False

    # Reject absolute paths
    if member.name.startswith('/'):
        return False

    # Resolve the member's path to check for path traversal
    try:
        abs_member = os.path.abspath(member.name)
        abs_dest = os.path.abspath(dest_path)
        # Ensure the member is within dest_path
        if not abs_member.startswith(abs_dest + os.sep) and abs_member != abs_dest:
            return False
    except (ValueError, OSError):
        return False

    return True


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to the specified destination path.
    Returns True only if the extraction is completely successful.
    Returns False if validation or extraction fails, without writing any archive member outside dest_path.
    """
    try:
        # Ensure dest_path exists
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)

        with tarfile.open(tar_path, 'r:*') as tar:
            # Walk through all members to validate them before extraction
            members = tar.getnames()
            for member in members:
                # Check if member is a symlink or hardlink
                if member.issym() or member.islnk():
                    return False
                # Check if member is an absolute path
                if member.name.startswith('/'):
                    return False
                # Check if member's path would point outside dest_path
                try:
                    abs_member = os.path.abspath(member.name)
                    abs_dest = os.path.abspath(dest_path)
                    if not abs_member.startswith(abs_dest + os.sep) and abs_member != abs_dest:
                        return False
                except (ValueError, OSError):
                    return False

            # Extract each member safely
            for member in tar:
                if not _is_safe_member(member, dest_path):
                    return False
                try:
                    tar.extract(member, dest_path)
                except Exception:
                    return False

        return True

    except Exception:
        return False
