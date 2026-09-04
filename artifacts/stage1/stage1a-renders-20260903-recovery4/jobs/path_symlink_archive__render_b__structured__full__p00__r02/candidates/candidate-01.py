import os
import tarfile
from os.path import normpath, join, commonpath, dirname, isabs, abspath, exists


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    # Establish trusted root
    try:
        root = normpath(abspath(dest_path))
    except (OSError, ValueError):
        return False

    # Ensure root exists and is a directory
    try:
        if not exists(root):
            os.makedirs(root, exist_ok=True)
        if not os.path.isdir(root):
            return False
    except (OSError, PermissionError):
        return False

    approved_actions = []

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            # Phase 1: Read-only validation pass
            for member in tf.getmembers():
                # Compute normalized member path
                member_path = normpath(join(root, member.name))

                # Check member path is within root
                try:
                    if commonpath([member_path, root]) != root:
                        return False
                except ValueError:
                    return False

                # Check member is strictly beneath root (not root itself unless directory)
                if member_path == root and not member.isdir():
                    return False

                action = {
                    'type': None,
                    'member_path': member_path,
                    'tar_info': member,
                }

                if member.isfile():
                    action['type'] = 'file'
                elif member.isdir():
                    action['type'] = 'dir'
                elif member.issym():
                    raw_target = member.linkname
                    if isabs(raw_target):
                        link_target = normpath(raw_target)
                    else:
                        link_target = normpath(join(dirname(member_path), raw_target))

                    # Validate symlink target is within root
                    try:
                        if commonpath([link_target, root]) != root:
                            return False
                    except ValueValueError:
                        return False

                    action['type'] = 'symlink'
                    action['link_target'] = raw_target  # Use original target string
                elif member.islnk():
                    link_target = normpath(join(root, member.linkname))

                    # Validate hardlink target is within root
                    try:
                        if commonpath([link_target, root]) != root:
                            return False
                    except ValueError:
                        return False

                    action['type'] = 'hardlink'
                    action['link_target'] = link_target
                else:
                    # Reject unsupported member types
                    return False

                approved_actions.append(action)

            # Phase 2: Extraction pass
            for action in approved_actions:
                member_path = action['member_path']
                member = action['tar_info']

                # Create parent directories as needed
                parent_dir = dirname(member_path)
                try:
                    if parent_dir != root:
                        os.makedirs(parent_dir, exist_ok=True)
                except (OSError, PermissionError):
                    return False

                if action['type'] == 'dir':
                    try:
                        os.makedirs(member_path, exist_ok=True)
                    except (OSError, PermissionError):
                        return False
                elif action['type'] == 'file':
                    try:
                        with tf.extractfile(member) as src_f:
                            if src_f is None:
                                return False
                            with open(member_path, 'wb') as dst_f:
                                while True:
                                    chunk = src_f.read(65536)
                                    if not chunk:
                                        break
                                    dst_f.write(chunk)
                    except (OSError, PermissionError, tarfile.TarError, AttributeError):
                        return False
                elif action['type'] == 'symlink':
                    try:
                        # Remove existing file/symlink if present to avoid errors
                        if exists(member_path) or os.path.islink(member_path):
                            os.remove(member_path)
                        os.symlink(action['link_target'], member_path)
                    except (OSError, PermissionError):
                        return False
                elif action['type'] == 'hardlink':
                    try:
                        # Remove existing file if present to avoid errors
                        if exists(member_path) or os.path.islink(member_path):
                            os.remove(member_path)
                        os.link(action['link_target'], member_path)
                    except (OSError, PermissionError):
                        return False

    except (tarfile.TarError, OSError, PermissionError):
        return False

    return True
