import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to the specified destination path.
    
    Validates that dest_path is safe and that no archive members would escape
    the destination directory. Returns True on complete success, False otherwise.
    """
    # Resolve and normalize the destination path to a canonical absolute path
    try:
        dest_root = os.path.realpath(dest_path)
    except (OSError, ValueError):
        return False

    # If dest_path is a file, ensure the directory exists, but we won't write outside
    # The requirement says "extract beneath dest_path", implying dest_path is the root.
    # We will treat dest_path as the root directory for extraction.

    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            # Validate all members before extracting
            for member in tar.getmembers():
                # Construct the full path for this member relative to dest_root
                # We use member.name which is the path inside the archive
                member_dir = os.path.dirname(member.name)
                member_file = os.path.basename(member.name) if member_file else member.name
                
                # If the member is a directory, we check the last component of its name
                # Actually, we need to check the full path of the member relative to dest_root
                # Let's build the full path and check for escapes
                full_member_path = os.path.join(dest_root, member.name)
                
                # Normalize the full member path to resolve .. and .
                # We must ensure it starts with dest_root
                try:
                    normalized_member_path = os.path.normpath(full_member_path)
                except ValueError:
                    return False
                
                # Check for absolute paths or escape attempts
                if not normalized_member_path.startswith(dest_root + os.sep) and normalized_member_path != dest_root:
                    return False
                
                # Additional check: if the member name contains .. or starts with .., it's suspicious
                # But normpath handles .. resolution. The critical check is the prefix.
                # However, we must also ensure that the member name itself doesn't contain ..
                # which could bypass the check if not normalized properly, though normpath handles it.
                # The spec says "contains .. segments that would escape".
                # We rely on the prefix check after normalization.
                
                # One edge case: if the member name is just ".." or "../foo", normpath will resolve it.
                # We need to ensure that even after normalization, it stays within dest_root.
                # The check `normalized_member_path.startswith(dest_root + os.sep)` handles this.
                # But we must also handle the case where normalized_member_path equals dest_root (empty dir)
                # If the member name is empty or just .., normpath might result in current dir or dest_root.
                # We want to extract into dest_root, so the resulting path should be under dest_root.
                
                # Wait, if member.name is "..", os.path.join(dest_root, "..") becomes ".." or "/".
                # We need to be strict. Let's use os.path.abspath on the joined path and check.
                # Actually, os.path.normpath is sufficient for relative path resolution.
                # The check `normalized_member_path.startswith(dest_root + os.sep)` is correct.
                # But we need to handle the case where normalized_member_path is exactly dest_root.
                # If the member is a directory, its name might be empty? No, member.name is the path.
                # If member.name is "", it's the root of the archive.
                
                # Let's refine:
                # 1. Join dest_root with member.name
                # 2. Normalize the result
                # 3. Check if it starts with dest_root + os.sep OR is equal to dest_root (if it's a directory root)
                # But wait, if member.name is "..", os.path.join(dest_root, "..") might be dest_root or above.
                # We need to ensure the final path is within dest_root.
                
                # Correct logic:
                # target_path = os.path.normpath(os.path.join(dest_root, member.name))
                # if not target_path.startswith(dest_root + os.sep) and target_path != dest_root:
                #     return False
                # But if member.name is "..", target_path might be dest_root or above.
                # If target_path is dest_root, it's okay (extracting to the root itself).
                # If target_path is above, it's not.
                
                # However, we also need to check if the member name itself contains .. that could be tricky.
                # But normpath handles .. resolution.
                
                # Let's do the check:
                target_path = os.path.normpath(os.path.join(dest_root, member.name))
                if not target_path.startswith(dest_root + os.sep) and target_path != dest_root:
                    return False
                
                # Also, we should check if the member name contains .. explicitly before normalization?
                # The spec says "contains .. segments that would escape".
                # If member.name is "a/../b", normpath makes it "b". "b" is safe if "b" is under dest_root.
                # But if member.name is "../a", normpath makes it "a" (relative to current) or above.
                # So the prefix check is the main guard.
                
                # One more thing: if dest_root is a file, we can't extract into it.
                # But the function signature implies dest_path is the destination directory.
                # We assume dest_path is a directory.
                
                pass
            
            # Extract the archive
            # Use getextraction() or extractall()
            # We need to ensure we don't extract outside dest_root.
            # The validation above ensures that.
            
            # Extract all members
            tar.extractall(path=dest_root)
            
            return True

    except (tarfile.TarError, OSError, IOError):
        return False
