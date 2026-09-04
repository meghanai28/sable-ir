import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_real = os.path.realpath(dest_path)
        if not os.path.isdir(dest_real):
            try:
                os.makedirs(dest_real, exist_ok=True)
            except OSError:
                return False

        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()

            validated_members = []

            for member in members:
                member_name = member.name
                if member_name.startswith('/') or member_name.startswith('\\'):
                    member_name = member_name[1:]
                if '..' in member_name.split('/'):
                    return False
                if member_name == '' or member_name == '.':
                    if member.isdir():
                        continue
                    else:
                        return False

                normalized_member = os.path.normpath(member_name)
                if normalized_member.startswith('..') or os.path.isabs(normalized_member):
                    return False

                full_member_path = os.path.join(dest_real, normalized_member)
                real_member_path = os.path.realpath(full_member_path)

                if not real_member_path.startswith(dest_real + os.sep) and real_member_path != dest_real:
                    return False

                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if link_target.startswith('/') or link_target.startswith('\\'):
                        normalized_target = os.path.normpath(link_target)
                        if os.path.isabs(normalized_target):
                            full_target = os.path.join(dest_real, normalized_target.lstrip('/').lstrip('\\'))
                        else:
                            full_target = os.path.join(dest_real, normalized_target)
                    else:
                        normalized_target = os.path.normpath(link_target)
                        if '..' in normalized_target.split(os.sep):
                            member_dir = os.path.dirname(real_member_path)
                            full_target = os.path.normpath(os.path.join(member_dir, link_target))
                        else:
                            member_dir = os.path.dirname(real_member_path)
                            full_target = os.path.normpath(os.path.join(member_dir, link_target))

                    real_target = os.path.realpath(full_target)

                    if not real_target.startswith(dest_real + os.sep) and real_target != dest_real:
                        return False

                validated_members.append(member)

            for member in validated_members:
                member_name = member.name
                if member_name.startswith('/') or member_name.startswith('\\'):
                    member_name = member_name[1:]
                if '..' in member_name.split('/'):
                    return False

                normalized_member = os.path.normpath(member_name)
                full_member_path = os.path.join(dest_real, normalized_member)

                if member.issym():
                    link_target = member.linkname
                    if link_target.startswith('/') or link_target.startswith('\\'):
                        normalized_target = os.path.normpath(link_target)
                        if os.path.isabs(normalized_target):
                            target_to_use = '/' + normalized_target.lstrip('/').lstrip('\\')
                        else:
                            target_to_use = link_target
                    else:
                        target_to_use = link_target

                    parent_dir = os.path.dirname(full_member_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    if os.path.exists(full_member_path) or os.path.islink(full_member_path):
                        os.remove(full_member_path)
                    os.symlink(target_to_use, full_member_path)

                elif member.islnk():
                    link_target = member.linkname
                    if link_target.startswith('/') or link_target.startswith('\\'):
                        normalized_target = os.path.normpath(link_target)
                        if os.path.isabs(normalized_target):
                            source_path = os.path.join(dest_real, normalized_target.lstrip('/').lstrip('\\'))
                        else:
                            source_path = os.path.join(dest_real, link_target)
                    else:
                        member_dir = os.path.dirname(full_member_path)
                        source_path = os.path.normpath(os.path.join(member_dir, link_target))

                    parent_dir = os.path.dirname(full_member_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    if os.path.exists(full_member_path) or os.path.islink(full_member_path):
                        os.remove(full_member_path)
                    os.link(source_path, full_member_path)

                else:
                    tf.extract(member, path=dest_real)

        return True

    except (tarfile.TarError, OSError, ValueError, IOError):
        return False
