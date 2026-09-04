import os
import tarfile
from os.path import abspath, normpath, join, dirname, commonpath, isabs, exists


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    # Establish trusted root
    try:
        root = normpath(abspath(dest_path))
    except Exception:
        return False

    # Ensure root exists as a directory
    try:
        if not exists(root):
            os.makedirs(root, exist_ok=True)
        if not os.path.isdir(root):
            return False
    except Exception:
        return False

    approved_actions = []

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            # Phase 1: Read-only validation pass
            for member in tf.getmembers():
                # Compute member path
                member_path = normpath(join(root, member.name))

                # Check member path is within root
                try:
                    if commonpath([member_path, root]) != root:
                        return False
                except ValueError:
                    return False

                # Check member is not root itself (unless directory)
                if member_path == root and not member.isdir():
                    return False

                action_type = None
                link_target = None
                raw_target = None

                if member.isfile() or member.isdir():
                    action_type = 'file' if member.isfile() else 'dir'
                elif member.issym():
                    action_type = 'symlink'
                    raw_target = member.linkname
                    if isabs(raw_target):
                        link_target = normpath(raw_target)
                    else:
                        link_target = normpath(join(dirname(member_path), raw_target))
                    # Validate symlink target is within root
                    try:
                        if commonpath([link_target, root]) != root:
                            return False
                    except ValueError:
                        return False
                elif member.islnk():
                    action_type = 'hardlink'
                    link_target = normpath(join(root, member.linkname))
                    # Validate hardlink target is within root
                    try:
                        if commonpath([link_target, root]) != root:
                            return False
                    except ValueError:
                        return False
                else:
                    # Reject unsupported types (block devices, character devices, FIFOs, etc.)
                    return False

                approved_actions.append({
                    'member': member,
                    'member_path': member_path,
                    'action_type': action_type,
                    'link_target': link_target,
                    'raw_target': raw_target,
                })

            # Phase 2: Extraction pass
            for action in approved_actions:
                member = action['member']
                member_path = action['member_path']
                action_type = action['action_type']
                link_target = action['link_target']
                raw_target = action['raw_target']

                # Create parent directories as needed
                parent_dir = dirname(member_path)
                try:
                    if parent_dir and parent_dir != root:
                        os.makedirs(parent_dir, exist_ok=True)
                except Exception:
                    return False

                if action_type == 'dir':
                    try:
                        os.makedirs(member_path, exist_ok=True)
                    except Exception:
                        return False
                elif action_type == 'file':
                    try:
                        with tf.extractfile(member) as src:
                            if src is None:
                                return False
                            with open(member_path, 'wb') as dst:
                                while True:
                                    chunk = src.read(65536)
                                    if not chunk:
                                        break
                                    dst.write(chunk)
                    except Exception:
                        return False
                elif action_type == 'symlink':
                    try:
                        os.symlink(raw_target, member_path)
                    except Exception:
                        return False
                elif action_type == 'hardlink':
                    try:
                        os.link(link_target, member_path)
                    except Exception:
                        return False

    except Exception:
        return False

    return True
