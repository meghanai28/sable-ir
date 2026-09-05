import os
import tarfile
import stat
import shutil
import tempfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination path with strict safety checks.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Normalize and validate dest_path
        # Ensure dest_path is not absolute and resolve it to a canonical form
        dest_path = os.path.realpath(dest_path)
        
        # Check if dest_path is absolute (after realpath it will be if it was)
        # The spec says "Reject absolute dest_path". However, if the user provides
        # a relative path, realpath will resolve it. We must ensure the final
        # resolved path is safe.
        if os.path.isabs(dest_path):
            raise ValueError("Destination path must not be absolute.")
        
        # Resolve the canonical path of the destination directory
        canonical_dest = os.path.realpath(os.path.dirname(dest_path))
        
        # Check for .. segments in the original or resolved path that might escape
        # We verify that the canonical dest matches the intended base
        # Actually, the safest approach per spec: "raise an error if it escapes the resolved dest_path"
        # This implies we should check if the resolved path has .. components that lead outside.
        # Since we took realpath, .. are resolved. We just need to ensure we don't extract outside.
        
        # Let's re-read: "normalize the destination and raise an error if it escapes the resolved dest_path"
        # This likely means: if the user provides "dest/../evil", realpath resolves it to "dest".
        # But if they provide an absolute path, we reject.
        # We assume the user's intent is to extract into 'dest_path' (relative).
        # We compute the canonical version of the destination directory.
        
        # Additional check: ensure the resolved path is within the expected scope if provided relative.
        # But the spec says "reject absolute dest_path".
        # So if dest_path is absolute -> error.
        # If relative, we resolve it.
        
        # Now, validate that no member extraction would escape the canonical_dest.
        # We will perform validation before opening the file.
        
        # Open the tar file in read-only mode to inspect members
        with tarfile.open(tar_path, 'r:*') as tar:
            # Collect all members and validate them
            valid_members = []
            invalid_members = []
            
            for member in tar.getmembers():
                # Skip if it's a symlink or hardlink
                if member.issym() or member.islnk():
                    invalid_members.append(member.name)
                    continue
                
                # Calculate the target path
                target_path = os.path.join(canonical_dest, member.name)
                
                # Normalize the target path to resolve ..
                # We must ensure the normalized path is still within canonical_dest
                normalized_target = os.path.normpath(target_path)
                
                # Check for absolute paths in member name
                if os.path.isabs(member.name):
                    invalid_members.append(member.name)
                    continue
                
                # Check if the normalized target escapes the canonical destination
                # We use os.path.commonpath to check containment safely
                try:
                    common = os.path.commonpath([canonical_dest, normalized_target])
                    if common != canonical_dest:
                        invalid_members.append(member.name)
                        continue
                except ValueError:
                    # If paths are on different drives (Windows) or invalid, it's unsafe
                    invalid_members.append(member.name)
                    continue
                
                valid_members.append(member)
            
            if invalid_members:
                return False
            
            # Now perform the extraction
            with tarfile.open(tar_path, 'r:*') as tar:
                for member in valid_members:
                    target_path = os.path.join(canonical_dest, member.name)
                    
                    # Ensure the directory exists
                    dir_path = os.path.dirname(target_path)
                    if not os.path.exists(dir_path):
                        os.makedirs(dir_path)
                    
                    # Extract the member
                    if member.isdir():
                        tar.extract(member, dir_path)
                    else:
                        tar.extract(member, dir_path)
            
            return True
            
    except Exception:
        return False
