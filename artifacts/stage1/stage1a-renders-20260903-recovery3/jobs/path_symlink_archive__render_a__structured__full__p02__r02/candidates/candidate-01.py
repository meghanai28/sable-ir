import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        abs_dest = os.path.normpath(os.path.abspath(dest_path))
        if not abs_dest.endswith(os.sep):
            abs_dest_with_sep = abs_dest + os.sep
        else:
            abs_dest_with_sep = abs_dest

        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf.getmembers():
                if member.issym() or member.islnk():
                    return False

                if member.isdir() or member.isfile():
                    member_name = member.name
                    candidate = os.path.normpath(os.path.join(abs_dest, member_name))
                    candidate_with_sep = candidate + os.sep if not candidate.endswith(os.sep) else candidate

                    if not (candidate_with_sep.startswith(abs_dest_with_sep) or candidate == abs_dest):
                        return False

                    try:
                        if member.isdir():
                            os.makedirs(candidate, exist_ok=True)
                        elif member.isfile():
                            parent_dir = os.path.dirname(candidate)
                            if parent_dir:
                                os.makedirs(parent_dir, exist_ok=True)
                            with tf.extractfile(member) as fsrc:
                                if fsrc is None:
                                    return False
                                with open(candidate, 'wb') as fdst:
                                    while True:
                                        chunk = fsrc.read(8192)
                                        if not chunk:
                                            break
                                        fdst.write(chunk)
                    except (OSError, IOError):
                        return False
                else:
                    return False

        return True
    except (OSError, IOError, tarfile.TarError):
        return False
