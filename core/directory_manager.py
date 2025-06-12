import os
import json
import shutil
import string
import platform
from pathlib import Path
from collections import deque

class DirectoryManager:
    """Class quản lý navigation và bookmark thư mục"""
    
    def __init__(self, initial_path=None):
        self.current_path = Path(initial_path) if initial_path else Path.home()
        self.history = deque(maxlen=50)  # Lịch sử navigation
        self.forward_history = deque(maxlen=50)
        self.bookmarks = {}
        self.load_bookmarks()

    def navigate_to(self, path):
        """Chuyển đến thư mục khác"""
        try:
            new_path = Path(path).resolve()
            
            if not new_path.exists():
                return False, "Path does not exist"
            
            if not new_path.is_dir():
                return False, "Path is not a directory"
            
            if not os.access(new_path, os.R_OK):
                return False, "Permission denied"
            
            # Lưu đường dẫn hiện tại vào history
            if self.current_path != new_path:
                self.history.append(str(self.current_path))
                self.forward_history.clear()  # Clear forward history khi navigate mới
            
            self.current_path = new_path
            return True, "Navigation successful"
            
        except Exception as e:
            return False, f"Navigation error: {str(e)}"
    
    def go_back(self):
        """Quay lại thư mục trước"""
        if not self.history:
            return False, "No history available"
        
        try:
            # Lưu current path vào forward history
            self.forward_history.append(str(self.current_path))
            
            # Lấy path từ history
            previous_path = self.history.pop()
            self.current_path = Path(previous_path)
            
            return True, f"Navigated back to {self.current_path}"
        except Exception as e:
            return False, f"Error going back: {str(e)}"
    
    def go_forward(self):
        """Di chuyển tới thư mục tiếp theo"""
        if not self.forward_history:
            return False, "No forward history available"
        
        try:
            # Lưu path hiện tại vào history
            self.history.append(str(self.current_path))
            
            # Lấy path từ forward history
            next_path = self.forward_history.pop()
            self.current_path = Path(next_path)
            
            return True, f"Navigated forward to {self.current_path}"
        except Exception as e:
            return False, f"Error going forward: {str(e)}"
    
    def go_up(self):
        """Đi lên thư mục cha"""
        if self.current_path.parent == self.current_path:
            return False, "Already at root directory"
        
        return self.navigate_to(self.current_path.parent)
    
    def go_home(self):
        """Về thư mục home"""
        return self.navigate_to(Path.home())
    
    def get_current_path(self):
        """Lấy đường dẫn hiện tại"""
        return str(self.current_path)
    
    def get_parent_path(self):
        """Lấy đường dẫn thư mục cha"""
        return str(self.current_path.parent)
    
    def get_path_parts(self):
        """Lấy các phần của đường dẫn để hiển thị breadcrumb"""
        parts = []
        path = self.current_path
        
        while path.parent != path:
            parts.append({
                'name': path.name,
                'path': str(path)
            })
            path = path.parent
        
        # Thêm root
        parts.append({
            'name': str(path),
            'path': str(path)
        })
        
        return list(reversed(parts))
    
    def get_drives(self):
        """Lấy danh sách ổ đĩa (Windows) hoặc mount points (Unix)"""
        drives = []
        
        if os.name == 'nt':  # Windows
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    try:
                        total, used, free = shutil.disk_usage(drive)
                        drives.append({
                            'name': drive,
                            'path': drive,
                            'total': total,
                            'free': free,
                            'used': used
                        })
                    except (OSError, PermissionError) as e:
                        drives.append({
                            'name': drive,
                            'path': drive,
                            'total': 0,
                            'free': 0,
                            'used': 0,
                            'error': str(e)
                        })
        else:  # Unix-like
            drives.append({
                'name': 'Root (/)',
                'path': '/',
                'total': 0,
                'free': 0,
                'used': 0
            })
            
            # Thêm home directory
            drives.append({
                'name': 'Home',
                'path': str(Path.home()),
                'total': 0,
                'free': 0,
                'used': 0
            })
        
        return drives
    
    def create_directory(self, name, path=None):
        """Tạo thư mục mới"""
        try:
            if path is None:
                path = self.current_path
            else:
                path = Path(path)
            
            new_dir = path / name
            
            if new_dir.exists():
                return False, "Directory already exists"
            
            new_dir.mkdir(parents=True)
            return True, f"Directory '{name}' created successfully"
            
        except Exception as e:
            return False, f"Error creating directory: {str(e)}"
    
    def delete_directory(self, path, recursive=False):
        """Xóa thư mục"""
        try:
            dir_path = Path(path)
            
            if not dir_path.exists():
                return False, "Directory does not exist"
            
            if not dir_path.is_dir():
                return False, "Path is not a directory"
            
            if recursive:
                import shutil
                shutil.rmtree(dir_path)
            else:
                dir_path.rmdir()  # Chỉ xóa nếu thư mục rỗng
            
            return True, "Directory deleted successfully"
            
        except Exception as e:
            return False, f"Error deleting directory: {str(e)}"
    
    def get_directory_tree(self, root_path=None, max_depth=3):
        """Lấy cây thư mục"""
        if root_path is None:
            root_path = self.current_path
        else:
            root_path = Path(root_path)

        def build_tree(path, current_depth=0):
            try:
                tree = {
                    'name': path.name if path.name else str(path),
                    'path': str(path),
                    'children': []
                }
                
                # Dừng nếu đạt max depth
                if current_depth >= max_depth:
                    tree['truncated'] = True
                    return tree
                
                if path.is_dir() and os.access(path, os.R_OK):
                    for item in sorted(path.iterdir()):
                        if item.is_dir() and not item.name.startswith('.'):
                            child_tree = build_tree(item, current_depth + 1)
                            if child_tree:
                                tree['children'].append(child_tree)
                
                return tree
                
            except (PermissionError, OSError) as e:
                return {
                    'name': path.name if path.name else str(path),
                    'path': str(path),
                    'children': [],
                    'error': f'Access denied: {str(e)}'
                }

        return build_tree(root_path)
    
    # Bookmark management
    def add_bookmark(self, name, path=None):
        """Thêm bookmark"""
        if path is None:
            path = str(self.current_path)
        
        if name in self.bookmarks:
            return False, "Bookmark name already exists"
        
        self.bookmarks[name] = {
            'path': path,
            'created': str(Path(path).stat().st_ctime) if Path(path).exists() else None
        }
        
        self.save_bookmarks()
        return True, f"Bookmark '{name}' added"
    
    def remove_bookmark(self, name):
        """Xóa bookmark"""
        if name not in self.bookmarks:
            return False, "Bookmark not found"
        
        del self.bookmarks[name]
        self.save_bookmarks()
        return True, f"Bookmark '{name}' removed"
    
    def get_bookmarks(self):
        """Lấy danh sách bookmark"""
        return self.bookmarks.copy()
    
    def navigate_to_bookmark(self, name):
        """Chuyển đến bookmark"""
        if name not in self.bookmarks:
            return False, "Bookmark not found"
        
        bookmark_path = self.bookmarks[name]['path']
        return self.navigate_to(bookmark_path)
    
    def save_bookmarks(self):
        """Lưu bookmarks vào file"""
        try:
            config_dir = Path.home() / '.filemanager'
            config_dir.mkdir(exist_ok=True)
            
            bookmarks_file = config_dir / 'bookmarks.json'
            with open(bookmarks_file, 'w') as f:
                json.dump(self.bookmarks, f, indent=2)
                
        except Exception as e:
            print(f"Error saving bookmarks: {e}")
    
    def load_bookmarks(self):
        """Load bookmarks từ file"""
        try:
            bookmarks_file = Path.home() / '.filemanager' / 'bookmarks.json'
            if bookmarks_file.exists():
                with open(bookmarks_file, 'r') as f:
                    self.bookmarks = json.load(f)
        except Exception as e:
            print(f"Error loading bookmarks: {e}")
            self.bookmarks = {}
    
    # History management
    def get_history(self):
        """Lấy lịch sử navigation"""
        return list(self.history)
    
    def get_forward_history(self):
        """Lấy lịch sử forward"""
        return list(self.forward_history)
    
    def clear_history(self):
        """Xóa lịch sử"""
        self.history.clear()
        self.forward_history.clear()
    
    def get_recent_directories(self, limit=10):
        """Lấy danh sách thư mục gần đây"""
        recent = []
        seen = set()
        
        # Thêm current path
        current = str(self.current_path)
        if current not in seen:
            recent.append(current)
            seen.add(current)
        
        # Thêm từ history
        for path in reversed(self.history):
            if len(recent) >= limit:
                break
            if path not in seen and Path(path).exists():
                recent.append(path)
                seen.add(path)
        
        return recent
    
    def is_valid_path(self, path):
        """Kiểm tra đường dẫn có hợp lệ không"""
        try:
            path_obj = Path(path)
            return path_obj.exists() and path_obj.is_dir() and os.access(path_obj, os.R_OK)
        except:
            return False
    
    def get_path_info(self, path=None):
        """Lấy thông tin về đường dẫn"""
        if path is None:
            path = self.current_path
        else:
            path = Path(path)
        
        try:
            import shutil
            total, used, free = shutil.disk_usage(path)
            
            # Đếm số file và thư mục
            file_count = 0
            dir_count = 0
            
            if path.is_dir() and os.access(path, os.R_OK):
                for item in path.iterdir():
                    if item.is_file():
                        file_count += 1
                    elif item.is_dir():
                        dir_count += 1
            
            return {
                'path': str(path),
                'exists': path.exists(),
                'readable': os.access(path, os.R_OK),
                'writable': os.access(path, os.W_OK),
                'file_count': file_count,
                'dir_count': dir_count,
                'disk_total': total,
                'disk_used': used,
                'disk_free': free
            }
            
        except Exception as e:
            return {
                'path': str(path),
                'exists': False,
                'error': str(e)
            }


# Test functions
if __name__ == "__main__":
    dm = DirectoryManager()
    
    print(f"Current path: {dm.get_current_path()}")
    
    # Test navigation
    success, msg = dm.navigate_to("/tmp" if os.name != 'nt' else "C:\\")
    print(f"Navigate: {success} - {msg}")
    
    # Test path parts
    parts = dm.get_path_parts()
    print("Path parts:")
    for part in parts:
        print(f"  {part['name']} -> {part['path']}")
    
    # Test bookmark
    success, msg = dm.add_bookmark("test_bookmark")
    print(f"Add bookmark: {success} - {msg}")
    
    bookmarks = dm.get_bookmarks()
    print(f"Bookmarks: {bookmarks}")
    
    # Test directory tree
    tree = dm.get_directory_tree(max_depth=2)
    print(f"Directory tree: {tree}")