import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        abs_dest = os.path.abspath(dest_path)
        abs_dest = os.path.normpath(abs_dest)
        
        # Ensure dest_path exists as a directory or can be created
        if not os.path.exists(abs_dest):
            os.makedirs(abs_dest, exist_ok=True)
        
        if not os.path.isdir(abs_dest):
            return False
        
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf.getmembers():
                # Reject symbolic links and hard links
                if member.issym() or member.islnk():
                    return False
                
                # Only process regular files and directories
                if not (member.isfile() or member.isdir()):
                    return False
                
                # Validate member path containment
                member_path = member.name
                
                # Reject absolute paths
                if os.path.isabs(member_path):
                    return False
                
                # Join and normalize the extracted path
                full_path = os.path.join(abs_dest, member_path)
                full_path = os.path.normpath(full_path)
                
                # Verify strict containment within dest_path
                # Handle case where full_path equals abs_dest (directory member named "")
                if full_path == abs_dest:
                    if not member.isdir():
                        return False
                    continue
                
                # Ensure the normalized path starts with abs_dest + os.sep
                # or is exactly abs_dest for the root directory case
                prefix = abs_dest + os.sep
                if not (full_path == abs_dest or full_path.startswith(prefix)):
                    return False
                
                # Additional check: ensure no .. escapes through symlinks in path components
                # by re-resolving any symlinks in the path prefix
                real_full_path = os.path.realpath(full_path)
                real_abs_dest = os.path.realpath(abs_dest)
                if real_full_path != real_abs_dest and not real_full_path.startswith(real_abs_dest + os.sep):
                    return False
            
            # All members validated, now extract
            for member in tf.getmembers():
                if member.isfile() or member.isdir():
                    member_path = member.name
                    full_path = os.path.join(abs_dest, member_path)
                    full_path = os.path.normpath(full_path)
                    
                    if full_path == abs_dest:
                        continue
                    
                    try:
                        tf.extract(member, abs_dest)
                    except Exception:
                        return False
            
            return True
            
    except Exception:
        return False
