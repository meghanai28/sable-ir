import os
import tarfile
import errno


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        abs_dest = os.path.abspath(os.path.normpath(dest_path))
        abs_dest = os.path.realpath(abs_dest)
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            validated = []

            for member in members:
                member_name = member.name
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        member_name = '.'

                member_name = member_name.replace('\\', '/')

                extracted_path = os.path.join(abs_dest, member_name)
                extracted_path = os.path.abspath(extracted_path)
                extracted_path = os.path.normpath(extracted_path)

                try:
                    real_extracted = os.path.realpath(extracted_path)
                except (OSError, ValueError):
                    return False

                if not real_extracted.startswith(abs_dest + os.sep) and real_extracted != abs_dest:
                    return False

                link_target = None

                if member.issym() or member.islnk():
                    if member.issym():
                        raw_target = member.linkname
                    else:
                        raw_target = member.linkname

                    if raw_target is None:
                        return False

                    if os.path.isabs(raw_target):
                        normalized_target = raw_target.lstrip('/')
                        if not normalized_target:
                            normalized_target = '.'
                    else:
                        member_parent = os.path.dirname(real_extracted)
                        normalized_target = os.path.join(member_parent, raw_target)
                        normalized_target = os.path.normpath(normalized_target)

                    try:
                        real_target = os.path.realpath(normalized_target)
                    except (OSError, ValueError):
                        return False

                    if not real_target.startswith(abs_dest + os.sep) and real_target != abs_dest:
                        return False

                    link_target = raw_target

                validated.append((member, real_extracted, link_target))

            for member, real_extracted, link_target in validated:
                parent_dir = os.path.dirname(real_extracted)

                try:
                    os.makedirs(parent_dir, exist_ok=True)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        return False

                if member.isdir():
                    try:
                        os.makedirs(real_extracted, exist_ok=True)
                        mode = member.mode
                        if mode:
                            try:
                                os.chmod(real_extracted, mode)
                            except OSError:
                                pass
                    except OSError:
                        return False
                elif member.isfile() or member.isreg():
                    try:
                        f = tf.extractfile(member)
                        if f is None:
                            return False
                        with open(real_extracted, 'wb') as out_f:
                            while True:
                                chunk = f.read(65536)
                                if not chunk:
                                    break
                                out_f.write(chunk)
                        mode = member.mode
                        if mode:
                            try:
                                os.chmod(real_extracted, mode)
                            except OSError:
                                pass
                    except (OSError, tarfile.TarError, IOError):
                        return False
                elif member.issym():
                    try:
                        if os.path.exists(real_extracted) or os.path.islink(real_extracted):
                            os.remove(real_extracted)
                        os.symlink(link_target, real_extracted)
                    except OSError:
                        return False
                elif member.islnk():
                    try:
                        if os.path.exists(real_extracted) or os.path.islink(real_extracted):
                            os.remove(real_extracted)
                        os.link(link_target, real_extracted)
                    except OSError:
                        return False
                else:
                    continue

            return True

    except (tarfile.TarError, OSError, IOError):
        return False
