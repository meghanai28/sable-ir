import os
import tarfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        trust_anchor = os.path.realpath(dest_path)
        trust_anchor = os.path.abspath(trust_anchor)
        strict_prefix = trust_anchor + os.sep

        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    return False

                if not member.isfile() and not member.isdir():
                    return False

                member_name = member.name
                candidate_path = os.path.normpath(os.path.join(trust_anchor, member_name))

                if not candidate_path.startswith(strict_prefix):
                    return False

                if candidate_path == trust_anchor:
                    return False

                if member.isdir():
                    os.makedirs(candidate_path, exist_ok=True)
                elif member.isfile():
                    parent_dir = os.path.dirname(candidate_path)
                    if not parent_dir.startswith(strict_prefix) and parent_dir != trust_anchor:
                        return False
                    os.makedirs(parent_dir, exist_ok=True)

                    with tar.extractfile(member) as f:
                        if f is None:
                            return False
                        content = f.read()

                    with open(candidate_path, 'wb') as out_f:
                        out_f.write(content)

        return True

    except Exception:
        return False
