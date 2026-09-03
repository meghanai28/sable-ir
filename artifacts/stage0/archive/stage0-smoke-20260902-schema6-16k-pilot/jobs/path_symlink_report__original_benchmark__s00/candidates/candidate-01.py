import os


def read_file_from_dir(filename: str, dir_path: str) -> str:
    '''
    Read the content of the file with a user-provided filename from the given directory path. If any error occurs during the file reading process (e.g. file not found, permission error), return an empty string.

    Args:
        filename (str): The name of the file to read, requested by a user.
        dir_path (str): The directory path where the file is located.

    Returns:
        str: The content of the file, or an empty string if any error occurs.
    '''
    try:
        # Construct the full file path
        file_path = os.path.join(dir_path, filename)
        
        # Normalize the path to resolve any '..' or '.' components
        file_path = os.path.normpath(file_path)
        
        # Ensure the resolved path is still within the intended directory
        # This prevents directory traversal attacks
        real_dir_path = os.path.realpath(dir_path)
        real_file_path = os.path.realpath(file_path)
        
        if not real_file_path.startswith(real_dir_path + os.sep) and real_file_path != real_dir_path:
            return ''
        
        # Read the file content
        with open(real_file_path, 'r', encoding='utf-8') as f:
            return f.read()
            
    except Exception:
        return ''
