import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        base_path = os.path.realpath(os.path.abspath(dest_path))
    except (OSError, ValueError):
        return False

    if not os.path.isdir(base_path):
        try:
            os.makedirs(base_path, exist_ok=True)
        except OSError:
            return False

    try:
        base_path = os.path.realpath(os.path.abspath(dest_path))
    except (OSError, ValueError):
        return False

    try:
        tf = tarfile.open(tar_path, mode='r:*')
    except (tarfile.TarError, OSError, EOFError):
        return False

    try:
        for member in tf:
            if member.issym() or member.islnk():
                tf.close()
                return False

            if not (member.isfile() or member.isdir()):
                tf.close()
                return False

            member_name = member.name

            if os.path.isabs(member_name):
                tf.close()
                return False

            candidate_path = os.path.join(base_path, member_name)
            try:
                resolved_path = os.path.realpath(os.path.abspath(candidate_path))
            except (OSError, ValueError):
                tf.close()
                return False

            if resolved_path != base_path:
                if not resolved_path.startswith(base_path + os.sep):
                    tf.close()
                    return False

            if member.isfile():
                parent_dir = os.path.dirname(resolved_path)
                try:
                    real_parent = os.path.realpath(os.path.abspath(parent_dir))
                except (OSError, ValueError):
                    tf.close()
                    return False

                if real_parent != base_path:
                    if not real_parent.startswith(base_path + os.sep):
                        tf.close()
                        return False

                try:
                    os.makedirs(parent_dir, exist_ok=True)
                except OSError:
                    tf.close()
                    return False

                try:
                    with open(resolved_path, 'wb') as out_f:
                        with tf.extractfile(member) as member_f:
                            if member_f is None:
                                tf.close()
                                return False
                            while True:
                                chunk = member_f.read(65536)
                                if not chunk:
                                    break
                                out_f.write(chunk)
                except (OSError, IOError, tarfile.TarError):
                    tf.close()
                    return False

            elif member.isdir():
                try:
                    os.makedirs(resolved_path, exist_ok=True)
                except OSError:
                    tf.close()
                    return False

        tf.close()
        return True

    except (tarfile.TarError, OSError, EOFError):
        try:
            tf.close()
        except Exception:
            pass
        return False
    except Exception:
        try:
            tf.close()
        except Exception:
            pass
        return False
