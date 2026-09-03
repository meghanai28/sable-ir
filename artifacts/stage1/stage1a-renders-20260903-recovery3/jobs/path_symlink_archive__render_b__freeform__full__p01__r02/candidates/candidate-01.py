import os
import tarfile
import errno
import fcntl

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        os.makedirs(dest_path, exist_ok=True)
    except OSError:
        return False
    
    try:
        real_dest = os.path.realpath(dest_path)
    except OSError:
        return False
    
    if not os.path.isdir(real_dest):
        return False
    
    real_dest = os.path.abspath(real_dest)
    if not real_dest.endswith(os.sep):
        real_dest += os.sep
    
    try:
        tf = tarfile.open(tar_path, 'r:*')
    except (tarfile.TarError, OSError, IOError):
        return False
    
    members = tf.getmembers()
    
    validated_members = []
    validated_symlink_targets = {}
    validated_hardlink_targets = {}
    
    for member in members:
        if member.name.startswith('/') or member.name.startswith(os.sep):
            tf.close()
            return False
        
        member_path = os.path.join(real_dest, member.name)
        norm_path = os.path.normpath(member_path)
        abs_path = os.path.abspath(norm_path)
        
        if not abs_path.startswith(real_dest):
            tf.close()
            return False
        
        if member.issym() or member.islnk():
            pass
        elif member.isdir() or member.isfile() or member.ischr() or member.isblk() or member.isfifo():
            pass
        else:
            tf.close()
            return False
        
        if member.issym():
            link_target = member.linkname
            
            if os.path.isabs(link_target):
                norm_target = os.path.normpath(link_target)
                abs_target = os.path.abspath(norm_target)
            else:
                parent_dir = os.path.dirname(abs_path)
                resolved = os.path.join(parent_dir, link_target)
                norm_target = os.path.normpath(resolved)
                abs_target = os.path.abspath(norm_target)
            
            if not abs_target.startswith(real_dest):
                tf.close()
                return False
            
            validated_symlink_targets[member.name] = link_target
        
        if member.islnk():
            link_target = member.linkname
            
            if os.path.isabs(link_target):
                norm_target = os.path.normpath(link_target)
                abs_target = os.path.abspath(norm_target)
            else:
                hl_target_path = os.path.join(real_dest, link_target)
                norm_target = os.path.normpath(hl_target_path)
                abs_target = os.path.abspath(norm_target)
            
            if not abs_target.startswith(real_dest):
                tf.close()
                return False
            
            try:
                if os.path.lexists(abs_target) and not abs_target.startswith(real_dest):
                    tf.close()
                    return False
            except OSError:
                pass
            
            validated_hardlink_targets[member.name] = member.linkname
        
        if member.ischr() or member.isblk() or member.isfifo():
            tf.close()
            return False
        
        validated_members.append(member)
    
    try:
        dest_fd = os.open(real_dest, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        tf.close()
        return False
    
    try:
        for member in validated_members:
            member_path = os.path.join(real_dest, member.name)
            norm_path = os.path.normpath(member_path)
            abs_path = os.path.abspath(norm_path)
            
            rel_path = member.name
            path_parts = rel_path.replace('/', os.sep).split(os.sep)
            
            if path_parts[-1] == '':
                path_parts = path_parts[:-1]
            
            if not path_parts or path_parts == ['.']:
                continue
            
            current_fd = dest_fd
            
            try:
                for i, part in enumerate(path_parts[:-1]):
                    if part == '.' or part == '':
                        continue
                    if part == '..':
                        os.close(current_fd)
                        tf.close()
                        return False
                    
                    try:
                        new_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current_fd)
                        if i < len(path_parts) - 2 or not member.isdir():
                            pass
                        os.close(current_fd)
                        current_fd = new_fd
                    except OSError as e:
                        if e.errno == errno.ENOENT:
                            try:
                                os.mkdir(part, dir_fd=current_fd)
                                new_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current_fd)
                                os.close(current_fd)
                                current_fd = new_fd
                            except OSError:
                                os.close(current_fd)
                                tf.close()
                                return False
                        elif e.errno == errno.ENOTDIR:
                            os.close(current_fd)
                            tf.close()
                            return False
                        else:
                            os.close(current_fd)
                            tf.close()
                            return False
                
                final_part = path_parts[-1]
                
                if member.isdir():
                    if final_part == '.' or final_part == '':
                        os.close(current_fd)
                        continue
                    if final_part == '..':
                        os.close(current_fd)
                        tf.close()
                        return False
                    
                    try:
                        os.mkdir(final_part, dir_fd=current_fd)
                    except OSError as e:
                        if e.errno != errno.EEXIST:
                            os.close(current_fd)
                            tf.close()
                            return False
                        try:
                            stat_info = os.lstat(final_part, dir_fd=current_fd)
                            if not os.path.isdir(stat_info):
                                os.close(current_fd)
                                tf.close()
                                return False
                        except OSError:
                            os.close(current_fd)
                            tf.close()
                            return False
                    
                    os.close(current_fd)
                
                elif member.isfile():
                    if final_part == '.' or final_part == '' or final_part == '..':
                        os.close(current_fd)
                        tf.close()
                        return False
                    
                    try:
                        file_fd = os.open(final_part, os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW | os.O_EXCL, 0o666, dir_fd=current_fd)
                    except OSError as e:
                        os.close(current_fd)
                        tf.close()
                        return False
                    
                    try:
                        f = os.fdopen(file_fd, 'wb')
                        try:
                            file_obj = tf.extractfile(member)
                            if file_obj is None:
                                f.close()
                                os.close(current_fd)
                                tf.close()
                                return False
                            while True:
                                chunk = file_obj.read(65536)
                                if not chunk:
                                    break
                                f.write(chunk)
                        finally:
                            f.close()
                    except (OSError, IOError):
                        try:
                            os.close(file_fd)
                        except OSError:
                            pass
                        os.close(current_fd)
                        tf.close()
                        return False
                    
                    try:
                        os.utime(final_part, ns=(member.mtime * 1000000000, member.mtime * 1000000000), dir_fd=current_fd, follow_symlinks=False)
                    except OSError:
                        pass
                    
                    try:
                        os.chmod(final_part, member.mode, dir_fd=current_fd)
                    except OSError:
                        pass
                    
                    os.close(current_fd)
                
                elif member.issym():
                    if final_part == '.' or final_part == '' or final_part == '..':
                        os.close(current_fd)
                        tf.close()
                        return False
                    
                    target = validated_symlink_targets[member.name]
                    
                    try:
                        os.symlink(target, final_part, dir_fd=current_fd)
                    except OSError as e:
                        if e.errno != errno.EEXIST:
                            os.close(current_fd)
                            tf.close()
                            return False
                        try:
                            os.unlink(final_part, dir_fd=current_fd)
                            os.symlink(target, final_part, dir_fd=current_fd)
                        except OSError:
                            os.close(current_fd)
                            tf.close()
                            return False
                    
                    os.close(current_fd)
                
                elif member.islnk():
                    if final_part == '.' or final_part == '' or final_part == '..':
                        os.close(current_fd)
                        tf.close()
                        return False
                    
                    source = validated_hardlink_targets[member.name]
                    
                    source_path = os.path.join(real_dest, source)
                    source_norm = os.path.normpath(source_path)
                    source_abs = os.path.abspath(source_norm)
                    
                    if not source_abs.startswith(real_dest):
                        os.close(current_fd)
                        tf.close()
                        return False
                    
                    source_rel = source
                    source_parts = source_rel.replace('/', os.sep).split(os.sep)
                    
                    source_fd = dest_fd
                    try:
                        for j, spart in enumerate(source_parts[:-1]):
                            if spart == '.' or spart == '':
                                continue
                            if spart == '..':
                                os.close(source_fd)
                                os.close(current_fd)
                                tf.close()
                                return False
                            
                            try:
                                new_sfd = os.open(spart, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=source_fd)
                                if j > 0:
                                    pass
                                if source_fd != dest_fd:
                                    os.close(source_fd)
                                source_fd = new_sfd
                            except OSError:
                                if source_fd != dest_fd:
                                    os.close(source_fd)
                                os.close(current_fd)
                                tf.close()
                                return False
                        
                        source_final = source_parts[-1]
                        
                        try:
                            os.link(source_final, final_part, src_dir_fd=source_fd, dst_dir_fd=current_fd, follow_symlinks=False)
                        except OSError as e:
                            if source_fd != dest_fd:
                                os.close(source_fd)
                            os.close(current_fd)
                            tf.close()
                            return False
                        
                        if source_fd != dest_fd:
                            os.close(source_fd)
                        
                    except Exception:
                        if source_fd != dest_fd:
                            try:
                                os.close(source_fd)
                            except OSError:
                                pass
                        os.close(current_fd)
                        tf.close()
                        return False
                    
                    os.close(current_fd)
                
                else:
                    os.close(current_fd)
                    tf.close()
                    return False
            
            except Exception:
                try:
                    os.close(current_fd)
                except OSError:
                    pass
                tf.close()
                return False
    
    except Exception:
        try:
            os.close(dest_fd)
        except OSError:
            pass
        tf.close()
        return False
    
    try:
        os.close(dest_fd)
    except OSError:
        pass
    
    tf.close()
    return True
