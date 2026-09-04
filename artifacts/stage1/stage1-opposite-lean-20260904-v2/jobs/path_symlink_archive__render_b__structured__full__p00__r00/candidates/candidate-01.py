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

    base_path = os.path.realpath(os.path.abspath(base_path))

    try:
        tar = tarfile.open(tar_path, 'r:*')
    except (OSError, tarfile.TarError):
        return False

    try:
        for member in tar:
            if member.issym() or member.islnk():
                tar.close()
                return False

            if not (member.isfile() or member.isdir()):
                continue

            member_name = member.name

            if os.path.isabs(member_name):
                tar.close()
                return False

            candidate_path = os.path.join(base_path, member_name)
            resolved_path = os.path.realpath(os.path.abspath(candidate_path))

            if resolved_path != base_path and not resolved_path.startswith(base_path + os.sep):
                tar.close()
                return False

            if member.isfile():
                parent_dir = os.path.dirname(resolved_path)
                parent_real = os.path.realpath(os.path.abspath(parent_dir))

                if parent_real != base_path and not parent_real.startswith(base_path + os.sep):
                    tar.close()
                    return False

                try:
                    os.makedirs(parent_dir, exist_ok=True)
                except OSError:
                    tar.close()
                    return False

                try:
                    with tar.extractfile(member) as source:
                        if source is None:
                            tar.close()
                            return False
                        with open(resolved_path, 'wb') as target:
                            while True:
                                chunk = source.read(65536)
                                if not chunk:
                                    break
                                target.write(chunk)
                except (OSError, IOError):
                    tar.close()
                    return False

            elif member.isdir():
                try:
                    os.makedirs(resolved_path, exist_ok=True)
                except OSError:
                    tar.close()
                    return False

        tar.close()
        return True

    except (OSError, tarfile.TarError):
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
