import os
import tarfile
import tempfile
import shutil

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.realpath(dest_path))
        
        if not os.path.exists(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        
        if not os.path.isdir(dest_path):
            return False
        
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            for member in members:
                member_path = member.name
                
                if os.path.isabs(member_path):
                    member_path = member_path.lstrip('/')
                    if not member_path:
                        continue
                
                member_path = os.path.normpath(member_path)
                
                if member_path.startswith('..') or '/../' in member_path or member_path.endswith('/..'):
                    return False
                
                full_extract_path = os.path.join(dest_path, member_path)
                full_extract_path = os.path.abspath(os.path.realpath(full_extract_path))
                
                if not full_extract_path.startswith(dest_path + os.sep) and full_extract_path != dest_path:
                    return False
            
            temp_dir = tempfile.mkdtemp(prefix='tar_extract_')
            try:
                for member in members:
                    member_path = member.name
                    
                    if os.path.isabs(member_path):
                        member_path = member_path.lstrip('/')
                        if not member_path:
                            continue
                    
                    member_path = os.path.normpath(member_path)
                    
                    if member_path.startswith('..') or '/../' in member_path or member_path.endswith('/..'):
                        return False
                    
                    full_extract_path = os.path.join(dest_path, member_path)
                    full_extract_path = os.path.abspath(os.path.realpath(full_extract_path))
                    
                    if not full_extract_path.startswith(dest_path + os.sep) and full_extract_path != dest_path:
                        return False
                
                tf.extractall(path=temp_dir)
                
                for root, dirs, files in os.walk(temp_dir):
                    for name in dirs + files:
                        item_path = os.path.join(root, name)
                        rel_path = os.path.relpath(item_path, temp_dir)
                        rel_path = os.path.normpath(rel_path)
                        
                        full_dest_path = os.path.join(dest_path, rel_path)
                        full_dest_path = os.path.abspath(os.path.realpath(full_dest_path))
                        
                        if not full_dest_path.startswith(dest_path + os.sep) and full_dest_path != dest_path:
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            return False
                
                for root, dirs, files in os.walk(temp_dir):
                    for name in dirs + files:
                        item_path = os.path.join(root, name)
                        rel_path = os.path.relpath(item_path, temp_dir)
                        rel_path = os.path.normpath(rel_path)
                        
                        full_dest_path = os.path.join(dest_path, rel_path)
                        full_dest_path = os.path.abspath(os.path.realpath(full_dest_path))
                        
                        if not full_dest_path.startswith(dest_path + os.sep) and full_dest_path != dest_path:
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            return False
                
                for root, dirs, files in os.walk(temp_dir):
                    for name in files:
                        item_path = os.path.join(root, name)
                        rel_path = os.path.relpath(item_path, temp_dir)
                        rel_path = os.path.normpath(rel_path)
                        
                        full_dest_path = os.path.join(dest_path, rel_path)
                        
                        dest_dir = os.path.dirname(full_dest_path)
                        if not os.path.exists(dest_dir):
                            os.makedirs(dest_dir, exist_ok=True)
                        
                        if os.path.exists(full_dest_path):
                            if os.path.isdir(full_dest_path):
                                shutil.rmtree(full_dest_path)
                            else:
                                os.remove(full_dest_path)
                        
                        shutil.move(item_path, full_dest_path)
                    
                    for name in dirs:
                        item_path = os.path.join(root, name)
                        rel_path = os.path.relpath(item_path, temp_dir)
                        rel_path = os.path.normpath(rel_path)
                        
                        full_dest_path = os.path.join(dest_path, rel_path)
                        
                        if not os.path.exists(full_dest_path):
                            os.makedirs(full_dest_path, exist_ok=True)
                
                shutil.rmtree(temp_dir, ignore_errors=True)
                
            except Exception:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False
        
        return True
    
    except Exception:
        return False
