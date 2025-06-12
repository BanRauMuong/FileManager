import os
import sys
import subprocess
import platform
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from urllib.parse import quote


class FileExecutor:
    """
    Xử lý việc thực thi và mở file với ứng dụng phù hợp
    """
    
    def __init__(self):
            self.logger = logging.getLogger(__name__)
            self.system = platform.system().lower()
            
            # Fix: Windows detection
            if self.system == 'windows':
                self.system = 'windows'
            elif self.system == 'darwin':
                self.system = 'darwin'
            else:
                self.system = 'linux'
            
            # Mapping các extension với ứng dụng mặc định
            self.default_apps = {
                # Text files
                '.txt': 'notepad' if self.system == 'windows' else 'gedit',
                '.py': 'python',
                '.js': 'node',
                '.html': 'browser',
                '.css': 'browser',
                '.json': 'notepad' if self.system == 'windows' else 'gedit',
                '.xml': 'notepad' if self.system == 'windows' else 'gedit',
                '.md': 'notepad' if self.system == 'windows' else 'gedit',
                
                # Image files
                '.jpg': 'image_viewer',
                '.jpeg': 'image_viewer',
                '.png': 'image_viewer',
                '.gif': 'image_viewer',
                '.bmp': 'image_viewer',
                '.svg': 'browser',
                
                # Document files
                '.pdf': 'pdf_viewer',
                '.doc': 'word_processor',
                '.docx': 'word_processor',
                '.xls': 'spreadsheet',
                '.xlsx': 'spreadsheet',
                '.ppt': 'presentation',
                '.pptx': 'presentation',
                
                # Archive files
                '.zip': 'archive_manager',
                '.rar': 'archive_manager',
                '.7z': 'archive_manager',
                '.tar': 'archive_manager',
                '.gz': 'archive_manager',
                
                # Media files
                '.mp3': 'audio_player',
                '.wav': 'audio_player',
                '.flac': 'audio_player',
                '.mp4': 'video_player',
                '.avi': 'video_player',
                '.mkv': 'video_player',
                '.mov': 'video_player',
            }
            
            # Command mapping cho từng hệ điều hành
            self.system_commands = self._get_system_commands()
    
    def _get_system_commands(self) -> Dict[str, Dict[str, str]]:
        """Lấy các lệnh system-specific"""
        if self.system == 'windows':
            return {
                'open_file': 'start ""',
                'open_folder': 'explorer',
                'run_command': 'cmd /c',
                'notepad': 'notepad',
                'browser': 'start',
                'image_viewer': 'start',
                'pdf_viewer': 'start',
                'word_processor': 'start',
                'spreadsheet': 'start',
                'presentation': 'start',
                'archive_manager': 'start',
                'audio_player': 'start',
                'video_player': 'start',
            }
        elif self.system == 'darwin':  # macOS
            return {
                'open_file': 'open',
                'open_folder': 'open',
                'run_command': '/bin/bash -c',
                'notepad': 'open -e',
                'browser': 'open',
                'image_viewer': 'open',
                'pdf_viewer': 'open',
                'word_processor': 'open',
                'spreadsheet': 'open',
                'presentation': 'open',
                'archive_manager': 'open',
                'audio_player': 'open',
                'video_player': 'open',
            }
        else:  # Linux
            return {
                'open_file': 'xdg-open',
                'open_folder': 'xdg-open',
                'run_command': '/bin/bash -c',
                'notepad': 'gedit',
                'browser': 'xdg-open',
                'image_viewer': 'eog',
                'pdf_viewer': 'evince',
                'word_processor': 'libreoffice --writer',
                'spreadsheet': 'libreoffice --calc',
                'presentation': 'libreoffice --impress',
                'archive_manager': 'file-roller',
                'audio_player': 'rhythmbox',
                'video_player': 'vlc',
            }
    
    def execute_file(self, file_path: str, app_name: Optional[str] = None) -> bool:
        """
        Thực thi file với ứng dụng được chỉ định hoặc mặc định
        
        Args:
            file_path: Đường dẫn tới file
            app_name: Tên ứng dụng để mở (optional)
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"File không tồn tại: {file_path}")
                return False
            
            # Nếu không chỉ định app, sử dụng app mặc định
            if not app_name:
                app_name = self._get_default_app(file_path)
            
            # Kiểm tra quyền thực thi nếu là file executable
            if self._is_executable(file_path):
                return self._execute_executable(file_path)
            
            # Mở file với ứng dụng
            return self._open_with_app(file_path, app_name)
            
        except Exception as e:
            self.logger.error(f"Lỗi khi thực thi file {file_path}: {str(e)}")
            return False
    
    def _get_default_app(self, file_path: str) -> str:
        """Lấy ứng dụng mặc định cho file"""
        file_ext = Path(file_path).suffix.lower()
        return self.default_apps.get(file_ext, 'open_file')
    
    def _is_executable(self, file_path: str) -> bool:
        """Kiểm tra file có thể thực thi không"""
        if self.system == 'windows':
            executable_exts = ['.exe', '.bat', '.cmd', '.com', '.msi']
            return Path(file_path).suffix.lower() in executable_exts
        else:
            return os.access(file_path, os.X_OK)
    
    def _execute_executable(self, file_path: str) -> bool:
        """Thực thi file executable"""
        try:
            if self.system == 'windows':
                subprocess.Popen([file_path], shell=True)
            else:
                subprocess.Popen([file_path])
            return True
        except Exception as e:
            self.logger.error(f"Lỗi khi thực thi executable {file_path}: {str(e)}")
            return False
    
    def _open_with_app(self, file_path: str, app_name: str) -> bool:
        """Mở file với ứng dụng chỉ định - Security improved"""
        try:
            command = self.system_commands.get(app_name, self.system_commands['open_file'])
            
            if self.system == 'windows':
                if app_name == 'browser':
                    os.startfile(file_path)
                else:
                    # Security fix: Use list instead of string
                    cmd_parts = command.split()
                    cmd_parts.append(file_path)
                    subprocess.Popen(cmd_parts, shell=False)
            else:
                subprocess.Popen([command, file_path])
            
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi mở file với {app_name}: {str(e)}")
            return self._open_with_system_default(file_path)
    
    def _open_with_system_default(self, file_path: str) -> bool:
        """Mở file với ứng dụng mặc định của hệ thống"""
        try:
            if self.system == 'windows':
                os.startfile(file_path)
            elif self.system == 'darwin':
                subprocess.Popen(['open', file_path])
            else:
                subprocess.Popen(['xdg-open', file_path])
            return True
        except Exception as e:
            self.logger.error(f"Lỗi khi mở file với system default: {str(e)}")
            return False
    
    def open_folder(self, folder_path: str) -> bool:
        """
        Mở thư mục trong file explorer
        
        Args:
            folder_path: Đường dẫn thư mục
            
        Returns:
            bool: True nếu thành công
        """
        try:
            if not os.path.exists(folder_path):
                self.logger.error(f"Thư mục không tồn tại: {folder_path}")
                return False
            
            command = self.system_commands['open_folder']
            
            if self.system == 'windows':
                subprocess.Popen(f'{command} "{folder_path}"', shell=True)
            else:
                subprocess.Popen([command, folder_path])
            
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi mở thư mục {folder_path}: {str(e)}")
            return False
    
    def open_in_terminal(self, path: str) -> bool:
        """
        Mở terminal tại đường dẫn chỉ định
        
        Args:
            path: Đường dẫn (file hoặc folder)
            
        Returns:
            bool: True nếu thành công
        """
        try:
            # Nếu là file, lấy thư mục chứa file
            if os.path.isfile(path):
                path = os.path.dirname(path)
            
            if not os.path.exists(path):
                self.logger.error(f"Đường dẫn không tồn tại: {path}")
                return False
            
            if self.system == 'windows':
                subprocess.Popen(f'start cmd /k "cd /d {path}"', shell=True)
            elif self.system == 'darwin':
                subprocess.Popen(['open', '-a', 'Terminal', path])
            else:
                # Linux - thử các terminal phổ biến
                terminals = ['gnome-terminal', 'konsole', 'xfce4-terminal', 'xterm']
                for terminal in terminals:
                    try:
                        subprocess.Popen([terminal, '--working-directory', path])
                        break
                    except FileNotFoundError:
                        continue
                else:
                    self.logger.error("Không tìm thấy terminal application")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi mở terminal tại {path}: {str(e)}")
            return False
    
    def run_script(self, script_path: str, args: List[str] = None, timeout: int = 30) -> Tuple[bool, str, str]:
        """
        Chạy script với configurable timeout

        Args:
            script_path: Đường dẫn script
            args: Danh sách tham số truyền vào script
            timeout: Thời gian timeout (giây)

        Returns:
            Tuple[bool, str, str]: (thành công, stdout, stderr)
        """
        try:
            if not os.path.exists(script_path):
                return False, "", f"Script không tồn tại: {script_path}"

            # Xác định interpreter
            file_ext = Path(script_path).suffix.lower()
            interpreters = {
                '.py': 'python',
                '.js': 'node',
                '.sh': 'bash',
                '.bat': 'cmd',
                '.ps1': 'powershell',
            }

            interpreter = interpreters.get(file_ext)
            if not interpreter:
                return False, "", f"Không hỗ trợ định dạng script: {file_ext}"

            # Tạo command
            cmd = [interpreter, script_path]
            if args:
                cmd.extend(args)

            # Chạy script với timeout cấu hình
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return result.returncode == 0, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", f"Script timeout (>{timeout}s)"
        except Exception as e:
            return False, "", f"Lỗi khi chạy script: {str(e)}"
            
            # Xác định interpreter
            file_ext = Path(script_path).suffix.lower()
            interpreters = {
                '.py': 'python',
                '.js': 'node',
                '.sh': 'bash',
                '.bat': 'cmd',
                '.ps1': 'powershell',
            }
            
            interpreter = interpreters.get(file_ext)
            if not interpreter:
                return False, "", f"Không hỗ trợ định dạng script: {file_ext}"
            
            # Tạo command
            cmd = [interpreter, script_path]
            if args:
                cmd.extend(args)
            
            # Chạy script
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout  # Sử dụng tham số timeout
            )
            
            return result.returncode == 0, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", "Script timeout (>30s)"
        except Exception as e:
            return False, "", f"Lỗi khi chạy script: {str(e)}"
    
    def get_file_associations(self) -> Dict[str, List[str]]:
        """
        Lấy danh sách các ứng dụng có thể mở từng loại file
        
        Returns:
            Dict[str, List[str]]: Mapping extension -> list of apps
        """
        associations = {}
        
        for ext, default_app in self.default_apps.items():
            apps = [default_app]
            
            # Thêm các ứng dụng khác có thể mở file
            if ext in ['.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md']:
                apps.extend(['notepad', 'browser'])
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                apps.extend(['image_viewer', 'browser'])
            elif ext in ['.mp3', '.wav', '.flac']:
                apps.append('audio_player')
            elif ext in ['.mp4', '.avi', '.mkv', '.mov']:
                apps.append('video_player')
            
            associations[ext] = list(set(apps))  # Remove duplicates
        
        return associations
    
    def is_app_available(self, app_name: str) -> bool:
        """
        Kiểm tra ứng dụng có khả dụng không
        
        Args:
            app_name: Tên ứng dụng
            
        Returns:
            bool: True nếu có thể sử dụng
        """
        try:
            command = self.system_commands.get(app_name)
            if not command:
                return False
            
            # Thử chạy command với --version hoặc --help
            test_cmd = command.split()[0]
            subprocess.run([test_cmd, '--version'], 
                         capture_output=True, 
                         timeout=5)
            return True
            
        except:
            return False
    
    def get_mime_type(self, file_path: str) -> Optional[str]:
        """
        Lấy MIME type của file
        
        Args:
            file_path: Đường dẫn file
            
        Returns:
            Optional[str]: MIME type hoặc None
        """
        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            return mime_type
        except:
            return None