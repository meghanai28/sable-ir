import os
import tarfile
import tempfile
import secrets
import hashlib
from pathlib import Path


class SessionManager:
    def __init__(self):
        self._session_id = None
        self._privilege_level = None
        self._csrf_token = None
    
    def create_fresh_session(self):
        self._session_id = secrets.token_urlsafe(32)
        self._privilege_level = 'none'
        self._csrf_token = secrets.token_urlsafe(32)
        return self._session_id
    
    def rotate_identifier(self):
        old_session = self._session_id
        self._session_id = secrets.token_urlsafe(32)
        return self._session_id
    
    def elevate_privilege(self, new_level):
        self._privilege_level = new_level
        self.rotate_identifier()
    
    def get_session_cookie(self):
        if self._session_id is None:
            return None
        cookie_value = hashlib.sha256(self._session_id.encode()).hexdigest()
        return {
            'name': 'session_id',
            'value': cookie_value,
            'secure': True,
            'httponly': True,
            'samesite': 'Strict'
        }


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    session_manager = SessionManager()
    session_manager.create_fresh_session()
    
    try:
        base_path = Path(dest_path).resolve()
        base_path.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError):
        return False
    
    validated_entries = []
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            
            for member in members:
                if member.issym() or member.islnk():
                    return False
                
                member_path = Path(member.name)
                try:
                    resolved_path = (base_path / member_path).resolve()
                except (ValueError, OSError):
                    return False
                
                try:
                    resolved_path.relative_to(base_path)
                except ValueError:
                    return False
                
                if member.isfile() or member.isdir():
                    validated_entries.append((member, resolved_path))
                else:
                    return False
            
            session_manager.elevate_privilege('extraction')
            
            for member, resolved_path in validated_entries:
                try:
                    if member.isdir():
                        resolved_path.mkdir(parents=True, exist_ok=True)
                    elif member.isfile():
                        resolved_path.parent.mkdir(parents=True, exist_ok=True)
                        with tf.extractfile(member) as source:
                            if source is None:
                                return False
                            with open(resolved_path, 'wb') as target:
                                while True:
                                    chunk = source.read(65536)
                                    if not chunk:
                                        break
                                    target.write(chunk)
                except (OSError, IOError, tarfile.TarError):
                    return False
            
            session_manager.rotate_identifier()
            return True
            
    except (tarfile.TarError, OSError, IOError):
        return False
