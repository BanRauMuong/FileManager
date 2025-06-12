import json
import os
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable, Type
from dataclasses import dataclass, asdict, field, fields
from enum import Enum
from datetime import datetime
import jsonschema
from jsonschema import validate
import copy

class Theme(Enum):
    """Enum cho các theme được hỗ trợ"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"  # Theo system theme

class Language(Enum):
    """Enum cho các ngôn ngữ được hỗ trợ"""
    VIETNAMESE = "vi"
    ENGLISH = "en"
    CHINESE = "zh"
    JAPANESE = "ja"

class ViewMode(Enum):
    """Enum cho các chế độ xem"""
    LIST = "list"
    GRID = "grid"
    DETAILS = "details"
    TILES = "tiles"

class SortBy(Enum):
    """Enum cho các tiêu chí sắp xếp"""
    NAME = "name"
    SIZE = "size"
    DATE_MODIFIED = "date_modified"
    DATE_CREATED = "date_created"
    TYPE = "type"
    EXTENSION = "extension"

class CompressionFormat(Enum):
    """Enum cho các định dạng nén"""
    ZIP = "zip"
    RAR = "rar"
    TAR = "tar"
    TAR_GZ = "tar.gz"
    SEVEN_ZIP = "7z"

@dataclass
class UISettings:
    """Cấu hình giao diện"""
    theme: Theme = Theme.LIGHT
    language: Language = Language.VIETNAMESE
    window_width: int = 1200
    window_height: int = 800
    window_x: int = -1  # -1 để center
    window_y: int = -1  # -1 để center
    window_maximized: bool = False
    window_state: str = "normal"  # normal, minimized, maximized
    
    # Toolbar & Menu
    show_toolbar: bool = True
    show_statusbar: bool = True
    show_sidebar: bool = True
    toolbar_icon_size: int = 24
    
    # Colors (hex codes)
    accent_color: str = "#0078d4"
    text_color: str = "#000000"
    background_color: str = "#ffffff"
    
    # Fonts
    ui_font_family: str = "Segoe UI"
    ui_font_size: int = 10

@dataclass
class BrowserSettings:
    """Cấu hình file browser"""
    show_hidden_files: bool = False
    show_system_files: bool = False
    show_file_extensions: bool = True
    show_full_path: bool = True
    default_view_mode: ViewMode = ViewMode.DETAILS
    sort_by: SortBy = SortBy.NAME
    sort_ascending: bool = True
    group_directories_first: bool = True
    
    # Navigation
    remember_tabs: bool = True
    open_new_tab_on_double_click: bool = False
    confirm_navigation: bool = False
    
    # Preview
    enable_file_preview: bool = True
    preview_panel_width: int = 300
    show_thumbnails: bool = True
    thumbnail_size: int = 64

@dataclass
class EditorSettings:
    """Cấu hình text editor"""
    font_family: str = "Consolas"
    font_size: int = 12
    tab_size: int = 4
    use_spaces_for_tabs: bool = True
    word_wrap: bool = True
    show_line_numbers: bool = True
    highlight_current_line: bool = True
    show_whitespace: bool = False
    
    # Auto features
    auto_save: bool = True
    auto_save_interval: int = 30  # seconds
    auto_backup: bool = True
    max_backup_files: int = 5
    
    # Syntax highlighting
    enable_syntax_highlighting: bool = True
    color_scheme: str = "default"
    
    # Code folding
    enable_code_folding: bool = True
    fold_comments: bool = True

@dataclass
class SearchSettings:
    """Cấu hình tìm kiếm"""
    max_search_results: int = 1000
    search_in_content: bool = False
    case_sensitive_search: bool = False
    use_regex: bool = False
    search_subdirectories: bool = True
    exclude_patterns: List[str] = field(default_factory=lambda: ['*.tmp', '*.log', '.git', '.svn'])
    
    # Advanced search
    enable_indexing: bool = False
    index_file_content: bool = False
    max_indexed_file_size: int = 1024 * 1024  # 1MB

@dataclass
class CompressionSettings:
    """Cấu hình nén/giải nén"""
    default_compression: CompressionFormat = CompressionFormat.ZIP
    compression_level: int = 6  # 0-9
    create_subdir_on_extract: bool = True
    preserve_permissions: bool = True
    overwrite_existing: bool = False

@dataclass
class SecuritySettings:
    """Cấu hình bảo mật"""
    confirm_delete: bool = True
    confirm_overwrite: bool = True
    confirm_move_to_trash: bool = True
    backup_before_edit: bool = False
    scan_for_viruses: bool = False
    block_executable_files: bool = False
    
    # Path restrictions
    restricted_paths: List[str] = field(default_factory=list)
    allow_system_access: bool = False

@dataclass
class PerformanceSettings:
    """Cấu hình hiệu suất"""
    file_preview_size_limit: int = 10 * 1024 * 1024  # 10MB
    thumbnail_cache_size: int = 500
    max_recent_files: int = 20
    max_recent_directories: int = 15
    
    # Threading
    max_worker_threads: int = 4
    enable_background_operations: bool = True
    
    # Memory
    max_memory_usage: int = 512 * 1024 * 1024  # 512MB
    gc_interval: int = 60  # seconds

@dataclass
class NetworkSettings:
    """Cấu hình mạng (cho tương lai)"""
    enable_cloud_sync: bool = False
    cloud_provider: str = ""
    sync_interval: int = 300  # seconds
    
    # FTP/SFTP
    default_ftp_port: int = 21
    default_sftp_port: int = 22
    connection_timeout: int = 30

@dataclass
class PluginSettings:
    """Cấu hình plugin"""
    enable_plugins: bool = True
    plugin_directory: str = ""
    auto_update_plugins: bool = False
    enabled_plugins: List[str] = field(default_factory=list)

@dataclass
class AppSettings:
    """Cấu hình tổng thể của ứng dụng"""
    # Version info
    config_version: str = "1.0"
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Sub-settings
    ui: UISettings = field(default_factory=UISettings)
    browser: BrowserSettings = field(default_factory=BrowserSettings)
    editor: EditorSettings = field(default_factory=EditorSettings)
    search: SearchSettings = field(default_factory=SearchSettings)
    compression: CompressionSettings = field(default_factory=CompressionSettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)
    performance: PerformanceSettings = field(default_factory=PerformanceSettings)
    network: NetworkSettings = field(default_factory=NetworkSettings)
    plugins: PluginSettings = field(default_factory=PluginSettings)
    
    # Paths và bookmarks
    last_directory: str = ""
    startup_directory: str = ""  # Empty = last directory
    recent_directories: List[str] = field(default_factory=list)
    bookmarks: List[Dict[str, str]] = field(default_factory=list)
    favorite_files: List[str] = field(default_factory=list)
    
    # Custom user settings
    custom_settings: Dict[str, Any] = field(default_factory=dict)

class SettingsManager:
    """Quản lý cấu hình ứng dụng - Phiên bản nâng cấp"""
    
    _instance: Optional['SettingsManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_file: Optional[str] = None, auto_save: bool = True):
        if hasattr(self, '_initialized'):
            return
            
        self.logger = logging.getLogger(__name__)
        self.auto_save = auto_save
        self._observers: List[Callable[[str, Any, Any], None]] = []
        
        # Determine config file path
        if config_file is None:
            config_dir = self._get_config_directory()
            config_dir.mkdir(parents=True, exist_ok=True)
            self.config_file = config_dir / 'settings.json'
            self.backup_file = config_dir / 'settings.backup.json'
        else:
            self.config_file = Path(config_file)
            self.backup_file = self.config_file.with_suffix('.backup.json')
        
        self.settings = AppSettings()
        self.default_settings = AppSettings()  # Keep defaults for reset
        
        # JSON Schema for validation
        self._schema = self._create_schema()
        
        # Load settings
        self.load_settings()
        self._initialized = True
    
    def _get_config_directory(self) -> Path:
        """Lấy thư mục config phù hợp với từng OS"""
        if os.name == 'nt':  # Windows
            config_dir = Path(os.environ.get('APPDATA', Path.home())) / 'FileManager'
        elif os.name == 'posix':  # Linux/macOS
            if 'darwin' in os.uname().sysname.lower():  # macOS
                config_dir = Path.home() / 'Library' / 'Application Support' / 'FileManager'
            else:  # Linux
                config_dir = Path.home() / '.config' / 'filemanager'
        else:
            config_dir = Path.home() / '.filemanager'
        
        return config_dir
    
    def _create_schema(self) -> Dict:
        """Tạo JSON schema để validate settings"""
        return {
            "type": "object",
            "properties": {
                "config_version": {"type": "string"},
                "last_updated": {"type": "string"},
                "ui": {"type": "object"},
                "browser": {"type": "object"},
                "editor": {"type": "object"},
                "search": {"type": "object"},
                "compression": {"type": "object"},
                "security": {"type": "object"},
                "performance": {"type": "object"},
                "network": {"type": "object"},
                "plugins": {"type": "object"},
                "last_directory": {"type": "string"},
                "startup_directory": {"type": "string"},
                "recent_directories": {"type": "array", "items": {"type": "string"}},
                "bookmarks": {"type": "array"},
                "favorite_files": {"type": "array", "items": {"type": "string"}},
                "custom_settings": {"type": "object"}
            }
        }
    
    def add_observer(self, callback: Callable[[str, Any, Any], None]):
        """Thêm observer để theo dõi thay đổi settings"""
        self._observers.append(callback)
    
    def remove_observer(self, callback: Callable[[str, Any, Any], None]):
        """Xóa observer"""
        if callback in self._observers:
            self._observers.remove(callback)
    
    def _notify_observers(self, key: str, old_value: Any, new_value: Any):
        """Thông báo cho observers về thay đổi"""
        for callback in self._observers:
            try:
                callback(key, old_value, new_value)
            except Exception as e:
                self.logger.error(f"Error in settings observer: {e}")
    
    def load_settings(self) -> bool:
        """Tải cấu hình từ file với error recovery"""
        try:
            if self.config_file.exists():
                return self._load_from_file(self.config_file)
            elif self.backup_file.exists():
                self.logger.warning("Main config corrupted, loading from backup")
                return self._load_from_file(self.backup_file)
            else:
                self.logger.info("No config file found, using defaults")
                return True
                
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            # Try backup
            if self.backup_file.exists():
                try:
                    return self._load_from_file(self.backup_file)
                except:
                    pass
            
            # Use defaults if all fails
            self.settings = AppSettings()
            return False
    
    def _load_from_file(self, file_path: Path) -> bool:
        """Load settings từ file cụ thể"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate JSON
        try:
            validate(instance=data, schema=self._schema)
        except jsonschema.ValidationError as e:
            self.logger.warning(f"Settings validation failed: {e}")
        
        # Create new settings object
        new_settings = AppSettings()
        
        # Update nested settings
        for section_name, section_data in data.items():
            if hasattr(new_settings, section_name):
                section_obj = getattr(new_settings, section_name)
                if hasattr(section_obj, '__dataclass_fields__'):
                    # It's a dataclass, update fields
                    for field_name, value in section_data.items():
                        if hasattr(section_obj, field_name):
                            # Handle enum conversion
                            field_type = section_obj.__dataclass_fields__[field_name].type
                            if hasattr(field_type, '__origin__'):  # Generic types
                                setattr(section_obj, field_name, value)
                            elif issubclass(field_type, Enum):
                                try:
                                    enum_value = field_type(value)
                                    setattr(section_obj, field_name, enum_value)
                                except ValueError:
                                    self.logger.warning(f"Invalid enum value {value} for {field_name}")
                            else:
                                setattr(section_obj, field_name, value)
                else:
                    # Simple attribute
                    setattr(new_settings, section_name, section_data)
        
        self.settings = new_settings
        return True
    
    def save_settings(self, create_backup: bool = True) -> bool:
        """Lưu cấu hình vào file với backup"""
        try:
            # Create backup first
            if create_backup and self.config_file.exists():
                try:
                    import shutil
                    shutil.copy2(self.config_file, self.backup_file)
                except Exception as e:
                    self.logger.warning(f"Failed to create backup: {e}")
            
            # Update timestamp
            self.settings.last_updated = datetime.now().isoformat()
            
            # Create directory if needed
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dict with enum handling
            data = self._to_dict()
            
            # Write atomically
            temp_file = self.config_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            # Atomic move
            temp_file.replace(self.config_file)
            
            self.logger.info("Settings saved successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
            return False
    
    def _to_dict(self) -> Dict[str, Any]:
        """Convert settings to dict with proper enum handling"""
        def convert_value(obj):
            if isinstance(obj, Enum):
                return obj.value
            elif hasattr(obj, '__dataclass_fields__'):
                return {k: convert_value(v) for k, v in asdict(obj).items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_value(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert_value(v) for k, v in obj.items()}
            else:
                return obj
        
        return convert_value(self.settings)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Lấy giá trị cấu hình với dot notation support"""
        try:
            keys = key.split('.')
            obj = self.settings
            
            for k in keys:
                if hasattr(obj, k):
                    obj = getattr(obj, k)
                else:
                    return default
            
            return obj
        except Exception:
            return default
    
    def set(self, key: str, value: Any, auto_save: bool = None) -> bool:
        """Đặt giá trị cấu hình với dot notation support"""
        try:
            keys = key.split('.')
            obj = self.settings
            
            # Navigate to parent object
            for k in keys[:-1]:
                if hasattr(obj, k):
                    obj = getattr(obj, k)
                else:
                    return False
            
            # Set final value
            final_key = keys[-1]
            if hasattr(obj, final_key):
                old_value = getattr(obj, final_key)
                setattr(obj, final_key, value)
                
                # Notify observers
                self._notify_observers(key, old_value, value)
                
                # Auto save if enabled
                if auto_save or (auto_save is None and self.auto_save):
                    self.save_settings()
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error setting {key} = {value}: {e}")
            return False
    
    def get_section(self, section_name: str) -> Optional[Any]:
        """Lấy toàn bộ section settings"""
        return getattr(self.settings, section_name, None)
    
    def update_section(self, section_name: str, **kwargs) -> bool:
        """Cập nhật multiple settings trong section"""
        section = self.get_section(section_name)
        if section is None:
            return False
        
        try:
            for key, value in kwargs.items():
                if hasattr(section, key):
                    old_value = getattr(section, key)
                    setattr(section, key, value)
                    self._notify_observers(f"{section_name}.{key}", old_value, value)
            
            if self.auto_save:
                self.save_settings()
            
            return True
        except Exception as e:
            self.logger.error(f"Error updating section {section_name}: {e}")
            return False
    
    def add_recent_directory(self, directory: str):
        """Thêm thư mục vào danh sách gần đây"""
        if directory in self.settings.recent_directories:
            self.settings.recent_directories.remove(directory)
        
        self.settings.recent_directories.insert(0, directory)
        
        # Limit size
        max_recent = self.settings.performance.max_recent_directories
        if len(self.settings.recent_directories) > max_recent:
            self.settings.recent_directories = self.settings.recent_directories[:max_recent]
        
        if self.auto_save:
            self.save_settings()
    
    def add_bookmark(self, path: str, name: Optional[str] = None, icon: str = "") -> bool:
        """Thêm bookmark với icon support"""
        if name is None:
            name = Path(path).name or path
        
        bookmark = {
            'name': name,
            'path': path,
            'icon': icon,
            'created': datetime.now().isoformat()
        }
        
        # Check duplicates
        for existing in self.settings.bookmarks:
            if existing['path'] == path:
                return False
        
        self.settings.bookmarks.append(bookmark)
        
        if self.auto_save:
            self.save_settings()
        
        return True
    
    def remove_bookmark(self, path: str) -> bool:
        """Xóa bookmark"""
        for i, bookmark in enumerate(self.settings.bookmarks):
            if bookmark['path'] == path:
                del self.settings.bookmarks[i]
                if self.auto_save:
                    self.save_settings()
                return True
        return False
    
    def get_bookmarks(self) -> List[Dict[str, str]]:
        """Lấy danh sách bookmarks"""
        return copy.deepcopy(self.settings.bookmarks)
    
    def add_favorite_file(self, file_path: str):
        """Thêm file vào favorites"""
        if file_path not in self.settings.favorite_files:
            self.settings.favorite_files.append(file_path)
            if self.auto_save:
                self.save_settings()
    
    def remove_favorite_file(self, file_path: str) -> bool:
        """Xóa file khỏi favorites"""
        if file_path in self.settings.favorite_files:
            self.settings.favorite_files.remove(file_path)
            if self.auto_save:
                self.save_settings()
            return True
        return False
    
    def reset_to_defaults(self, section: Optional[str] = None):
        """Khôi phục cấu hình mặc định"""
        if section is None:
            self.settings = AppSettings()
        else:
            if hasattr(self.default_settings, section):
                default_section = getattr(self.default_settings, section)
                setattr(self.settings, section, copy.deepcopy(default_section))
        
        if self.auto_save:
            self.save_settings()
    
    def export_settings(self, file_path: Union[str, Path], sections: Optional[List[str]] = None) -> bool:
        """Xuất cấu hình ra file"""
        try:
            data = self._to_dict()
            
            # Export only specific sections if requested
            if sections:
                filtered_data = {k: v for k, v in data.items() if k in sections}
                data = filtered_data
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            self.logger.error(f"Error exporting settings: {e}")
            return False
    
    def import_settings(self, file_path: Union[str, Path], merge: bool = True) -> bool:
        """Nhập cấu hình từ file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not merge:
                # Complete replacement
                self.settings = AppSettings()
            
            # Update settings
            return self._load_from_dict(data)
            
        except Exception as e:
            self.logger.error(f"Error importing settings: {e}")
            return False
    
    def _load_from_dict(self, data: Dict[str, Any]) -> bool:
        """Load settings from dictionary"""
        try:
            for section_name, section_data in data.items():
                if hasattr(self.settings, section_name):
                    if section_name in ['recent_directories', 'bookmarks', 'favorite_files', 'custom_settings']:
                        # Simple lists/dicts
                        setattr(self.settings, section_name, section_data)
                    else:
                        # Dataclass sections
                        section_obj = getattr(self.settings, section_name)
                        if hasattr(section_obj, '__dataclass_fields__'):
                            for field_name, value in section_data.items():
                                if hasattr(section_obj, field_name):
                                    setattr(section_obj, field_name, value)
            
            if self.auto_save:
                self.save_settings()
            
            return True
        except Exception as e:
            self.logger.error(f"Error loading from dict: {e}")
            return False
    
    def validate_settings(self) -> List[str]:
        """Validate settings và trả về list các lỗi"""
        errors = []
        
        try:
            # Validate paths
            if self.settings.last_directory and not Path(self.settings.last_directory).exists():
                errors.append(f"Last directory does not exist: {self.settings.last_directory}")
            
            # Validate UI settings
            if self.settings.ui.window_width < 400:
                errors.append("Window width too small")
            
            if self.settings.ui.window_height < 300:
                errors.append("Window height too small")
            
            # Validate performance settings
            if self.settings.performance.max_worker_threads < 1:
                errors.append("Max worker threads must be at least 1")
            
            # Clean up invalid recent directories
            valid_dirs = []
            for dir_path in self.settings.recent_directories:
                if Path(dir_path).exists():
                    valid_dirs.append(dir_path)
                else:
                    errors.append(f"Recent directory does not exist: {dir_path}")
            
            self.settings.recent_directories = valid_dirs
            
            # Clean up invalid bookmarks
            valid_bookmarks = []
            for bookmark in self.settings.bookmarks:
                if Path(bookmark['path']).exists():
                    valid_bookmarks.append(bookmark)
                else:
                    errors.append(f"Bookmark path does not exist: {bookmark['path']}")
            
            self.settings.bookmarks = valid_bookmarks
            
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return errors
    
    def get_custom_setting(self, key: str, default: Any = None) -> Any:
        """Lấy custom setting"""
        return self.settings.custom_settings.get(key, default)
    
    def set_custom_setting(self, key: str, value: Any):
        """Đặt custom setting"""
        self.settings.custom_settings[key] = value
        if self.auto_save:
            self.save_settings()
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support - auto save on exit"""
        if self.auto_save:
            self.save_settings()


# Singleton instance
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Lấy singleton instance của SettingsManager"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


# Convenience functions
def get_setting(key: str, default: Any = None) -> Any:
    """Lấy cấu hình nhanh"""
    return get_settings_manager().get(key, default)


def set_setting(key: str, value: Any) -> bool:
    """Đặt cấu hình nhanh"""
    return get_settings_manager().set(key, value)


def save_settings() -> bool:
    """Lưu cấu hình nhanh"""
    return get_settings_manager().save_settings()


def get_ui_settings() -> UISettings:
    """Lấy UI settings"""
    return get_settings_manager().get_section('ui')


def get_browser_settings() -> BrowserSettings:
    """Lấy browser settings"""
    return get_settings_manager().get_section('browser')


def get_editor_settings() -> EditorSettings:
    """Lấy editor settings"""
    return get_settings_manager().get_section('editor')


# Context manager helper
def settings_context(auto_save: bool = True):
    """Context manager để tự động save settings"""
    return SettingsManager(auto_save=auto_save)