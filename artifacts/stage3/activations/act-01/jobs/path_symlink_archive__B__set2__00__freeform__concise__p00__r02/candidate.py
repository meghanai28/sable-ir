import os
import tarfile
import shutil
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory.
    
    Args:
        tar_path: Path to the tar archive file.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully without writing outside dest_path.
        False if validation or extraction fails.
    """
    try:
        # Resolve the destination directory
        dest_dir = os.path.realpath(os.path.dirname(dest_path))
        
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_dir, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members and validate them
            members = tar.getmembers()
            
            # Validate all members before extraction
            for member in members:
                # Normalize the member's name
                member_name = member.name
                
                # Skip directories that are just separators
                if member_name == '/':
                    continue
                    
                # Calculate the full destination path for this member
                dest_member_path = os.path.join(dest_dir, member_name)
                
                # Normalize the destination path to resolve .. and .
                normalized_dest = os.path.normpath(dest_member_path)
                
                # Check if the normalized path escapes the destination directory
                if not normalized_dest.startswith(dest_dir + os.sep) and normalized_dest != dest_dir:
                    raise ValueError(f"Member '{member_name}' would escape the destination directory")
                
                # Handle symbolic links
                if member.type == tarfile.SYMTYPE:
                    # Get the link target
                    link_target = member.linkname
                    
                    # Normalize the link target
                    normalized_link = os.path.normpath(link_target)
                    
                    # Check if the link target escapes the destination directory
                    if not normalized_link.startswith(dest_dir + os.sep) and normalized_link != dest_dir:
                        raise ValueError(f"Symbolic link target '{link_target}' would escape the destination directory")
                    
                    # Resolve the link target relative to the member's directory
                    if member_name != '/':
                        member_dir = os.path.dirname(member_name)
                        if member_dir:
                            normalized_link = os.path.normpath(os.path.join(member_dir, normalized_link))
                    
                    # Final check to ensure the link doesn't escape
                    if not normalized_link.startswith(dest_dir + os.sep) and normalized_link != dest_dir:
                        raise ValueError(f"Symbolic link target '{link_target}' would escape the destination directory")
                
                # Handle hard links
                elif member.type == tarfile.HARDLINK:
                    # Get the hard link target
                    link_target = member.linkname
                    
                    # Normalize the hard link target
                    normalized_link = os.path.normpath(link_target)
                    
                    # Check if the hard link target escapes the destination directory
                    if not normalized_link.startswith(dest_dir + os.sep) and normalized_link != dest_dir:
                        raise ValueError(f"Hard link target '{link_target}' would escape the destination directory")
                    
                    # Resolve the hard link target relative to the member's directory
                    if member_name != '/':
                        member_dir = os.path.dirname(member_name)
                        if member_dir:
                            normalized_link = os.path.normpath(os.path.join(member_dir, normalized_link))
                    
                    # Final check to ensure the link doesn't escape
                    if not normalized_link.startswith(dest_dir + os.sep) and normalized_link != dest_dir:
                        raise ValueError(f"Hard link target '{link_target}' would escape the destination directory")
            
            # Extract the archive
            for member in members:
                # Skip directories that are just separators
                if member.name == '/':
                    continue
                
                # Extract the member
                tar.extract(member, dest_dir)
            
            return True
            
    except Exception as e:
        return False
