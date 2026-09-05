import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict path validation.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
        
    Returns:
        True if extraction completes successfully with all members inside dest_path.
        False if validation fails or extraction is interrupted.
    """
    try:
        # Normalize and validate dest_path
        dest_path = os.path.normpath(dest_path)
        
        # Ensure dest_path is within root directory (prevent absolute path escapes)
        real_dest = os.path.realpath(dest_path)
        if not real_dest.startswith(os.path.realpath('/')):
            # On Windows, check if it's a valid drive or absolute path
            if os.name == 'nt':
                # Check if it starts with a drive letter or is absolute
                if not (real_dest.startswith(os.path.sep) or real_dest.startswith('\\\\')):
                    raise ValueError("Destination path must be absolute")
            else:
                if not real_dest.startswith(os.path.sep):
                    raise ValueError("Destination path must be absolute")
        
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar file and iterate through members
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                # Resolve the full path for the member
                member_dir = os.path.dirname(member.name)
                member_file = member.name
                
                # Construct the full path relative to dest_path
                if member_dir:
                    full_member_dir = os.path.normpath(os.path.join(dest_path, member_dir))
                else:
                    full_member_dir = dest_path
                
                # Check if the directory path escapes the destination
                real_member_dir = os.path.realpath(full_member_dir)
                if not real_member_dir.startswith(real_dest):
                    raise ValueError(f"Member directory escapes destination: {member.name}")
                
                # Check if the final file path escapes the destination
                if member_file:
                    full_member_file = os.path.normpath(os.path.join(full_member_dir, member_file))
                    real_member_file = os.path.realpath(full_member_file)
                    if not real_member_file.startswith(real_dest):
                        raise ValueError(f"Member file escapes destination: {member.name}")
                
                # Handle symlinks and hardlinks
                if member.issym():
                    link_target = member.linkname
                    # Resolve the link target
                    if os.path.isabs(link_target):
                        resolved_link = os.path.normpath(os.path.join(dest_path, link_target))
                    else:
                        resolved_link = os.path.normpath(os.path.join(full_member_dir, link_target))
                    
                    real_link = os.path.realpath(resolved_link)
                    if not real_link.startswith(real_dest):
                        raise ValueError(f"Symlink target escapes destination: {member.name} -> {link_target}")
                    
                    # Check if the symlink target is a directory
                    if os.path.isdir(real_link):
                        # Ensure the directory is within dest_path
                        if not real_link.startswith(real_dest):
                            raise ValueError(f"Symlink target directory escapes destination: {member.name} -> {link_target}")
                
                elif member.islnk():
                    link_target = member.linkname
                    # Resolve the link target
                    if os.path.isabs(link_target):
                        resolved_link = os.path.normpath(os.path.join(dest_path, link_target))
                    else:
                        resolved_link = os.path.normpath(os.path.join(full_member_dir, link_target))
                    
                    real_link = os.path.realpath(resolved_link)
                    if not real_link.startswith(real_dest):
                        raise ValueError(f"Hardlink target escapes destination: {member.name} -> {link_target}")
                
                # Extract the member
                tar.extract(member, dest_path)
                
        return True
        
    except Exception as e:
        return False
