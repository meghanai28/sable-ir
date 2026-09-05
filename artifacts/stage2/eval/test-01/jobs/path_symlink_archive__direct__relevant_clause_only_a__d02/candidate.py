import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path, rejecting any symbolic or hard links.
    Returns True on complete success, False otherwise.
    """
    if not os.path.exists(tar_path):
        return False
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get all members
            members = tar.getmembers()
            
            # Validate members for links and check paths
            for member in members:
                # Skip if it's a link (symbolic or hard)
                if member.type == tarfile.SYMTYPE or member.type == tarfile.LINKTYPE:
                    return False
                
                # Check if the member is a directory
                if member.isdir():
                    continue
                
                # For regular files, check if the path is outside dest_path
                # We need to resolve the path relative to the archive's root
                # tarfile.getmember() returns a TarInfo where name is the path
                member_name = member.name
                
                # Check if the member name starts with a path separator or is absolute
                if os.path.sep in member_name or member_name.startswith(os.path.sep):
                    return False
                
                # Construct the full path in dest_path
                dest_member_path = os.path.join(dest_path, member_name)
                
                # Ensure the destination directory exists
                dest_dir = os.path.dirname(dest_member_path)
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                
                # Extract the member
                tar.extract(member, dest_path)
            
            return True
            
    except Exception:
        return False
