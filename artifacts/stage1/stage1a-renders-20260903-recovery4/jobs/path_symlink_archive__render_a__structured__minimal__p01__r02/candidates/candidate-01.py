import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.realpath(dest_path))
    except (OSError, ValueError):
        return False

    if not os.path.isdir(dest_path):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            validated_paths = []

            for member in members:
                if member.issym() or member.islnk():
                    return False

                if not (member.isfile() or member.isdir()):
                    return False

                member_name = member.name

                if os.path.isabs(member_name):
                    return False

                parts = member_name.replace('\\', '/').split('/')
                clean_parts = []
                for part in parts:
                    if part == '' or part == '.':
                        continue
                    elif part == '..':
                        return False
                    else:
                        clean_parts.append(part)

                if not clean_parts:
                    if member.isdir():
                        continue
                    else:
                        return False

                relative_path = os.path.join(*clean_parts)
                target_path = os.path.join(dest_path, relative_path)
                target_path = os.path.abspath(os.path.realpath(target_path))

                try:
                    real_dest = os.path.realpath(dest_path)
                except (OSError, ValueError):
                    return False

                if target_path == real_dest:
                    if member.isdir():
                        continue
                    else:
                        return False

                try:
                    common = os.path.commonpath([target_path, real_dest])
                except ValueError:
                    return False

                if common != real_dest:
                    return False

                validated_paths.append((member, target_path))

            for member, target_path in validated_paths:
                if member.isdir():
                    try:
                        os.makedirs(target_path, exist_ok=True)
                    except (OSError, IOError):
                        return False
                elif member.isfile():
                    try:
                        parent_dir = os.path.dirname(target_path)
                        if parent_dir:
                            os.makedirs(parent_dir, exist_ok=True)
                    except (OSError, IOError):
                        return False

                    try:
                        file_obj = tf.extractfile(member)
                        if file_obj is None:
                            return False
                    except (OSError, IOError, tarfile.TarError):
                        return False

                    try:
                        with open(target_path, 'wb') as f:
                            while True:
                                chunk = file_obj.read(65536)
                                if not chunk:
                                    break
                                f.write(chunk)
                    except (OSError, IOError):
                        return False
                    finally:
                        file_obj.close()

                    try:
                        mode = member.mode
                        if mode is not None:
                            os.chmod(target_path, mode)
                    except (OSError, IOError):
                        pass

        return True

    except (tarfile.TarError, OSError, IOError):
        return False
