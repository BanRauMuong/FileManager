import os
import shutil
import stat
import locale
from pathlib import Path
from datetime import datetime
import mimetypes
import hashlib

class FileOperations:
    """Class xử lý các thao tác file cơ bản"""
    
    def __init__(self):
        self.clipboard = None
        self.clipboard_action = None
        self.default_encoding = locale.getpreferredencoding()
    
    def create_file(self, path, content="", encoding=None):
        """Tạo file mới với encoding detection"""
        try:
            if encoding is None:
                encoding = self.default_encoding
                
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            return True, "File created successfully"
        except Exception as e:
            return False, f"Error creating file: {str(e)}"
    
    def read_file(self, path, encoding="utf-8", binary=False):
        """Đọc nội dung file"""
        try:
            file_path = Path(path)
            if not file_path.exists():
                return False, "File not found", None
            
            if binary:
                with open(file_path, 'rb') as f:
                    content = f.read()
            else:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
            
            return True, "File read successfully", content
        except Exception as e:
            return False, f"Error reading file: {str(e)}", None
    
    def write_file(self, path, content, mode="w", encoding="utf-8"):
        """Ghi nội dung vào file"""
        try:
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if 'b' in mode:
                with open(file_path, mode) as f:
                    f.write(content)
            else:
                with open(file_path, mode, encoding=encoding) as f:
                    f.write(content)
            
            return True, "File written successfully"
        except Exception as e:
            return False, f"Error writing file: {str(e)}"
    
    def delete_file(self, path):
        """Xóa file hoặc thư mục"""
        try:
            file_path = Path(path)
            if not file_path.exists():
                return False, "File/directory not found"
            
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir():
                shutil.rmtree(file_path)
            
            return True, "Deleted successfully"
        except Exception as e:
            return False, f"Error deleting: {str(e)}"
    
    def copy_file(self, source, destination):
        """Sao chép file hoặc thư mục"""
        try:
            src_path = Path(source)
            dest_path = Path(destination)
            
            if not src_path.exists():
                return False, "Source not found"
            
            # Tạo thư mục đích nếu chưa tồn tại
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            if src_path.is_file():
                shutil.copy2(src_path, dest_path)
            elif src_path.is_dir():
                shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
            
            return True, "Copied successfully"
        except Exception as e:
            return False, f"Error copying: {str(e)}"
    
    def move_file(self, source, destination):
        """Di chuyển file hoặc thư mục"""
        try:
            src_path = Path(source)
            dest_path = Path(destination)
            
            if not src_path.exists():
                return False, "Source not found"
            
            # Tạo thư mục đích nếu chưa tồn tại
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(src_path), str(dest_path))
            return True, "Moved successfully"
        except Exception as e:
            return False, f"Error moving: {str(e)}"
    
    def rename_file(self, old_path, new_name):
        """Đổi tên file hoặc thư mục"""
        try:
            old_file = Path(old_path)
            if not old_file.exists():
                return False, "File not found"
            
            new_file = old_file.parent / new_name
            if new_file.exists():
                return False, "File with new name already exists"
            
            old_file.rename(new_file)
            return True, "Renamed successfully"
        except Exception as e:
            return False, f"Error renaming: {str(e)}"
    
    def get_file_info(self, path):
        """Lấy thông tin chi tiết của file"""
        try:
            file_path = Path(path)
            if not file_path.exists():
                return None
            
            stat_info = file_path.stat()
            
            info = {
                'name': file_path.name,
                'path': str(file_path.absolute()),
                'size': stat_info.st_size,
                'size_formatted': self.format_size(stat_info.st_size),
                'type': 'Directory' if file_path.is_dir() else 'File',
                'extension': file_path.suffix if file_path.is_file() else '',
                'mime_type': mimetypes.guess_type(str(file_path))[0] if file_path.is_file() else None,
                'created': datetime.fromtimestamp(stat_info.st_ctime),
                'modified': datetime.fromtimestamp(stat_info.st_mtime),
                'accessed': datetime.fromtimestamp(stat_info.st_atime),
                'permissions': oct(stat_info.st_mode)[-3:],
                'is_readable': os.access(file_path, os.R_OK),
                'is_writable': os.access(file_path, os.W_OK),
                'is_executable': os.access(file_path, os.X_OK),
                'is_hidden': file_path.name.startswith('.') or bool(stat_info.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN) if os.name == 'nt' else file_path.name.startswith('.')
            }
            
            # Thêm hash cho file nhỏ
            if file_path.is_file() and stat_info.st_size < 10 * 1024 * 1024:  # < 10MB
                info['md5'] = self.get_file_hash(file_path, 'md5')
            
            return info
        except Exception as e:
            return None
    
    def _is_hidden_file(self, file_path: Path) -> bool:
        """Kiểm tra file ẩn cross-platform"""
        if file_path.name.startswith('.'):
            return True

        if os.name == 'nt':  # Windows
            try:
                attrs = os.stat(file_path).st_file_attributes
                return bool(attrs & stat.FILE_ATTRIBUTE_HIDDEN)
            except (AttributeError, OSError):
                return False

        return False

    def get_file_hash(self, file_path, algorithm='md5'):
        """Tính hash của file"""
        try:
            hash_obj = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception:
            return None
    
    def format_size(self, size_bytes):
        """Format kích thước file"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def get_directory_size(self, path, max_depth=10):
        """Tính tổng kích thước của thư mục với depth limit"""
        try:
            total_size = 0

            for root, dirs, files in os.walk(path):
                # Tính depth hiện tại
                level = os.path.relpath(root, path).count(os.sep)
                if level >= max_depth:
                    dirs[:] = []  # Ngừng đi sâu hơn
                    continue

                for filename in files:
                    file_path = os.path.join(root, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except (OSError, FileNotFoundError):
                        continue
            return total_size
        except Exception:
            return 0
    
    def create_directory(self, path):
        """Tạo thư mục mới"""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True, "Directory created successfully"
        except Exception as e:
            return False, f"Error creating directory: {str(e)}"
    
    def list_directory(self, path, show_hidden=False, sort_by='name', reverse=False):
        """Liệt kê nội dung thư mục với error handling tốt hơn"""
        try:
            dir_path = Path(path)
            if not dir_path.exists() or not dir_path.is_dir():
                return False, "Directory not found", []
            
            items = []
            for item in dir_path.iterdir():
                try:
                    # Skip hidden files if requested
                    if not show_hidden and self._is_hidden_file(item):
                        continue
                    
                    stat_info = item.stat()
                    item_info = {
                        'name': item.name,
                        'path': str(item),
                        'is_dir': item.is_dir(),
                        'size': stat_info.st_size if item.is_file() else 0,  # Don't calculate dir size here
                        'modified': stat_info.st_mtime,
                        'extension': item.suffix.lower() if item.is_file() else '',
                        'permissions': oct(stat_info.st_mode)[-3:],
                        'is_readable': os.access(item, os.R_OK),
                        'is_writable': os.access(item, os.W_OK)
                    }
                    items.append(item_info)
                    
                except (OSError, PermissionError) as e:
                    # Add error entry for inaccessible items
                    items.append({
                        'name': item.name,
                        'path': str(item),
                        'is_dir': item.is_dir(),
                        'size': 0,
                        'modified': 0,
                        'extension': '',
                        'error': str(e)
                    })
            
            # Sắp xếp
            if sort_by == 'name':
                items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()), reverse=reverse)
            elif sort_by == 'size':
                items.sort(key=lambda x: (not x['is_dir'], x['size']), reverse=reverse)
            elif sort_by == 'date':
                items.sort(key=lambda x: (not x['is_dir'], x['modified']), reverse=reverse)
            elif sort_by == 'type':
                items.sort(key=lambda x: (not x['is_dir'], x['extension']), reverse=reverse)
            
            return True, "Directory listed successfully", items
        except Exception as e:
            return False, f"Error listing directory: {str(e)}", []
    
    def search_files(self, root_path, pattern="*", search_content="", file_types=None, 
                    min_size=None, max_size=None, date_from=None, date_to=None):
        """Tìm kiếm file"""
        try:
            from fnmatch import fnmatch
            results = []
            
            for root, dirs, files in os.walk(root_path):
                for file in files:
                    file_path = Path(root) / file
                    
                    try:
                        # Kiểm tra pattern tên file
                        if pattern != "*" and not fnmatch(file.lower(), pattern.lower()):
                            continue
                        
                        stat_info = file_path.stat()
                        
                        # Kiểm tra loại file
                        if file_types and file_path.suffix.lower() not in [f.lower() for f in file_types]:
                            continue
                        
                        # Kiểm tra kích thước
                        if min_size and stat_info.st_size < min_size:
                            continue
                        if max_size and stat_info.st_size > max_size:
                            continue
                        
                        # Kiểm tra ngày
                        if date_from and datetime.fromtimestamp(stat_info.st_mtime) < date_from:
                            continue
                        if date_to and datetime.fromtimestamp(stat_info.st_mtime) > date_to:
                            continue
                        
                        # Tìm kiếm nội dung file (chỉ với file text)
                        if search_content:
                            try:
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
                                    if search_content.lower() not in content.lower():
                                        continue
                            except:
                                continue
                        
                        results.append({
                            'name': file,
                            'path': str(file_path),
                            'size': stat_info.st_size,
                            'modified': datetime.fromtimestamp(stat_info.st_mtime)
                        })
                        
                    except (OSError, PermissionError):
                        continue
            
            return True, f"Found {len(results)} files", results
        except Exception as e:
            return False, f"Search error: {str(e)}", []
    
    def set_clipboard(self, path, action='copy'):
        """Đặt file vào clipboard"""
        self.clipboard = path
        self.clipboard_action = action
    
    def get_clipboard(self):
        """Lấy file từ clipboard"""
        return self.clipboard, self.clipboard_action
    
    def clear_clipboard(self):
        """Xóa clipboard"""
        self.clipboard = None
        self.clipboard_action = None


# Test functions
if __name__ == "__main__":
    file_ops = FileOperations()
    
    # Test tạo file
    success, msg = file_ops.create_file("test/sample.txt", "Hello World!")
    print(f"Create file: {success} - {msg}")
    
    # Test đọc file
    success, msg, content = file_ops.read_file("test/sample.txt")
    print(f"Read file: {success} - {msg}")
    if success:
        print(f"Content: {content}")
    
    # Test thông tin file
    info = file_ops.get_file_info("test/sample.txt")
    if info:
        print(f"File info: {info}")
    
    # Test list directory
    success, msg, items = file_ops.list_directory(".")
    print(f"List directory: {success} - {msg}")
    for item in items[:5]:  # Hiển thị 5 item đầu
        print(f"  {item['name']} - {'DIR' if item['is_dir'] else 'FILE'}")