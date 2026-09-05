import os
import tarfile
import stat
import shutil

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
        # Ensure dest_path exists and is a directory
        dest_path = os.path.abspath(dest_path)
        if not os.path.isdir(dest_path):
            return False
        
        # Resolve the tar file path
        tar_file = os.path.abspath(tar_path)
        if not os.path.isfile(tar_file):
            return False
        
        # Create a temporary directory for safe extraction
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp(dir=dest_path, prefix='.safe_extract_')
            
            with tarfile.open(tar_file, 'r:*') as tar:
                for member in tar.getmembers():
                    # Skip directories to avoid creating them (optional safety, but standard is to extract dirs)
                    # However, we must validate the final path before extraction
                    
                    # Calculate the full path where this member would be extracted
                    # We use the temp_dir as the base for validation to ensure we don't escape
                    # But actually, we should validate against dest_path directly as per spec "outside dest_path"
                    # Let's calculate the target path relative to dest_path
                    target_path = os.path.normpath(os.path.join(dest_path, member.name))
                    
                    # Security check: Ensure the target path is within dest_path
                    # We resolve both paths and check if target starts with dest_path
                    # Note: dest_path might have trailing slash or not, so we normalize
                    dest_path_normalized = os.path.normpath(dest_path)
                    target_path_normalized = os.path.normpath(target_path)
                    
                    # Check if target is outside dest_path (e.g., ../traversal)
                    if not (target_path_normalized.startswith(dest_path_normalized + os.sep) or 
                            target_path_normalized == dest_path_normalized):
                        return False
                    
                    # Check for symbolic links and resolve their targets
                    if member.issym() or member.islnk():
                        # Get the link target
                        link_target = member.linkname
                        
                        # Resolve the link target relative to the member's location in the archive
                        # The link target in the tar file is relative to the member's directory
                        # We need to resolve it against the member's path to get the absolute path
                        # Actually, tar link targets are relative to the member's directory in the archive
                        # But for safety, we should resolve it relative to the extraction point
                        
                        # Calculate the location of the member in the temp directory
                        member_in_temp = os.path.normpath(os.path.join(temp_dir, member.name))
                        
                        # Resolve the link target relative to the member's location
                        # If the member is a directory, the link target is relative to that directory
                        # If the member is a file, the link target is relative to the file's directory (which is parent)
                        # Standard behavior: link target is relative to the member's directory
                        link_target_resolved = os.path.normpath(os.path.join(member_in_temp, link_target))
                        
                        # Further resolve to handle ..
                        link_target_resolved = os.path.normpath(link_target_resolved)
                        
                        # Security check: Ensure resolved link target is within dest_path
                        if not (link_target_resolved.startswith(dest_path_normalized + os.sep) or 
                                link_target_resolved == dest_path_normalized):
                            return False
                        
                        # Also check for hard links
                        if member.islnk():
                            # Hard links are stored with a linkname that is relative to the member's directory
                            # Similar resolution applies
                            hard_link_target = member.linkname
                            hard_link_target_resolved = os.path.normpath(os.path.join(member_in_temp, hard_link_target))
                            hard_link_target_resolved = os.path.normpath(hard_link_target_resolved)
                            
                            if not (hard_link_target_resolved.startswith(dest_path_normalized + os.sep) or 
                                    hard_link_target_resolved == dest_path_normalized):
                                return False
                    
                    # Extract the member to the temp directory
                    tar.extract(member, temp_dir)
                    
                    # After extraction, we need to move the extracted content to dest_path
                    # But first, we should validate the extracted file's location
                    extracted_path = os.path.normpath(os.path.join(temp_dir, member.name))
                    
                    # Check if extracted path is within dest_path
                    if not (extracted_path.startswith(dest_path_normalized + os.sep) or 
                            extracted_path == dest_path_normalized):
                        # Clean up temp dir if needed
                        if temp_dir and os.path.exists(temp_dir):
                            shutil.rmtree(temp_dir, ignore_errors=True)
                        return False
                    
                    # Move the extracted file/directory to dest_path
                    # We need to handle the case where dest_path already exists
                    dest_dir = os.path.dirname(extracted_path)
                    dest_file = os.path.basename(extracted_path)
                    
                    # Ensure dest_dir exists in dest_path
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir, exist_ok=True)
                    
                    # Move the file
                    if os.path.exists(extracted_path):
                        shutil.move(extracted_path, dest_path)
                    else:
                        # If extraction failed or was skipped, clean up
                        if temp_dir and os.path.exists(temp_dir):
                            shutil.rmtree(temp_dir, ignore_errors=True)
                        return False
                        
        except Exception:
            return False
        finally:
            # Clean up temp directory if it was created
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        return True
        
    except Exception:
        return False
