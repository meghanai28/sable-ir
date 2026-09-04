import os
import tarfile
import tempfile
import shutil


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.realpath(dest_path))
        if not os.path.isdir(dest_path):
            return False
        
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            validated_members = []
            for member in members:
                member_path = member.name
                
                if os.path.isabs(member_path):
                    member_path = member_path.lstrip('/')
                    if not member_path:
                        continue
                
                normalized_member_path = os.path.normpath(member_path)
                if normalized_member_path.startswith('..') or os.path.isabs(normalized_member_path):
                    return False
                
                full_member_path = os.path.join(dest_path, normalized_member_path)
                real_member_path = os.path.realpath(full_member_path)
                
                if not real_member_path.startswith(dest_path + os.sep) and real_member_path != dest_path:
                    return False
                
                if member.issym() or member.islnk():
                    link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_link_target = os.path.normpath(link_target)
                        if not normalized_link_target.startswith(dest_path + os.sep) and normalized_link_target != dest_path:
                            return False
                    else:
                        link_dir = os.path.dirname(real_member_path)
                        normalized_link_target = os.path.normpath(os.path.join(link_dir, link_target))
                        real_link_target = os.path.realpath(normalized_link_target)
                        
                        if not real_link_target.startswith(dest_path + os.sep) and real_link_target != dest_path:
                            return False
                
                validated_members.append((member, real_member_path))
            
            with tempfile.TemporaryDirectory(dir=dest_path) as tmpdir:
                for member, expected_path in validated_members:
                    try:
                        tf.extract(member, path=tmpdir, set_attrs=False)
                    except Exception:
                        return False
                    
                    extracted_path = os.path.join(tmpdir, member.name)
                    real_extracted_path = os.path.realpath(extracted_path)
                    
                    if not real_extracted_path.startswith(dest_path + os.sep) and real_extracted_path != dest_path:
                        return False
                    
                    if member.issym() or member.islnk():
                        if os.path.islink(extracted_path):
                            link_target = os.readlink(extracted_path)
                            if os.path.isabs(link_target):
                                normalized_target = os.path.normpath(link_target)
                                if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                                    return False
                            else:
                                link_dir = os.path.dirname(real_extracted_path)
                                normalized_target = os.path.normpath(os.path.join(link_dir, link_target))
                                real_target = os.path.realpath(normalized_target)
                                if not real_target.startswith(dest_path + os.sep) and real_target != dest_path:
                                    return False
                
                for member, expected_path in validated_members:
                    extracted_path = os.path.join(tmpdir, member.name)
                    real_extracted_path = os.path.realpath(extracted_path)
                    
                    if not real_extracted_path.startswith(dest_path + os.sep) and real_extracted_path != dest_path:
                        return False
                    
                    final_path = expected_path
                    
                    if os.path.exists(final_path) or os.path.islink(final_path):
                        if os.path.isdir(final_path) and not os.path.islink(final_path):
                            shutil.rmtree(final_path)
                        else:
                            os.remove(final_path)
                    
                    final_dir = os.path.dirname(final_path)
                    os.makedirs(final_dir, exist_ok=True)
                    
                    if member.isdir():
                        os.makedirs(final_path, exist_ok=True)
                        shutil.copymode(extracted_path, final_path)
                    elif member.issym():
                        link_target = os.readlink(extracted_path)
                        os.symlink(link_target, final_path)
                    elif member.islnk():
                        link_target = os.readlink(extracted_path)
                        if os.path.isabs(link_target):
                            normalized_target = os.path.normpath(link_target)
                            if not normalized_target.startswith(dest_path + os.sep) and normalized_target != dest_path:
                                return False
                            os.link(normalized_target, final_path)
                        else:
                            link_dir = os.path.dirname(final_path)
                            normalized_target = os.path.normpath(os.path.join(link_dir, link_target))
                            real_target = os.path.realpath(normalized_target)
                            if not real_target.startswith(dest_path + os.sep) and real_target != dest_path:
                                return False
                            os.link(real_target, final_path)
                    elif member.isreg() or member.ischr() or member.isblk() or member.isfifo() or member.isdev():
                        shutil.copy2(extracted_path, final_path)
                    else:
                        return False
        
        return True
    
    except Exception:
        return False
