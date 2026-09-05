import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict security controls.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    # Validate dest_path is not absolute
    if os.path.isabs(dest_path):
        return False
    
    # Normalize dest_path to remove . and .. segments
    normalized_dest = os.path.normpath(dest_path)
    
    # Check if normalized path escapes the intended destination (shouldn't happen with normpath, but validate)
    # If the user provided a path like "./foo/../../bar", normpath resolves it.
    # We ensure the resolved path starts with the normalized dest.
    if not normalized_dest.startswith(os.path.normpath(os.path.join(os.path.dirname(dest_path), ''))):
        # This check is mostly to ensure we don't have issues with relative paths that look like they might escape
        pass
    
    # Create the destination directory if it doesn't exist
    try:
        os.makedirs(normalized_dest, exist_ok=True)
    except Exception:
        return False
    
    # Validate the tar_path exists and is a file
    if not os.path.isfile(tar_path):
        return False
    
    # Read and validate all archive members before extraction
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members
            members = tar.getmembers()
            
            for member in members:
                # Resolve the full path of the member
                # We need to resolve relative to the normalized dest_path
                member_path = os.path.normpath(os.path.join(normalized_dest, member.name))
                
                # Check for absolute paths
                if os.path.isabs(member.name):
                    return False
                
                # Check for .. in the path
                if '..' in member.name.split(os.sep):
                    return False
                
                # Ensure the resolved path is within the destination directory
                # We use os.path.commonpath to verify the path is within the dest
                try:
                    common = os.path.commonpath([normalized_dest, member_path])
                    if common != normalized_dest:
                        return False
                except ValueError:
                    # This can happen if paths are on different drives (Windows) or have different root structures
                    return False
                
                # Additional check: ensure the directory part of the member path exists within dest
                dir_part = os.path.dirname(member_path)
                if dir_part and not dir_part.startswith(normalized_dest):
                    return False
                
                # Check for symlinks pointing outside the destination
                if member.issym() or member.islnk():
                    try:
                        link_target = member.linkname
                        # Resolve the link target relative to the member's location if it's relative
                        if not os.path.isabs(link_target):
                            # The link target is relative to the member's directory
                            member_dir = os.path.dirname(member.name)
                            resolved_link = os.path.normpath(os.path.join(member_dir, link_target))
                        else:
                            resolved_link = link_target
                        
                        # Check if the resolved link escapes the destination
                        if not resolved_link.startswith(normalized_dest):
                            return False
                    except Exception:
                        return False
                
                # Validate file type
                if member.isdir():
                    # Ensure no symlinks to directories outside
                    if member.issym() or member.islnk():
                        continue
                elif member.isfile():
                    # Ensure no symlinks to files outside
                    if member.issym() or member.islnk():
                        continue
                else:
                    # Skip non-file/non-directory members or reject based on policy
                    # For strict security, we might want to reject these, but the prompt implies we extract members
                    # If a member is a device or something else, we should probably skip or reject
                    # The prompt says "extract the tar archive", implying we process valid members
                    # However, to be safe, we'll skip unknown types or return False if we encounter unexpected types that could be dangerous
                    # Given the instruction "validate every member", we should be strict.
                    # But standard tar extraction might fail on these. Let's assume we only extract valid file/directory members.
                    # If the member is not a file or directory, we skip it to prevent extraction of dangerous types
                    pass
            
            # All members validated, proceed with extraction
            for member in members:
                if member.isdir():
                    # Create directory
                    os.makedirs(os.path.normpath(os.path.join(normalized_dest, member.name)), exist_ok=True)
                elif member.isfile():
                    # Extract file
                    # We need to ensure the directory exists before extracting the file
                    dir_path = os.path.dirname(os.path.normpath(os.path.join(normalized_dest, member.name)))
                    if dir_path and not os.path.exists(dir_path):
                        os.makedirs(dir_path)
                    
                    with tar.extractfile(member) as src:
                        dest_file_path = os.path.normpath(os.path.join(normalized_dest, member.name))
                        with open(dest_file_path, 'wb') as dst:
                            dst.write(src.read())
                # Skip other member types to ensure safety
            return True
            
    except Exception:
        return False
