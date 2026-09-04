import os
import tarfile
from os.path import normpath, join, dirname, sep

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    safe_dest = normpath(os.path.abspath(dest_path))
    if not safe_dest.endswith(sep):
        safe_dest += sep

    def is_inside_safe(path: str) -> bool:
        normalized = normpath(path)
        if normalized == safe_dest.rstrip(sep):
            return True
        if normalized.startswith(safe_dest):
            return True
        return False

    def has_path_boundary_prefix(path: str) -> bool:
        normalized = normpath(path)
        if normalized == safe_dest.rstrip(sep):
            return True
        if normalized.startswith(safe_dest):
            next_char = normalized[len(safe_dest)]
            if next_char == sep:
                return True
        return False

    def sanitize_member_name(name: str) -> str:
        sanitized = name.lstrip(sep)
        if os.name == 'nt':
            if len(sanitized) >= 2 and sanitized[1] == ':':
                sanitized = sanitized[2:].lstrip(sep)
        while sanitized.startswith('..' + sep):
            sanitized = sanitized[3:]
        if sanitized == '..':
            sanitized = ''
        if sanitized.startswith(sep):
            sanitized = sanitized.lstrip(sep)
        return sanitized

    try:
        tf = tarfile.open(tar_path, 'r:*')
    except (tarfile.TarError, OSError, IOError):
        return False

    try:
        members = tf.getmembers()
    except (tarfile.TarError, OSError, IOError):
        tf.close()
        return False

    validated_manifest = {}
    symlink_members = {}
    hardlink_members = {}
    regular_members = []
    dir_members = []

    for member in members:
        sanitized_name = sanitize_member_name(member.name)
        if not sanitized_name and member.name:
            tf.close()
            return False

        extract_path = normpath(join(safe_dest.rstrip(sep), sanitized_name))

        if not has_path_boundary_prefix(extract_path):
            tf.close()
            return False

        if member.issym():
            link_target = member.linkname
            parent_dir = dirname(extract_path)
            if os.path.isabs(link_target):
                resolved_target = normpath(link_target)
            else:
                resolved_target = normpath(join(parent_dir, link_target))

            if not is_inside_safe(resolved_target):
                tf.close()
                return False

            symlink_members[member] = {
                'extract_path': extract_path,
                'link_target': link_target,
                'sanitized_name': sanitized_name
            }

        elif member.islnk():
            sanitized_link_name = sanitize_member_name(member.linkname)
            if not sanitized_link_name and member.linkname:
                tf.close()
                return False

            target_path = normpath(join(safe_dest.rstrip(sep), sanitized_link_name))

            if not has_path_boundary_prefix(target_path):
                tf.close()
                return False

            hardlink_members[member] = {
                'extract_path': extract_path,
                'target_path': target_path,
                'sanitized_link_name': sanitized_link_name
            }

        elif member.isdir():
            dir_members.append({
                'member': member,
                'extract_path': extract_path,
                'sanitized_name': sanitized_name
            })

        elif member.isfile() or member.isreg():
            regular_members.append({
                'member': member,
                'extract_path': extract_path,
                'sanitized_name': sanitized_name
            })

        else:
            tf.close()
            return False

    for hl_member, hl_info in hardlink_members.items():
        target_path = hl_info['target_path']
        target_is_symlink = False
        for sym_member, sym_info in symlink_members.items():
            if sym_info['extract_path'] == target_path:
                target_is_symlink = True
                break
        if target_is_symlink:
            tf.close()
            return False

    written_files = set()

    try:
        for dir_info in dir_members:
            extract_path = dir_info['extract_path']
            os.makedirs(extract_path, exist_ok=True)

        for reg_info in regular_members:
            member = reg_info['member']
            extract_path = reg_info['extract_path']

            parent_dir = dirname(extract_path)
            os.makedirs(parent_dir, exist_ok=True)

            if os.name == 'nt':
                fd = os.open(extract_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
            else:
                fd = os.open(extract_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o666)

            try:
                with os.fdopen(fd, 'wb') as f:
                    with tf.extractfile(member) as src:
                        if src is None:
                            os.close(fd)
                            return False
                        while True:
                            chunk = src.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
            except:
                try:
                    os.close(fd)
                except:
                    pass
                raise

            written_files.add(extract_path)

        for sym_member, sym_info in symlink_members.items():
            extract_path = sym_info['extract_path']
            link_target = sym_info['link_target']
            parent_dir = dirname(extract_path)
            os.makedirs(parent_dir, exist_ok=True)
            os.symlink(link_target, extract_path)

        for hl_member, hl_info in hardlink_members.items():
            extract_path = hl_info['extract_path']
            target_path = hl_info['target_path']

            if target_path not in written_files:
                if not os.path.exists(target_path):
                    tf.close()
                    return False

            parent_dir = dirname(extract_path)
            os.makedirs(parent_dir, exist_ok=True)
            os.link(target_path, extract_path)
            written_files.add(extract_path)

    except (OSError, IOError, tarfile.TarError):
        tf.close()
        return False

    tf.close()
    return True
