import os
import tarfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    """
    Extract a tar archive to dest_path with strict path validation.
    
    Returns True only if extraction completes successfully without writing
    any content outside dest_path. Returns False if validation or extraction fails.
    """
    try:
        # Normalize dest_path to absolute and resolve symlinks if necessary
        # We need to ensure dest_path is absolute and doesn't escape root
        dest_path = os.path.abspath(dest_path)
        
        # Check if dest_path escapes the root filesystem
        if not dest_path.startswith(os.sep) and dest_path != os.sep:
            # On Windows, os.sep is '\' and root is 'C:\' etc.
            # On Unix, os.sep is '/' and root is '/'
            # We check if the path starts with a drive letter (Windows) or is just '/' (Unix)
            if os.name == 'nt':
                # Windows: root is like 'C:', 'D:', etc.
                if dest_path.startswith('\\') or dest_path[1] == ':':
                    pass # Valid root
                else:
                    raise ValueError("dest_path escapes root filesystem")
            else:
                # Unix-like: root is '/'
                if dest_path == '/' or dest_path.startswith('/'):
                    pass
                else:
                    raise ValueError("dest_path escapes root filesystem")
        
        # Create dest_path directory if it doesn't exist
        os.makedirs(dest_path, exist_ok=True)
        
        # Open the tar archive
        with tarfile.open(tar_path, 'r:*') as tar:
            # Get list of all members before extracting
            members = tar.getnames()
            
            # Validate each member before extraction
            for member in members:
                member_info = tar.getmember(member)
                
                # Check if member is a symlink
                if member_info.issym():
                    # Resolve the symlink target
                    linkname = member_info.linkname
                    # Normalize the link target relative to dest_path
                    # The link target is relative to the member's location in the archive
                    # But we need to resolve it relative to the extraction directory
                    # Actually, for symlinks, we need to check the resolved path
                    # The linkname is relative to the member's directory in the archive
                    # But when extracting, the member will be at dest_path + member.name
                    # So the resolved path is dest_path + member.name + '/' + linkname
                    
                    # Resolve the link target
                    full_link_target = os.path.normpath(os.path.join(dest_path, member.name, linkname))
                    
                    # Check if the resolved link target escapes dest_path
                    # We need to check if the path starts with dest_path + os.sep
                    if not (full_link_target == dest_path or full_link_target.startswith(dest_path + os.sep)):
                        raise ValueError(f"Symlink {member.name} would escape dest_path: {full_link_target}")
                    
                    # Also check if the link target itself is outside dest_path
                    # We need to resolve the link target and ensure it's within dest_path
                    # The link target might be absolute or relative
                    if os.path.isabs(linkname):
                        # Absolute link target - must be within dest_path
                        resolved_link = os.path.normpath(linkname)
                        if not (resolved_link == dest_path or resolved_link.startswith(dest_path + os.sep)):
                            raise ValueError(f"Absolute symlink target {linkname} escapes dest_path")
                    else:
                        # Relative link target - resolve relative to the member's directory
                        # The member's directory is the prefix of member.name
                        member_dir = os.path.dirname(member.name)
                        resolved_link = os.path.normpath(os.path.join(dest_path, member_dir, linkname))
                        if not (resolved_link == dest_path or resolved_link.startswith(dest_path + os.sep)):
                            raise ValueError(f"Relative symlink target {linkname} escapes dest_path")
                
                # Check if member is a hard link
                elif member_info.issym():  # This also covers hard links in some tar implementations
                    # For hard links, we need to check the linkname
                    linkname = member_info.linkname
                    # Similar to symlinks, resolve the link target
                    member_dir = os.path.dirname(member.name)
                    full_link_target = os.path.normpath(os.path.join(dest_path, member_dir, linkname))
                    
                    if not (full_link_target == dest_path or full_link_target.startswith(dest_path + os.sep)):
                        raise ValueError(f"Hard link {member.name} would escape dest_path: {full_link_target}")
                
                # Check if member is a directory
                elif member.isdir():
                    # Directory members are safe as long as their name doesn't escape
                    # But we should still check if the name contains ..
                    if '..' in member.name.split(os.sep):
                        raise ValueError(f"Directory member {member.name} contains ..")
                
                # Check if member is a file
                else:
                    # For regular files, check if the member name contains ..
                    if '..' in member.name.split(os.sep):
                        raise ValueError(f"File member {member.name} contains ..")
            
            # Now extract the archive
            tar.extractall(dest_path)
            
            return True
            
    except Exception as e:
        return False
