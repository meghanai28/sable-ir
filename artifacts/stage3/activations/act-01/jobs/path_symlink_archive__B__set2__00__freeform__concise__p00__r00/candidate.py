import os
import tarfile
import stat
import shutil
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory, validating that no file
    or directory is written outside the destination path. Returns True on success,
    False on any failure or validation error.
    """
    try:
        # Resolve the destination path to an absolute path
        resolved_dest = os.path.realpath(dest_path)
        resolved_dest = os.path.abspath(resolved_dest)

        # Ensure the destination directory exists
        if not os.path.isdir(resolved_dest):
            os.makedirs(resolved_dest, exist_ok=True)

        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get the list of members before extracting
            members = tar.getmembers()

            # Validate all members first
            for member in members:
                if member.isdir():
                    continue
                # Normalize the member's name
                member_name = member.name
                if not member_name.startswith(os.sep):
                    member_name = os.sep + member_name

                # Resolve the full path of the member
                full_member_path = os.path.join(resolved_dest, member_name)
                resolved_member_path = os.path.realpath(full_member_path)

                # Check if the resolved path escapes the destination
                if not resolved_member_path.startswith(resolved_dest + os.sep):
                    if resolved_member_path == resolved_dest:
                        continue
                    return False

                # Check for symbolic links that might escape
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    # Normalize the link target
                    if not link_target.startswith(os.sep):
                        link_target = os.sep + link_target
                    # Resolve the link target relative to the member's location
                    # We need to resolve the link target relative to the member's directory
                    member_dir = os.path.dirname(member.name)
                    if not member_dir.startswith(os.sep):
                        member_dir = os.sep + member_dir
                    link_target_dir = os.path.join(resolved_dest, member_dir)
                    resolved_link_target = os.path.realpath(os.path.join(link_target_dir, link_target))
                    if not resolved_link_target.startswith(resolved_dest + os.sep):
                        if resolved_link_target == resolved_dest:
                            continue
                        return False

            # Extract the archive
            for member in members:
                if member.isdir():
                    # Create the directory
                    dir_path = os.path.join(resolved_dest, member.name)
                    os.makedirs(dir_path, exist_ok=True)
                else:
                    # Extract the file
                    extract_path = os.path.join(resolved_dest, member.name)
                    if member.isdir():
                        continue
                    if member.issym():
                        # Create symbolic link
                        link_path = os.path.join(resolved_dest, member.name)
                        link_target = member.linkname
                        if not link_target.startswith(os.sep):
                            link_target = os.sep + link_target
                        # Resolve the link target relative to the member's location
                        member_dir = os.path.dirname(member.name)
                        if not member_dir.startswith(os.sep):
                            member_dir = os.sep + member_dir
                        link_target_dir = os.path.join(resolved_dest, member_dir)
                        resolved_link_target = os.path.realpath(os.path.join(link_target_dir, link_target))
                        if not resolved_link_target.startswith(resolved_dest + os.sep):
                            if resolved_link_target == resolved_dest:
                                continue
                            return False
                        os.symlink(link_target, link_path)
                    elif member.islnk():
                        # Create hard link
                        link_path = os.path.join(resolved_dest, member.name)
                        link_target = member.linkname
                        if not link_target.startswith(os.sep):
                            link_target = os.sep + link_target
                        # Resolve the link target relative to the member's location
                        member_dir = os.path.dirname(member.name)
                        if not member_dir.startswith(os.sep):
                            member_dir = os.sep + member_dir
                        link_target_dir = os.path.join(resolved_dest, member_dir)
                        resolved_link_target = os.path.realpath(os.path.join(link_target_dir, link_target))
                        if not resolved_link_target.startswith(resolved_dest + os.sep):
                            if resolved_link_target == resolved_dest:
                                continue
                            return False
                        os.link(link_target, link_path)
                    else:
                        # Extract regular file
                        shutil.copyfileobj(member.fileobj, extract_path)
                        os.chmod(extract_path, member.mode)

            return True

    except Exception as e:
        return False
