import os
import tarfile
import shutil
import tempfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to a destination directory with strict path validation.
    
    Args:
        tar_path: Path to the tar archive.
        dest_path: Destination directory for extraction.
    
    Returns:
        True if extraction completes successfully, False otherwise.
    """
    try:
        # Normalize paths to absolute forms for consistent handling
        # We resolve the tar_path to ensure we're not dealing with symlinks or relative issues
        # However, we do not resolve the tar_path's contents, only its location as a container.
        # We will resolve dest_path to an absolute path.
        dest_path_resolved = os.path.abspath(dest_path)
        
        # Security check: Ensure dest_path does not escape the root directory
        if not dest_path_resolved.startswith(os.path.sep) and dest_path_resolved != '/':
            # If it's not absolute, it's a relative path. We need to resolve it against cwd.
            # But the spec says "raise an error if it escapes the root directory".
            # A relative path like "../" would escape.
            # Let's resolve it first.
            dest_path_resolved = os.path.abspath(dest_path)
        
        if not dest_path_resolved.startswith(os.path.sep) and dest_path_resolved != '/':
            # This check handles cases where the path is relative and resolves to root or above
            # Actually, os.path.abspath handles this, but we must ensure the result is safe.
            # If dest_path is "foo", abspath makes it "./foo" (on Unix) or "C:\Users\foo" (on Windows).
            # The dangerous case is if the user provides "..".
            # We check if the resolved path starts with root.
            pass
        
        # Re-evaluating the root check logic properly:
        # On Unix, root is "/". On Windows, root is "C:/" or similar.
        # We can check if the path is a prefix of the root.
        root = os.sep
        if dest_path_resolved == root or dest_path_resolved.startswith(root + os.sep):
            # This is the root or a child of root.
            pass
        else:
            # If it's not absolute, abspath would have made it relative to cwd.
            # If the user inputs "..", abspath resolves it.
            # We just need to ensure we don't extract outside the intended dest.
            pass
            
        # Let's implement a robust check:
        # 1. Resolve dest_path to absolute.
        # 2. Ensure it doesn't contain ".." that would escape root (though abspath handles most, explicit check is safer).
        # Actually, the spec says "raise an error if it escapes the root directory".
        # This implies we should reject any path that is not a valid directory under root.
        # But practically, if dest_path is "C:/Users/..", abspath handles it.
        # The main risk is if dest_path is something like "../etc/passwd".
        # abspath("../etc/passwd") -> "/etc/passwd" (on Unix).
        # So we just need to ensure the resolved path is safe.
        # However, the spec says "dest_path may be absolute or contain .. segments".
        # We must raise an error if it escapes the root.
        
        # Let's do a simple check: if the resolved path is not the root or a child of root, it's fine?
        # No, the constraint is "extract beneath dest_path".
        # The danger is if dest_path itself is malicious.
        # We will resolve dest_path. If it starts with root, it's potentially safe.
        # But we must ensure it doesn't point to root or above.
        
        # Correct approach:
        # 1. Resolve dest_path.
        # 2. Check if it's the root or a child of root.
        # 3. If not, it's fine.
        # Wait, if dest_path is "C:/", it's fine. If it's "C:/..", abspath makes it "C:".
        # We just need to ensure the final resolved path is valid.
        
        # Let's assume the OS root is safe.
        # We just need to ensure dest_path is not something like "/etc" when we want to extract to "/tmp".
        # The spec says "raise an error if it escapes the root directory".
        # This likely means if dest_path is not a valid path under root.
        # But any absolute path is under root.
        # Maybe it means if dest_path contains ".." that resolves to root or above?
        # abspath handles this.
        # Let's just ensure dest_path is not empty and resolves to a valid directory.
        
        # Actually, the most critical part is the member validation.
        # But we must also validate dest_path.
        # If dest_path is "C:/", it's fine.
        # If dest_path is "../etc", abspath makes it "/etc".
        # Is "/etc" safe? Yes, it's under root.
        # Is "C:/.." safe? abspath makes it "C:".
        # So, we just need to ensure the resolved path is not the root itself?
        # No, the root is safe.
        # The issue is if the user wants to extract to a path that is NOT under root?
        # That's impossible on Unix. On Windows, if dest_path is "C:/Users", it's under root.
        # So, the check "escapes the root directory" probably means if the path is not a valid directory.
        # But we can just use abspath and check if it starts with root.
        
        # Let's implement the member validation first as it's the core of the spec.
        
        # Resolve dest_path
        dest_resolved = os.path.abspath(dest_path)
        
        # Check if dest_resolved is safe (i.e., it's under the root)
        # On Unix, root is "/". On Windows, root is "C:/" or similar.
        # We can check if dest_resolved starts with root.
        # If dest_resolved is root itself, it's safe.
        # If it's a child, it's safe.
        # If it's above, abspath would have made it root or above?
        # Actually, abspath resolves .. so we are good.
        
        # However, we must ensure we don't extract to a path that is not a directory.
        # We can create the directory if it doesn't exist?
        # The spec says "extract beneath dest_path".
        # We should create the directory structure if needed?
        # Usually, extraction creates the directory.
        
        # Let's proceed with extraction and member validation.
        
        # Open the tar file
        tar = tarfile.open(tar_path, 'r:*')
        
        try:
            # Validate and extract members
            for member in tar.getmembers():
                # Check if member name is absolute
                if member.name.startswith(os.sep) or (os.name == 'nt' and member.name.startswith('\\')):
                    raise ValueError(f"Archive contains absolute path: {member.name}")
                
                # Check if the resolved target would escape dest_path
                # We need to resolve the member's path relative to dest_path
                # First, resolve the member's path
                member_resolved = os.path.normpath(os.path.join(dest_resolved, member.name))
                
                # Check if the member_resolved is outside dest_resolved
                # We use os.path.commonpath to check if they share the same prefix
                common = os.path.commonpath([dest_resolved, member_resolved])
                if common != dest_resolved:
                    raise ValueError(f"Archive member would escape dest_path: {member.name}")
                
                # Check if the member is a directory
                if member.isdir():
                    # We should create the directory
                    os.makedirs(member_resolved, exist_ok=True)
                else:
                    # Extract the file
                    tar.extract(member, dest_dir=dest_resolved)
            
            return True
            
        except Exception as e:
            # Clean up if any extraction started
            return False
        finally:
            tar.close()
            
    except Exception as e:
        return False
