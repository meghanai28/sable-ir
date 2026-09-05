import os
import tarfile
import shutil
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict security controls.
    
    This function validates all archive members before extraction to prevent
    directory traversal attacks and symlink/hard-link exploits.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory where the archive will be extracted.
        
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    # Ensure the destination directory exists
    try:
        os.makedirs(dest_path, exist_ok=True)
    except OSError:
        return False
    
    # Create a temporary directory for validation to ensure we don't write outside dest_path
    # during the validation phase. We will perform all checks relative to dest_path.
    temp_dir = tempfile.mkdtemp()
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extracting any part of the archive
            for member in tar.getmembers():
                # Calculate the absolute path of the member relative to the destination
                # tarfile.getmember returns a TarInfo object with name attribute
                member_name = member.name
                
                # Skip if the name is empty (e.g., .tar.gz wrapper)
                if not member_name:
                    continue
                
                # Construct the target path within the destination
                target_path = os.path.join(dest_path, member_name)
                abs_target_path = os.path.abspath(target_path)
                abs_dest_path = os.path.abspath(dest_path)
                
                # Check for directory traversal
                if not abs_target_path.startswith(abs_dest_path):
                    return False
                
                # Check for symbolic links
                if member.issym():
                    return False
                
                # Check for hard links
                if member.ishardlink():
                    return False
                
                # Additional check: ensure the target of a symlink would be within dest_path
                # (though we already reject symlinks entirely per the plan, this is a safeguard)
                # The plan says: "reject every symbolic-link and hard-link member"
                # So we don't need to check the target of the link, just reject the member itself.
                
                # For regular files and directories, we proceed to extraction later
                # But we must ensure that even if we extract, it stays within dest_path
                # The startswith check above handles the traversal prevention.
                
            # All members passed validation
            # Now extract the archive
            for member in tar:
                member_name = member.name
                if not member_name:
                    continue
                    
                target_path = os.path.join(dest_path, member_name)
                abs_target_path = os.path.abspath(target_path)
                
                # Double-check before writing
                if not abs_target_path.startswith(abs_dest_path):
                    return False
                
                if member.isdir():
                    os.makedirs(target_path)
                elif member.isfile():
                    # Extract file content
                    with tar.extractfile(member) as src:
                        with open(target_path, 'wb') as dst:
                            dst.write(src.read())
                else:
                    # Skip other types (directories are handled above, files above)
                    # If there are other types, we might need to handle them or skip
                    # The plan says "regular files and directories may still be extracted"
                    # It implies we should skip others or handle them safely.
                    # Since we rejected symlinks and hardlinks, we only have files, dirs, and possibly others.
                    # We'll skip non-file/non-dir members to be safe, or handle them if needed.
                    # However, standard tar members are file, dir, symlink, hardlink, etc.
                    # We've handled file and dir. Symlink and hardlink are rejected.
                    # What about device files? We'll skip them as they are not regular files/dirs.
                    pass
                    
            return True
            
    except (tarfile.TarError, OSError, IOError):
        return False
    finally:
        # Clean up the temporary directory if it was used (though we didn't use it for extraction logic)
        # Actually, we used temp_dir for nothing in the logic above, but let's clean it up just in case
        try:
            shutil.rmtree(temp_dir)
        except OSError:
            pass
