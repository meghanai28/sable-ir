import os
import stat

def read_report(filename: str, reports_root: str) -> str:
    # Resolve reports_root to an absolute path
    abs_root = os.path.abspath(reports_root)
    
    # Ensure reports_root exists and is a directory
    if not os.path.isdir(abs_root):
        raise ValueError("reports_root must be a directory")
    
    # Form candidate path by joining and normalize textually
    candidate = os.path.join(abs_root, filename)
    normalized = os.path.normpath(candidate)
    
    # Reject if normalized path equals reports_root or steps outside it
    if normalized == abs_root:
        raise ValueError("target must be strictly beneath reports_root")
    
    # Check for directory traversal outside root using commonprefix
    # Ensure normalized path starts with abs_root followed by separator
    if not normalized.startswith(abs_root + os.sep):
        raise ValueError("target must be strictly beneath reports_root")
    
    # Enforce symbolic-link prohibition on user-selected path components
    # Walk from first component after abs_root through final filename
    # Get the relative path from abs_root to normalized
    rel_path = os.path.relpath(normalized, abs_root)
    
    # Build up each prefix and check for symlinks
    current = abs_root
    components = rel_path.split(os.sep)
    
    for component in components:
        current = os.path.join(current, component)
        # Check if this path component is a symlink without following it
        try:
            file_stat = os.lstat(current)
            if stat.S_ISLNK(file_stat.st_mode):
                raise ValueError("symbolic link detected in user-selected path")
        except OSError:
            # If lstat fails, the path doesn't exist; that's ok for intermediate
            # components if it's the final component, but we still need to check
            # existing prefixes. For non-existing paths, lstat raises which we
            # can ignore if it's the last component we're checking - but actually
            # we need to be more careful. We should only skip if it's acceptable
            # for the path to not exist yet (i.e., we're creating), but for reads
            # the final file must exist. However, intermediate directories must
            # exist. Let's re-raise if it's not the final component, otherwise
            # let it pass to the open() call.
            # Actually, simpler: check what we can, and if a component doesn't
            # exist, we can't check it for symlink-ness. For existing prefixes,
            # we must verify. For the final file, if it doesn't exist, FileNotFoundError
            # will propagate from open().
            # But wait - what if a non-existent path has a symlink in an existing prefix?
            # We already checked all existing prefixes. If current doesn't exist,
            # we need to check if its parent exists and was checked.
            # Actually, we should check: if the error is because current doesn't exist,
            # and this is not the final component, then a parent directory is missing
            # which means the path is invalid. But the open() will also fail.
            # For symlink checking, we only care about existing nodes.
            # If lstat fails on an intermediate component, that means a directory
            # in the path doesn't exist, which will cause FileNotFoundError later.
            # But we should still check: is there a symlink at this exact location?
            # If the path doesn't exist, there's no symlink there.
            # However, we need to distinguish between "doesn't exist" and other errors.
            # For simplicity: if it's the last component, let it pass (open will handle).
            # If it's an intermediate component, the path is broken, but we still
            # need to ensure we don't miss a symlink check on an existing component.
            # Actually, os.lstat on a non-existent path raises FileNotFoundError.
            # Since we check components in order, if an earlier component is missing,
            # we can't reach later ones. So we should just pass on FileNotFoundError
            # for the final component only.
            if component != components[-1]:
                # Intermediate component doesn't exist - will cause FileNotFoundError
                # We can't continue checking further components meaningfully
                # But we should not raise ValueError here; let FileNotFoundError happen at open
                # Actually no: if an intermediate dir doesn't exist, we should stop checking
                # and let open() fail. But we need to make sure we don't miss symlinks.
                # Since we check in order, all prior existing components were checked.
                # This missing component is not a symlink (it doesn't exist).
                # We can break out since further components can't be checked anyway.
                break
            # For final component, if it doesn't exist, that's ok - open() will raise FileNotFoundError
    
    # All checks passed, open and read the file
    with open(normalized, 'r', encoding='utf-8') as f:
        return f.read()
