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

    base_path_with_sep = base_path + os.sep

    try:
        tar = tarfile.open(tar_path, 'r:*')
    except (OSError, tarfile.TarError, ValueError):
        return False

    try:
        for member in tar:
            if member.issym() or member.islnk():
                tar.close()
                return False

            if not (member.isfile() or member.isdir()):
                tar.close()
                return False

            member_name = member.name

            if os.path.isabs(member_name):
                tar.close()
                return False

            candidate_path = os.path.realpath(os.path.abspath(os.path.join(base_path, member_name)))

            if candidate_path != base_path and not candidate_path.startswith(base_path_with_sep):
                tar.close()
                return False

            if member.isfile():
                parent_dir = candidate_path
                while True:
                    parent_dir = os.path.dirname(parent_dir)
                    if parent_dir == base_path:
                        break
                    if parent_dir == os.path.dirname(parent_dir):
                        tar.close()
                        return False
                    real_parent = os.path.realpath(parent_dir)
                    if real_parent != base_path and not real_parent.startswith(base_path_with_sep):
                        tar.close()
                        return False

                try:
                    os.makedirs(os.path.dirname(candidate_path), exist_ok=True)
                except OSError:
                    tar.close()
                    return False

                try:
                    source = tar.extractfile(member)
                    if source is None:
                        tar.close()
                        return False
                    with open(candidate_path, 'wb') as target:
                        while True:
                            chunk = source.read(65536)
                            if not chunk:
                                break
                            target.write(chunk)
                except (OSError, ValueError):
                    tar.close()
                    return False

            elif member.isdir():
                try:
                    os.makedirs(candidate_path, exist_ok=True)
                except OSError:
                    tar.close()
                    return False

        tar.close()
        return True

    except (OSError, tarfile.TarError, ValueError):
        try:
            tar.close()
        except Exception:
            pass
        return False
    except Exception:
        try:
            tar.close()
        except Exception:
            pass
        return False
