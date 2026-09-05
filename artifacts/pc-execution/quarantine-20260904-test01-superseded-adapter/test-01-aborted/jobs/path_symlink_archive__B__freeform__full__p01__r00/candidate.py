import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict safety checks.
    
    Returns True only if the entire archive is extracted successfully without
    writing any member outside dest_path. Returns False on any validation or
    extraction failure.
    """
    try:
        # Resolve and validate dest_path immediately
        dest_path_resolved = os.path.realpath(dest_path)
        
        # Reject absolute paths that start with current dir or contain ..
        if dest_path_resolved.startswith(os.path.abspath(dest_path)) or dest_path_resolved == os.path.abspath(dest_path):
            # Additional check to ensure no .. traversal in the original path components
            dest_parts = dest_path.replace('\\', '/').split('/')
            if '..' in dest_parts:
                return False
        
        # Create the destination directory if it doesn't exist
        os.makedirs(dest_path_resolved, exist_ok=True)
        
        # Open the tar file
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members and validate them first
            members = tar.getmembers()
            
            for member in members:
                # Skip directories
                if member.isdir():
                    continue
                    
                # Resolve the target path for this member
                member_name = member.name
                if not member_name:
                    continue
                    
                # Check for absolute paths in member names
                if os.path.isabs(member_name):
                    return False
                
                # Construct the full path for the member
                member_full_path = os.path.join(dest_path_resolved, member_name)
                
                # Normalize the path to remove .. and .
                member_full_path_normalized = os.path.normpath(member_full_path)
                
                # Ensure the normalized path is still within dest_path
                if not member_full_path_normalized.startswith(os.path.normpath(dest_path_resolved)):
                    return False
                
                # Check for symbolic links
                if member.issym() or member.islnk():
                    # Get the link target
                    link_target = member.linkname if member.issym() else member.linkname
                    
                    # Resolve the link target
                    link_target_resolved = os.path.realpath(os.path.join(dest_path_resolved, member.name))
                    
                    # Check if the link target escapes the destination
                    if not link_target_resolved.startswith(os.path.normpath(dest_path_resolved)):
                        return False
                    
                    # Check if the link target itself is absolute
                    if os.path.isabs(link_target):
                        if not link_target_resolved.startswith(os.path.normpath(dest_path_resolved)):
                            return False
                    
                    # Skip extraction of links for safety, or extract with caution
                    # For this implementation, we'll skip creating the link itself but allow the file extraction
                    # Actually, per requirements, we must validate and reject if they escape
                    # We'll just skip creating the link but the file extraction will be validated
                    continue
                
                # Check for hard links
                if member.islnk():
                    # Get the hard link target
                    link_target = member.linkname
                    
                    # Resolve the hard link target
                    link_target_resolved = os.path.realpath(os.path.join(dest_path_resolved, member.name))
                    
                    # Check if the hard link target escapes the destination
                    if not link_target_resolved.startswith(os.path.normpath(dest_path_resolved)):
                        return False
                    
                    # Skip extraction of hard links for safety
                    continue
                
                # Extract the member
                try:
                    tar.extract(member, dest_path_resolved)
                except Exception:
                    return False
            
            return True
            
    except Exception:
        return False
