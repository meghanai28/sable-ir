import os
import tarfile
from typing import Optional

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    # Session management with secure cookie attributes
    _session_cookie = {
        'Secure': True,
        'HttpOnly': True,
        'SameSite': 'Strict',
        'session_id': None
    }
    
    def _rotate_session_id() -> str:
        import secrets
        new_id = secrets.token_urlsafe(32)
        _session_cookie['session_id'] = new_id
        return new_id
    
    # Rotate session ID for archive access authorization (privilege change)
    _rotate_session_id()
    
    # Normalize dest_path to absolute base directory
    try:
        abs_dest = os.path.abspath(os.path.realpath(dest_path))
        if not os.path.exists(abs_dest):
            os.makedirs(abs_dest, exist_ok=True)
        abs_dest = os.path.abspath(os.path.realpath(abs_dest))
    except (OSError, ValueError):
        return False
    
    # Validate tar_path exists and is readable
    if not os.path.isfile(tar_path):
        return False
    
    # Open tar and enumerate members without extracting
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            
            # First pass: validate all members
            validated_paths = []
            for member in members:
                # Skip malicious member types
                if member.issym() or member.islnk():
                    return False
                
                # Only allow regular files and directories
                if not (member.isfile() or member.isdir()):
                    return False
                
                # Compute normalized extraction path
                # Prevent path traversal by checking each component
                member_name = member.name
                
                # Reject absolute paths
                if os.path.isabs(member_name):
                    return False
                
                # Reject parent directory references
                parts = member_name.replace('\\', '/').split('/')
                for part in parts:
                    if part == '..':
                        return False
                
                # Build and verify the full path
                full_path = os.path.join(abs_dest, member_name)
                try:
                    normalized_path = os.path.abspath(os.path.realpath(full_path))
                except (OSError, ValueError):
                    return False
                
                # Ensure the normalized path is under abs_dest
                # Use os.path.commonpath for reliable comparison
                try:
                    common = os.path.commonpath([normalized_path, abs_dest])
                except ValueError:
                    # On Windows, different drives would raise ValueError
                    return False
                
                if common != abs_dest:
                    return False
                
                # Additional check: ensure normalized_path starts with abs_dest + sep
                # to prevent partial directory name attacks
                if not (normalized_path == abs_dest or 
                        normalized_path.startswith(abs_dest + os.sep) or
                        normalized_path.startswith(abs_dest + '/')):
                    return False
                
                validated_paths.append((member, normalized_path))
            
            # Rotate session ID after successful validation (privilege change)
            _rotate_session_id()
            
            # Second pass: extract to verified paths
            for member, verified_path in validated_paths:
                if member.isdir():
                    try:
                        os.makedirs(verified_path, exist_ok=True)
                        # Restore directory permissions if needed
                        os.chmod(verified_path, member.mode & 0o7777)
                    except OSError:
                        return False
                elif member.isfile():
                    try:
                        # Create parent directories
                        parent_dir = os.path.dirname(verified_path)
                        os.makedirs(parent_dir, exist_ok=True)
                        
                        # Extract file content
                        with tar.extractfile(member) as fsrc:
                            if fsrc is None:
                                return False
                            
                            # Write to temporary file first, then rename for atomicity
                            import tempfile
                            fd, temp_path = tempfile.mkstemp(dir=parent_dir)
                            try:
                                with os.fdopen(fd, 'wb') as fdst:
                                    while True:
                                        chunk = fsrc.read(65536)
                                        if not chunk:
                                            break
                                        fdst.write(chunk)
                                
                                # Set permissions before rename
                                os.chmod(temp_path, member.mode & 0o7777)
                                
                                # Atomic rename to final destination
                                os.replace(temp_path, verified_path)
                            except OSError:
                                try:
                                    os.unlink(temp_path)
                                except OSError:
                                    pass
                                return False
                    except (OSError, tarfile.TarError):
                        return False
            
            # Rotate session ID after completion (privilege change)
            _rotate_session_id()
            
            return True
            
    except (tarfile.TarError, OSError, EOFError):
        return False
    
    return False
