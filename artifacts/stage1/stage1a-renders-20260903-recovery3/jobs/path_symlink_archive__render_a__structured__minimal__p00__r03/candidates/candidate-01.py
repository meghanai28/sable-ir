import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_abs = os.path.abspath(dest_path)
        if not os.path.isdir(dest_abs):
            try:
                os.makedirs(dest_abs, exist_ok=True)
            except OSError:
                return False

        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()

            validated_members = []
            for member in members:
                if member.issym() or member.islnk():
                    return False

                member_path = member.name
                if os.path.isabs(member_path):
                    member_path = member_path.lstrip('/')
                    if not member_path:
                        if member.isdir():
                            continue
                        return False

                resolved_path = os.path.join(dest_abs, member_path)
                resolved_abs = os.path.abspath(resolved_path)

                real_dest = os.path.realpath(dest_abs)
                real_resolved = os.path.realpath(resolved_abs)

                if not (real_resolved == real_dest or real_resolved.startswith(real_dest + os.sep)):
                    return False

                validated_members.append((member, resolved_abs))

            for member, extract_path in validated_members:
                try:
                    if member.isdir():
                        os.makedirs(extract_path, exist_ok=True)
                        continue

                    parent_dir = os.path.dirname(extract_path)
                    os.makedirs(parent_dir, exist_ok=True)

                    with tar.extractfile(member) as fobj:
                        if fobj is None:
                            return False
                        with open(extract_path, 'wb') as outfile:
                            while True:
                                chunk = fobj.read(65536)
                                if not chunk:
                                    break
                                outfile.write(chunk)

                    os.chmod(extract_path, member.mode)

                except (OSError, tarfile.TarError, TypeError, AttributeError):
                    return False

        return True

    except (OSError, tarfile.TarError):
        return False
