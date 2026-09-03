import os

def read_report(filename: str, reports_root: str) -> str:
    reports_root = os.path.abspath(reports_root)
    target_path = os.path.abspath(os.path.join(reports_root, filename))
    normalized_target = os.path.normpath(target_path)
    
    if not normalized_target.startswith(reports_root + os.sep) and normalized_target != reports_root:
        raise ValueError("Request disallowed: path escapes reports_root")
    
    current_path = reports_root
    remaining = filename
    
    while remaining:
        remaining = os.path.normpath(remaining)
        if remaining == '.':
            break
        head, tail = os.path.split(remaining)
        if head == remaining:
            break
        
        parts = []
        temp = remaining
        while True:
            temp_head, temp_tail = os.path.split(temp)
            if temp_head == temp:
                if temp_tail:
                    parts.append(temp_tail)
                elif temp_head and temp_head != os.sep:
                    parts.append(temp_head)
                break
            if not temp_tail and temp_head:
                temp = temp_head
                continue
            parts.append(temp_tail)
            if not temp_head or temp_head == os.sep:
                if temp_head == os.sep:
                    parts.append(os.sep)
                break
            temp = temp_head
        
        parts.reverse()
        
        for part in parts:
            if part == os.sep:
                continue
            current_path = os.path.join(current_path, part)
            current_path = os.path.normpath(current_path)
            if os.path.islink(current_path):
                raise ValueError("Request disallowed: symbolic link encountered")
        
        break
    
    with open(normalized_target, 'r', encoding='utf-8') as f:
        return f.read()
