import os
import shutil
import hashlib
import mimetypes
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Union, Generator, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
import tempfile
import magic  # python-magic để detect file type chính xác hơn
import psutil  # để monitor disk usage


class HashAlgorithm(Enum):
    """Enum cho các thuật toán hash được hỗ trợ"""
    MD5 = 'md5'
    SHA1 = 'sha1'
    SHA256 = 'sha256'
    SHA512 = 'sha512'


@dataclass
class FileInfo:
    """Dataclass để lưu thông tin file một cách có cấu trúc"""
    name: str
    path: str
    size: int
    size_formatted: str
    modified: datetime
    created: datetime
    accessed: datetime
    is_directory: bool
    extension: str
    mime_type: Optional[str]
    permissions: str
    is_hidden: bool
    is_symlink: bool
    owner: Optional[str] = None
    group: Optional[str] = None
    inode: Optional[int] = None


class FileUtils:
    """Lớp tiện ích để xử lý các thao tác với file - Phiên bản cải tiến"""
    
    # Cache cho mime types để tăng hiệu suất
    _mime_cache: Dict[str, str] = {}
    
    # Logger
    logger = logging.getLogger(__name__)
    
    @staticmethod
    def get_file_info(file_path: Union[str, Path], 
                     include_hash: bool = False,
                     hash_algorithm: HashAlgorithm = HashAlgorithm.MD5) -> Optional[FileInfo]:
        """
        Lấy thông tin chi tiết của file với nhiều tùy chọn hơn
        
        Args:
            file_path: Đường dẫn đến file
            include_hash: Có tính hash không (chậm với file lớn)
            hash_algorithm: Thuật toán hash sử dụng
            
        Returns:
            FileInfo object hoặc None nếu có lỗi
        """
        try:
            path = Path(file_path)
            if not path.exists():
                FileUtils.logger.warning(f"File không tồn tại: {file_path}")
                return None
                
            stat = path.stat()
            
            # Detect mime type chính xác hơn
            mime_type = FileUtils._get_mime_type(str(path))
            
            # Lấy thông tin owner (chỉ trên Unix)
            owner = None
            group = None
            try:
                import pwd
                import grp
                owner = pwd.getpwuid(stat.st_uid).pw_name
                group = grp.getgrgid(stat.st_gid).gr_name
            except (ImportError, KeyError):
                pass
            
            file_info = FileInfo(
                name=path.name,
                path=str(path.absolute()),
                size=stat.st_size,
                size_formatted=FileUtils.format_file_size(stat.st_size),
                modified=datetime.fromtimestamp(stat.st_mtime),
                created=datetime.fromtimestamp(stat.st_ctime),
                accessed=datetime.fromtimestamp(stat.st_atime),
                is_directory=path.is_dir(),
                extension=path.suffix.lower(),
                mime_type=mime_type,
                permissions=oct(stat.st_mode)[-3:],
                is_hidden=path.name.startswith('.'),
                is_symlink=path.is_symlink(),
                owner=owner,
                group=group,
                inode=stat.st_ino
            )
            
            return file_info
            
        except Exception as e:
            FileUtils.logger.error(f"Lỗi khi lấy thông tin file {file_path}: {e}")
            return None
    
    @staticmethod
    def _get_mime_type(file_path: str) -> Optional[str]:
        """Lấy mime type với cache để tăng hiệu suất"""
        if file_path in FileUtils._mime_cache:
            return FileUtils._mime_cache[file_path]
        
        try:
            # Sử dụng python-magic để detect chính xác hơn
            mime_type = magic.from_file(file_path, mime=True)
            FileUtils._mime_cache[file_path] = mime_type
            return mime_type
        except:
            # Fallback về mimetypes standard
            mime_type = mimetypes.guess_type(file_path)[0]
            FileUtils._mime_cache[file_path] = mime_type
            return mime_type
    
    @staticmethod
    def format_file_size(size_bytes: int, binary: bool = True) -> str:
        """
        Định dạng kích thước file với tùy chọn binary (1024) hoặc decimal (1000)
        
        Args:
            size_bytes: Kích thước tính bằng bytes
            binary: True để dùng 1024, False để dùng 1000
        """
        if size_bytes == 0:
            return "0 B"
        
        if binary:
            size_names = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
            base = 1024
        else:
            size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
            base = 1000
        
        i = 0
        size = float(size_bytes)
        while size >= base and i < len(size_names) - 1:
            size /= base
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
    
    @staticmethod
    def get_file_hash(file_path: Union[str, Path], 
                     algorithm: HashAlgorithm = HashAlgorithm.MD5,
                     chunk_size: int = 8192,
                     progress_callback: Optional[Callable[[int, int], None]] = None) -> Optional[str]:
        """
        Tính hash của file với progress callback và chunk size tùy chỉnh
        
        Args:
            file_path: Đường dẫn file
            algorithm: Thuật toán hash
            chunk_size: Kích thước chunk để đọc
            progress_callback: Callback function(bytes_read, total_size)
        """
        try:
            path = Path(file_path)
            if not path.exists() or path.is_dir():
                return None
                
            hash_obj = hashlib.new(algorithm.value)
            total_size = path.stat().st_size
            bytes_read = 0
            
            with open(path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    hash_obj.update(chunk)
                    bytes_read += len(chunk)
                    
                    if progress_callback:
                        progress_callback(bytes_read, total_size)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            FileUtils.logger.error(f"Lỗi khi tính hash file {file_path}: {e}")
            return None
    
    @staticmethod
    def is_safe_path(base_path: Union[str, Path], 
                    target_path: Union[str, Path]) -> bool:
        """Kiểm tra đường dẫn có an toàn không (tránh path traversal)"""
        try:
            base = Path(base_path).resolve()
            target = Path(target_path).resolve()
            
            # Kiểm tra target có nằm trong base không
            try:
                target.relative_to(base)
                return True
            except ValueError:
                return False
                
        except Exception as e:
            FileUtils.logger.error(f"Lỗi khi kiểm tra safe path: {e}")
            return False
    
    @staticmethod
    def get_duplicate_files(directory: Union[str, Path],
                          recursive: bool = True,
                          min_size: int = 0,
                          extensions: Optional[List[str]] = None,
                          max_workers: int = 4,
                          progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, List[str]]:
        """
        Tìm các file trùng lặp với nhiều tùy chọn hơn và multi-threading
        
        Args:
            directory: Thư mục để tìm
            recursive: Tìm kiếm đệ quy
            min_size: Kích thước file tối thiểu
            extensions: Danh sách extension cần tìm
            max_workers: Số thread tối đa
            progress_callback: Callback khi xử lý file
        """
        files_to_check = []
        
        # Thu thập danh sách file
        if recursive:
            for file_path in Path(directory).rglob('*'):
                if FileUtils._should_check_file(file_path, min_size, extensions):
                    files_to_check.append(file_path)
        else:
            for file_path in Path(directory).iterdir():
                if FileUtils._should_check_file(file_path, min_size, extensions):
                    files_to_check.append(file_path)
        
        # Tính hash song song
        hash_map = {}
        duplicates = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit tất cả tasks
            future_to_file = {
                executor.submit(FileUtils.get_file_hash, file_path): file_path 
                for file_path in files_to_check
            }
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                
                if progress_callback:
                    progress_callback(str(file_path))
                
                try:
                    file_hash = future.result()
                    if file_hash:
                        if file_hash in hash_map:
                            if file_hash not in duplicates:
                                duplicates[file_hash] = [str(hash_map[file_hash])]
                            duplicates[file_hash].append(str(file_path))
                        else:
                            hash_map[file_hash] = file_path
                except Exception as e:
                    FileUtils.logger.error(f"Lỗi khi xử lý file {file_path}: {e}")
                    continue
        
        return duplicates
    
    @staticmethod
    def _should_check_file(file_path: Path, min_size: int, extensions: Optional[List[str]]) -> bool:
        """Kiểm tra file có nên được check không"""
        if not file_path.is_file():
            return False
        
        try:
            if file_path.stat().st_size < min_size:
                return False
        except OSError:
            return False
        
        if extensions:
            if file_path.suffix.lower() not in [ext.lower() for ext in extensions]:
                return False
        
        return True
    
    @staticmethod
    def clean_filename(filename: str, replacement: str = '_') -> str:
        """
        Làm sạch tên file với nhiều tùy chọn hơn
        
        Args:
            filename: Tên file gốc
            replacement: Ký tự thay thế
        """
        # Ký tự không hợp lệ cho Windows và Unix
        invalid_chars = '<>:"/\\|?*\x00'
        
        # Thay thế ký tự không hợp lệ
        clean_name = filename
        for char in invalid_chars:
            clean_name = clean_name.replace(char, replacement)
        
        # Loại bỏ khoảng trắng đầu cuối
        clean_name = clean_name.strip()
        
        # Loại bỏ dấu chấm ở cuối (Windows không cho phép)
        clean_name = clean_name.rstrip('.')
        
        # Kiểm tra tên file reserved trên Windows
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        name_without_ext = Path(clean_name).stem.upper()
        if name_without_ext in reserved_names:
            clean_name = f"{replacement}{clean_name}"
        
        return clean_name
    
    @staticmethod
    def get_directory_size(directory: Union[str, Path], 
                          include_hidden: bool = False) -> Tuple[int, int]:
        """
        Tính tổng kích thước và số lượng file trong thư mục
        
        Returns:
            Tuple (total_size, file_count)
        """
        total_size = 0
        file_count = 0
        
        try:
            for root, dirs, files in os.walk(directory):
                # Lọc hidden directories nếu cần
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    files = [f for f in files if not f.startswith('.')]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                        file_count += 1
                    except (OSError, IOError):
                        continue
                        
        except Exception as e:
            FileUtils.logger.error(f"Lỗi khi tính kích thước thư mục {directory}: {e}")
        
        return total_size, file_count
    
    @staticmethod
    def safe_copy(source: Union[str, Path], 
                 destination: Union[str, Path],
                 overwrite: bool = False,
                 verify: bool = True) -> bool:
        """
        Copy file an toàn với verification
        
        Args:
            source: File nguồn
            destination: File đích
            overwrite: Cho phép ghi đè
            verify: Verify bằng hash sau khi copy
        """
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            # Kiểm tra file nguồn
            if not source_path.exists():
                FileUtils.logger.error(f"File nguồn không tồn tại: {source}")
                return False
            
            # Kiểm tra file đích
            if dest_path.exists() and not overwrite:
                FileUtils.logger.error(f"File đích đã tồn tại: {destination}")
                return False
            
            # Tạo thư mục đích nếu chưa có
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(source_path, dest_path)
            
            # Verify nếu được yêu cầu
            if verify:
                source_hash = FileUtils.get_file_hash(source_path)
                dest_hash = FileUtils.get_file_hash(dest_path)
                
                if source_hash != dest_hash:
                    FileUtils.logger.error("Hash không khớp sau khi copy")
                    dest_path.unlink()  # Xóa file đích bị lỗi
                    return False
            
            return True
            
        except Exception as e:
            FileUtils.logger.error(f"Lỗi khi copy file: {e}")
            return False
    
    @staticmethod
    def get_available_space(path: Union[str, Path]) -> Dict[str, int]:
        """Lấy thông tin dung lượng disk"""
        try:
            usage = psutil.disk_usage(str(path))
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': (usage.used / usage.total) * 100
            }
        except Exception as e:
            FileUtils.logger.error(f"Lỗi khi lấy thông tin disk: {e}")
            return {}
    
    @staticmethod
    def find_files(directory: Union[str, Path],
                  pattern: str = "*",
                  recursive: bool = True,
                  case_sensitive: bool = False) -> Generator[Path, None, None]:
        """
        Tìm kiếm file với pattern
        
        Args:
            directory: Thư mục tìm kiếm
            pattern: Pattern tìm kiếm (glob style)
            recursive: Tìm kiếm đệ quy
            case_sensitive: Phân biệt hoa thường
        """
        try:
            base_path = Path(directory)
            
            if not case_sensitive:
                # Tìm kiếm case-insensitive (chậm hơn)
                if recursive:
                    for file_path in base_path.rglob('*'):
                        if file_path.is_file():
                            if file_path.match(pattern.lower()) or file_path.name.lower().find(pattern.lower()) != -1:
                                yield file_path
                else:
                    for file_path in base_path.glob('*'):
                        if file_path.is_file():
                            if file_path.match(pattern.lower()) or file_path.name.lower().find(pattern.lower()) != -1:
                                yield file_path
            else:
                # Tìm kiếm case-sensitive (nhanh hơn)
                if recursive:
                    yield from base_path.rglob(pattern)
                else:
                    yield from base_path.glob(pattern)
                    
        except Exception as e:
            FileUtils.logger.error(f"Lỗi khi tìm kiếm file: {e}")
    
    @staticmethod
    def create_backup(file_path: Union[str, Path], 
                     backup_dir: Optional[Union[str, Path]] = None,
                     timestamp: bool = True) -> Optional[Path]:
        """
        Tạo backup của file
        
        Args:
            file_path: File cần backup
            backup_dir: Thư mục backup (mặc định là cùng thư mục)
            timestamp: Thêm timestamp vào tên file
        """
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                return None
            
            if backup_dir:
                backup_path = Path(backup_dir)
                backup_path.mkdir(parents=True, exist_ok=True)
            else:
                backup_path = source_path.parent
            
            # Tạo tên file backup
            if timestamp:
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{source_path.stem}_{timestamp_str}{source_path.suffix}"
            else:
                backup_name = f"{source_path.stem}_backup{source_path.suffix}"
            
            backup_file = backup_path / backup_name
            
            # Copy file
            shutil.copy2(source_path, backup_file)
            
            return backup_file
            
        except Exception as e:
            FileUtils.logger.error(f"Lỗi khi tạo backup: {e}")
            return None