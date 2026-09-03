import os
import tarfile
import errno
import stat


def _normalize_path(path):
    return os.path.normpath(os.path.abspath(path))


def _is_inside(base, path, sep=os.sep):
    return path.startswith(base + sep)


def _get_member_path(base, member_name):
    return _normalize_path(os.path.join(base, member_name))


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    base = _normalize_path(dest_path)
    
    if not os.path.isdir(base):
        return False
    
    try:
        tf = tarfile.open(tar_path, 'r:*')
    except Exception:
        return False
    
    try:
        members = tf.getmembers()
    except Exception:
        tf.close()
        return False
    
    manifest = []
    hard_link_targets = set()
    regular_file_members = set()
    
    for m in members:
        if m.issym() or m.islnk():
            pass
        elif m.isfile():
            regular_file_members.add(_get_member_path(base, m.name))
        elif m.isdir():
            pass
        else:
            pass
    
    for m in members:
        member_path = _get_member_path(base, m.name)
        
        if not _is_inside(base, member_path):
            tf.close()
            return False
        
        if m.isfile():
            member_type = 'file'
        elif m.isdir():
            member_type = 'dir'
        elif m.issym():
            member_type = 'symlink'
        elif m.islnk():
            member_type = 'hardlink'
        else:
            tf.close()
            return False
        
        if member_type == 'symlink':
            raw_target = m.linkname
            if os.path.isabs(raw_target):
                link_target = _normalize_path(raw_target)
            else:
                link_target = _normalize_path(os.path.join(os.path.dirname(member_path), raw_target))
            
            if not _is_inside(base, link_target):
                tf.close()
                return False
        
        elif member_type == 'hardlink':
            link_target = _get_member_path(base, m.linkname)
            
            if not _is_inside(base, link_target):
                tf.close()
                return False
            
            if link_target not in regular_file_members:
                tf.close()
                return False
            
            hard_link_targets.add(link_target)
        
        manifest.append({
            'tarinfo': m,
            'member_path': member_path,
            'member_type': member_type,
        })
    
    for entry in manifest:
        m = entry['tarinfo']
        member_path = entry['member_path']
        member_type = entry['member_type']
        
        parent_dir = os.path.dirname(member_path)
        
        if not _is_inside(base, parent_dir) and parent_dir != base:
            tf.close()
            return False
        
        rel_to_base = os.path.relpath(parent_dir, base)
        current_path = base
        
        if rel_to_base != '.':
            components = rel_to_base.split(os.sep)
            for component in components:
                next_path = os.path.join(current_path, component)
                
                try:
                    st = os.lstat(next_path)
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        try:
                            os.mkdir(next_path)
                        except OSError:
                            tf.close()
                            return False
                        current_path = next_path
                        continue
                    else:
                        tf.close()
                        return False
                
                if stat.S_ISLNK(st.st_mode):
                    tf.close()
                    return False
                
                if not stat.S_ISDIR(st.st_mode):
                    tf.close()
                    return False
                
                current_path = next_path
        
        try:
            if member_type == 'dir':
                try:
                    os.mkdir(member_path)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        tf.close()
                        return False
                    st = os.lstat(member_path)
                    if not stat.S_ISDIR(st.st_mode):
                        tf.close()
                        return False
            
            elif member_type == 'file':
                try:
                    fd = os.open(member_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o666)
                except OSError as e:
                    tf.close()
                    return False
                
                try:
                    f = os.fdopen(fd, 'wb')
                except Exception:
                    os.close(fd)
                    tf.close()
                    return False
                
                try:
                    fileobj = tf.extractfile(m)
                    if fileobj is None:
                        f.close()
                        tf.close()
                        return False
                    
                    while True:
                        chunk = fileobj.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                    
                    fileobj.close()
                except Exception:
                    f.close()
                    tf.close()
                    return False
                
                f.close()
            
            elif member_type == 'symlink':
                try:
                    os.symlink(m.linkname, member_path)
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        try:
                            os.remove(member_path)
                            os.symlink(m.linkname, member_path)
                        except OSError:
                            tf.close()
                            return False
                    else:
                        tf.close()
                        return False
            
            elif member_type == 'hardlink':
                link_target = _get_member_path(base, m.linkname)
                
                try:
                    st = os.lstat(link_target)
                except OSError:
                    tf.close()
                    return False
                
                if stat.S_ISLNK(st.st_mode):
                    tf.close()
                    return False
                
                if not stat.S_ISREG(st.st_mode):
                    tf.close()
                    return False
                
                try:
                    os.link(link_target, member_path)
                except OSError as e:
                    if e.errno == errno.EEXIST:
                        try:
                            os.remove(member_path)
                            os.link(link_target, member_path)
                        except OSError:
                            tf.close()
                            return False
                    else:
                        tf.close()
                        return False
        
        except Exception:
            tf.close()
            return False
    
    tf.close()
    return True
