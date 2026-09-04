import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_abs = os.path.abspath(os.path.normpath(dest_path))
        if not dest_abs.endswith(os.sep):
            dest_abs += os.sep

        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()

            validated_members = []
            for member in members:
                member_path = member.name
                if os.path.isabs(member_path):
                    member_path = member_path.lstrip('/')
                    if not member_path:
                        member_path = '.'

                extracted_path = os.path.join(dest_abs, member_path)
                normalized_path = os.path.normpath(extracted_path)

                if normalized_path != dest_abs and not normalized_path.startswith(dest_abs):
                    return False

                if member.issym() or member.islnk():
                    if member.issym():
                        link_target = member.linkname
                    else:
                        link_target = member.linkname

                    if os.path.isabs(link_target):
                        normalized_target = os.path.normpath(link_target)
                        if normalized_target != dest_abs and not normalized_target.startswith(dest_abs):
                            return False
                    else:
                        if member.issym():
                            target_base = os.path.dirname(normalized_path)
                        else:
                            target_base = dest_abs

                        resolved_target = os.path.join(target_base, link_target)
                        normalized_target = os.path.normpath(resolved_target)

                        if normalized_target != dest_abs and not normalized_target.startswith(dest_abs):
                            return False

                validated_members.append(member)

            for member in validated_members:
                member_path = member.name
                if os.path.isabs(member_path):
                    member_path = member_path.lstrip('/')
                    if not member_path:
                        member_path = '.'

                extracted_path = os.path.join(dest_abs, member_path)
                normalized_path = os.path.normpath(extracted_path)

                if member.issym() or member.islnk():
                    if member.issym():
                        link_target = member.linkname
                    else:
                        link_target = member.linkname

                    if os.path.isabs(link_target):
                        normalized_target = os.path.normpath(link_target)
                    else:
                        if member.issym():
                            target_base = os.path.dirname(normalized_path)
                        else:
                            target_base = dest_abs

                        resolved_target = os.path.join(target_base, link_target)
                        normalized_target = os.path.normpath(resolved_target)

                    if normalized_target != dest_abs and not normalized_target.startswith(dest_abs):
                        return False

                    if member.issym():
                        os.symlink(link_target, normalized_path)
                    else:
                        os.link(normalized_target, normalized_path)
                elif member.isdir():
                    os.makedirs(normalized_path, exist_ok=True)
                elif member.isfile():
                    os.makedirs(os.path.dirname(normalized_path), exist_ok=True)
                    with tf.extractfile(member) as fobj:
                        if fobj is not None:
                            with open(normalized_path, 'wb') as outfile:
                                outfile.write(fobj.read())
                else:
                    pass

            return True

    except Exception:
        return False
