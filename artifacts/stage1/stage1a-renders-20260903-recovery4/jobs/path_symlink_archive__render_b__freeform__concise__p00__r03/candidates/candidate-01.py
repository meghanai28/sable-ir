import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        abs_dest = os.path.abspath(os.path.normpath(dest_path))
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            validated_members = []
            
            for member in members:
                member_name = member.name
                
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        continue
                
                if member.issym() or member.islnk():
                    if member.issym():
                        link_target = member.linkname
                    else:
                        link_target = member.linkname
                    
                    if os.path.isabs(link_target):
                        normalized_target = os.path.normpath(link_target)
                    else:
                        member_dir = os.path.dirname(member_name)
                        if member_dir:
                            combined = os.path.join(member_dir, link_target)
                        else:
                            combined = link_target
                        normalized_target = os.path.normpath(combined)
                    
                    if os.path.isabs(normalized_target):
                        resolved_target = normalized_target
                    else:
                        resolved_target = os.path.join(abs_dest, normalized_target)
                    
                    resolved_target = os.path.normpath(resolved_target)
                    
                    if not (resolved_target == abs_dest or resolved_target.startswith(abs_dest + os.sep)):
                        return False
                    
                    validated_members.append((member, member_name, resolved_target))
                
                elif member.isdir() or member.isfile() or member.isfifo() or member.ischr() or member.isblk() or member.isdev():
                    extraction_path = os.path.join(abs_dest, member_name)
                    normalized_path = os.path.normpath(extraction_path)
                    
                    if not (normalized_path == abs_dest or normalized_path.startswith(abs_dest + os.sep)):
                        return False
                    
                    validated_members.append((member, member_name, None))
                
                else:
                    return False
            
            for member, member_name, link_target in validated_members:
                extraction_path = os.path.join(abs_dest, member_name)
                extraction_path = os.path.normpath(extraction_path)
                
                try:
                    if member.isdir():
                        os.makedirs(extraction_path, exist_ok=True)
                        mode = member.mode
                        if mode:
                            try:
                                os.chmod(extraction_path, mode)
                            except OSError:
                                pass
                    
                    elif member.isfile():
                        parent_dir = os.path.dirname(extraction_path)
                        if parent_dir:
                            os.makedirs(parent_dir, exist_ok=True)
                        
                        with tf.extractfile(member) as source:
                            if source is None:
                                return False
                            with open(extraction_path, 'wb') as target:
                                while True:
                                    chunk = source.read(65536)
                                    if not chunk:
                                        break
                                    target.write(chunk)
                        
                        mode = member.mode
                        if mode:
                            try:
                                os.chmod(extraction_path, mode)
                            except OSError:
                                pass
                    
                    elif member.issym():
                        parent_dir = os.path.dirname(extraction_path)
                        if parent_dir:
                            os.makedirs(parent_dir, exist_ok=True)
                        
                        os.symlink(member.linkname, extraction_path)
                    
                    elif member.islnk():
                        parent_dir = os.path.dirname(extraction_path)
                        if parent_dir:
                            os.makedirs(parent_dir, exist_ok=True)
                        
                        if os.path.isabs(member.linkname):
                            link_source = member.linkname
                        else:
                            member_dir = os.path.dirname(member_name)
                            if member_dir:
                                combined = os.path.join(member_dir, member.linkname)
                            else:
                                combined = member.linkname
                            link_source = os.path.normpath(combined)
                        
                        if os.path.isabs(link_source):
                            abs_link_source = link_source
                        else:
                            abs_link_source = os.path.join(abs_dest, link_source)
                        
                        abs_link_source = os.path.normpath(abs_link_source)
                        
                        try:
                            os.link(abs_link_source, extraction_path)
                        except OSError:
                            return False
                    
                    else:
                        return False
                
                except (OSError, IOError, tarfile.TarError):
                    return False
            
            return True
    
    except (OSError, IOError, tarfile.TarError):
        return False
