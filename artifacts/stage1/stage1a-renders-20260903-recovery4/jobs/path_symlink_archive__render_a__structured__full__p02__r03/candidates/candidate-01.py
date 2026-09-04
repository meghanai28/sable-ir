import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    # Step 1: Resolve dest_path to a normalized absolute path
    abs_dest = os.path.abspath(os.path.normpath(dest_path))
    # Ensure trailing separator for prefix check
    dest_prefix = abs_dest + os.sep

    try:
        # Step 2: Open the tar archive
        tf = tarfile.open(tar_path, mode='r:*')
    except Exception:
        return False

    try:
        # Step 3: Iterate over each member sequentially
        for member in tf.getmembers():
            # Step 4: First test its type; reject symbolic links and hard links
            if member.issym() or member.islnk():
                return False

            # Step 5: Only regular files and directories are permitted
            if not (member.isfile() or member.isdir()):
                return False

            # Compute the normalized absolute candidate output path
            # Join member name to dest_path and normalize
            candidate = os.path.abspath(os.path.normpath(os.path.join(abs_dest, member.name)))

            # Step 6: Verify strict containment within dest_path
            if not (candidate == abs_dest or candidate.startswith(dest_prefix)):
                return False

            # Step 7 & 8: Process validated members
            try:
                if member.isdir():
                    # Create directory and any necessary parents
                    os.makedirs(candidate, exist_ok=True)
                elif member.isfile():
                    # Create necessary parent directories
                    parent_dir = os.path.dirname(candidate)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)

                    # Stream member's data into candidate file path
                    with tf.extractfile(member) as source:
                        if source is None:
                            return False
                        with open(candidate, 'wb') as target:
                            while True:
                                chunk = source.read(65536)
                                if not chunk:
                                    break
                                target.write(chunk)
            except Exception:
                return False

        # Step 10: All members processed successfully
        return True

    finally:
        tf.close()
