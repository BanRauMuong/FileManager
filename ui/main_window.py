import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging
from threading import Thread
import webbrowser

from .file_browser import FileBrowser
from .text_editor import TextEditor
from ..core.file_operations import FileOperations
from ..core.directory_manager import DirectoryManager
from ..core.file_executor import FileExecutor
from ..utils.search_engine import SearchEngine
from ..utils.compression import CompressionManager
from ..config.settings import Settings


class MainWindow:
    """
    Cửa sổ chính của File Manager
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components
        self.file_ops = FileOperations()
        self.dir_manager = DirectoryManager()
        self.file_executor = FileExecutor()
        self.search_engine = SearchEngine()
        self.compression_manager = CompressionManager()
        self.settings = Settings()
        
        # UI components
        self.file_browser = None
        self.text_editor = None
        
        # State variables
        self.current_path = tk.StringVar(value=os.path.expanduser("~"))
        self.status_text = tk.StringVar(value="Ready")
        self.selected_files = []
        self.clipboard_files = []
        self.clipboard_operation = None  # 'copy' or 'cut'
        
        # Setup UI
        self._setup_window()
        self._create_menu()
        self._create_toolbar()
        self._create_main_layout()
        self._create_statusbar()
        self._setup_bindings()
        
        # Load settings
        self._load_settings()
        
        # Initialize file browser
        self._initialize_file_browser()
    
    def _setup_window(self):
        """Thiết lập cửa sổ chính"""
        self.root.title("Advanced File Manager")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Icon (nếu có)
        try:
            self.root.iconbitmap("assets/icon.ico")
        except:
            pass
        
        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configure colors
        self.root.configure(bg='#f0f0f0')
    
    def _create_menu(self):
        """Tạo menu bar"""
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        
        # File menu
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Folder", command=self._new_folder, accelerator="Ctrl+Shift+N")
        file_menu.add_command(label="New File", command=self._new_file, accelerator="Ctrl+N")
        file_menu.add_separator()
        file_menu.add_command(label="Open", command=self._open_selected, accelerator="Enter")
        file_menu.add_command(label="Open With...", command=self._open_with)
        file_menu.add_separator()
        file_menu.add_command(label="Properties", command=self._show_properties, accelerator="Alt+Enter")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._exit_app, accelerator="Ctrl+Q")
        
        # Edit menu
        edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Cut", command=self._cut_files, accelerator="Ctrl+X")
        edit_menu.add_command(label="Copy", command=self._copy_files, accelerator="Ctrl+C")
        edit_menu.add_command(label="Paste", command=self._paste_files, accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="Delete", command=self._delete_files, accelerator="Delete")
        edit_menu.add_command(label="Rename", command=self._rename_file, accelerator="F2")
        edit_menu.add_separator()
        edit_menu.add_command(label="Select All", command=self._select_all, accelerator="Ctrl+A")
        
        # View menu
        view_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh", command=self._refresh_view, accelerator="F5")
        view_menu.add_separator()
        view_menu.add_checkbutton(label="Show Hidden Files", command=self._toggle_hidden_files)
        view_menu.add_checkbutton(label="Show File Extensions", command=self._toggle_extensions)
        view_menu.add_separator()
        
        # View modes
        view_mode_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="View Mode", menu=view_mode_menu)
        view_mode_menu.add_radiobutton(label="List", command=lambda: self._set_view_mode('list'))
        view_mode_menu.add_radiobutton(label="Details", command=lambda: self._set_view_mode('details'))
        view_mode_menu.add_radiobutton(label="Icons", command=lambda: self._set_view_mode('icons'))
        
        # Tools menu
        tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Search", command=self._open_search, accelerator="Ctrl+F")
        tools_menu.add_command(label="Terminal Here", command=self._open_terminal)
        tools_menu.add_separator()
        tools_menu.add_command(label="Compress", command=self._compress_files)
        tools_menu.add_command(label="Extract", command=self._extract_archive)
        tools_menu.add_separator()
        tools_menu.add_command(label="Calculate Folder Size", command=self._calculate_folder_size)
        tools_menu.add_command(label="Find Duplicates", command=self._find_duplicates)
        
        # Help menu
        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _create_toolbar(self):
        """Tạo toolbar"""
        self.toolbar_frame = ttk.Frame(self.root)
        self.toolbar_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        # Navigation buttons
        nav_frame = ttk.Frame(self.toolbar_frame)
        nav_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        self.back_btn = ttk.Button(nav_frame, text="◀", command=self._go_back, width=3)
        self.back_btn.pack(side=tk.LEFT, padx=2)
        
        self.forward_btn = ttk.Button(nav_frame, text="▶", command=self._go_forward, width=3)
        self.forward_btn.pack(side=tk.LEFT, padx=2)
        
        self.home_btn = ttk.Button(nav_frame, text="🏠", command=self._go_home, width=3)
        self.home_btn.pack(side=tk.LEFT, padx=2)
        
        self.up_btn = ttk.Button(nav_frame, text="↑", command=self._go_up, width=3)
        self.up_btn.pack(side=tk.LEFT, padx=2)
        
        # Address bar
        addr_frame = ttk.Frame(self.toolbar_frame)
        addr_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        ttk.Label(addr_frame, text="Location:").pack(side=tk.LEFT)
        self.address_entry = ttk.Entry(addr_frame, textvariable=self.current_path, font=('Consolas', 10))
        self.address_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.address_entry.bind('<Return>', self._navigate_to_path)
        
        # Action buttons
        action_frame = ttk.Frame(self.toolbar_frame)
        action_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.search_btn = ttk.Button(action_frame, text="🔍", command=self._open_search, width=3)
        self.search_btn.pack(side=tk.LEFT, padx=2)
        
        self.view_btn = ttk.Button(action_frame, text="📋", command=self._cycle_view_mode, width=3)
        self.view_btn.pack(side=tk.LEFT, padx=2)
        
        self.refresh_btn = ttk.Button(action_frame, text="🔄", command=self._refresh_view, width=3)
        self.refresh_btn.pack(side=tk.LEFT, padx=2)
    
    def _create_main_layout(self):
        """Tạo layout chính"""
        # Main paned window
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Sidebar
        self.sidebar_frame = ttk.Frame(self.main_paned, width=200)
        self.main_paned.add(self.sidebar_frame, minsize=150)
        
        # Create sidebar
        self._create_sidebar()
        
        # Right panel - Main content
        self.content_paned = ttk.PanedWindow(self.main_paned, orient=tk.VERTICAL)
        self.main_paned.add(self.content_paned, minsize=400)
        
        # File browser frame
        self.browser_frame = ttk.Frame(self.content_paned)
        self.content_paned.add(self.browser_frame, minsize=300)
        
        # Preview/Editor frame (collapsible)
        self.preview_frame = ttk.Frame(self.content_paned)
        self.content_paned.add(self.preview_frame, minsize=100)
        
        # Initially hide preview frame
        self.content_paned.forget(self.preview_frame)
        self.preview_visible = False
    
    def _create_sidebar(self):
        """Tạo sidebar với quick access"""
        # Bookmarks section
        bookmarks_label = ttk.Label(self.sidebar_frame, text="Bookmarks", font=('Arial', 10, 'bold'))
        bookmarks_label.pack(anchor=tk.W, padx=5, pady=5)
        
        self.bookmarks_tree = ttk.Treeview(self.sidebar_frame, show='tree', height=8)
        self.bookmarks_tree.pack(fill=tk.BOTH, padx=5, pady=2)
        
        # Add default bookmarks
        self._populate_bookmarks()
        
        # Recent locations
        recent_label = ttk.Label(self.sidebar_frame, text="Recent", font=('Arial', 10, 'bold'))
        recent_label.pack(anchor=tk.W, padx=5, pady=(15, 5))
        
        self.recent_tree = ttk.Treeview(self.sidebar_frame, show='tree', height=6)
        self.recent_tree.pack(fill=tk.BOTH, padx=5, pady=2)
        
        # Drives section (Windows)
        if os.name == 'nt':
            drives_label = ttk.Label(self.sidebar_frame, text="Drives", font=('Arial', 10, 'bold'))
            drives_label.pack(anchor=tk.W, padx=5, pady=(15, 5))
            
            self.drives_tree = ttk.Treeview(self.sidebar_frame, show='tree', height=4)
            self.drives_tree.pack(fill=tk.BOTH, padx=5, pady=2)
            self._populate_drives()
        
        # Bind events
        self.bookmarks_tree.bind('<Double-1>', self._on_bookmark_double_click)
        self.recent_tree.bind('<Double-1>', self._on_recent_double_click)
        if hasattr(self, 'drives_tree'):
            self.drives_tree.bind('<Double-1>', self._on_drive_double_click)
    
    def _create_statusbar(self):
        """Tạo status bar"""
        self.statusbar = ttk.Frame(self.root)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Status text
        self.status_label = ttk.Label(self.statusbar, textvariable=self.status_text)
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Progress bar (hidden by default)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.statusbar, variable=self.progress_var, length=200)
        
        # File count and size info
        self.info_label = ttk.Label(self.statusbar, text="")
        self.info_label.pack(side=tk.RIGHT, padx=5)
    
    def _setup_bindings(self):
        """Thiết lập keyboard shortcuts"""
        self.root.bind('<Control-n>', lambda e: self._new_file())
        self.root.bind('<Control-Shift-N>', lambda e: self._new_folder())
        self.root.bind('<Control-o>', lambda e: self._open_selected())
        self.root.bind('<Control-c>', lambda e: self._copy_files())
        self.root.bind('<Control-x>', lambda e: self._cut_files())
        self.root.bind('<Control-v>', lambda e: self._paste_files())
        self.root.bind('<Control-a>', lambda e: self._select_all())
        self.root.bind('<Control-f>', lambda e: self._open_search())
        self.root.bind('<Control-q>', lambda e: self._exit_app())
        self.root.bind('<F2>', lambda e: self._rename_file())
        self.root.bind('<F5>', lambda e: self._refresh_view())
        self.root.bind('<Delete>', lambda e: self._delete_files())
        self.root.bind('<Alt-Return>', lambda e: self._show_properties())
        self.root.bind('<BackSpace>', lambda e: self._go_up())
        
        # Navigation
        self.root.bind('<Alt-Left>', lambda e: self._go_back())
        self.root.bind('<Alt-Right>', lambda e: self._go_forward())
        self.root.bind('<Alt-Up>', lambda e: self._go_up())
        self.root.bind('<Alt-Home>', lambda e: self._go_home())
    
    def _initialize_file_browser(self):
        """Khởi tạo file browser"""
        self.file_browser = FileBrowser(
            self.browser_frame,
            self.current_path.get(),
            self._on_file_selected,
            self._on_file_double_click,
            self._on_context_menu
        )
        
        # Update status
        self._update_status()
    
    def _populate_bookmarks(self):
        """Điền bookmarks mặc định"""
        bookmarks = [
            ("Desktop", os.path.join(os.path.expanduser("~"), "Desktop")),
            ("Documents", os.path.join(os.path.expanduser("~"), "Documents")),
            ("Downloads", os.path.join(os.path.expanduser("~"), "Downloads")),
            ("Pictures", os.path.join(os.path.expanduser("~"), "Pictures")),
            ("Music", os.path.join(os.path.expanduser("~"), "Music")),
            ("Videos", os.path.join(os.path.expanduser("~"), "Videos")),
        ]
        
        for name, path in bookmarks:
            if os.path.exists(path):
                self.bookmarks_tree.insert('', 'end', text=name, values=[path])
    
    def _populate_drives(self):
        """Điền danh sách drives (Windows)"""
        if os.name == 'nt':
            import string
            drives = ['%s:' % d for d in string.ascii_uppercase if os.path.exists('%s:' % d)]
            for drive in drives:
                self.drives_tree.insert('', 'end', text=drive, values=[drive + '\\'])
    
    # Event handlers
    def _on_file_selected(self, files: List[str]):
        """Xử lý khi file được chọn"""
        self.selected_files = files
        self._update_status()
        
        # Show preview if single file selected
        if len(files) == 1 and os.path.isfile(files[0]):
            self._show_preview(files[0])
    
    def _on_file_double_click(self, file_path: str):
        """Xử lý double-click trên file"""
        if os.path.isdir(file_path):
            self._navigate_to(file_path)
        else:
            self.file_executor.execute_file(file_path)
    
    def _on_context_menu(self, event, file_path: str = None):
        """Hiện context menu"""
        context_menu = tk.Menu(self.root, tearoff=0)
        
        if file_path:
            context_menu.add_command(label="Open", command=lambda: self._open_file(file_path))
            context_menu.add_command(label="Open With...", command=lambda: self._open_with_dialog(file_path))
            context_menu.add_separator()
            context_menu.add_command(label="Cut", command=self._cut_files)
            context_menu.add_command(label="Copy", command=self._copy_files)
            context_menu.add_separator()
            context_menu.add_command(label="Delete", command=self._delete_files)
            context_menu.add_command(label="Rename", command=self._rename_file)
            context_menu.add_separator()
            context_menu.add_command(label="Properties", command=self._show_properties)
        else:
            context_menu.add_command(label="Paste", command=self._paste_files)
            context_menu.add_separator()
            context_menu.add_command(label="New Folder", command=self._new_folder)
            context_menu.add_command(label="New File", command=self._new_file)
            context_menu.add_separator()
            context_menu.add_command(label="Refresh", command=self._refresh_view)
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def _on_bookmark_double_click(self, event):
        """Xử lý double-click trên bookmark"""
        selection = self.bookmarks_tree.selection()
        if selection:
            item = self.bookmarks_tree.item(selection[0])
            path = item['values'][0]
            self._navigate_to(path)
    
    def _on_recent_double_click(self, event):
        """Xử lý double-click trên recent location"""
        selection = self.recent_tree.selection()
        if selection:
            item = self.recent_tree.item(selection[0])
            path = item['values'][0]
            self._navigate_to(path)
    
    def _on_drive_double_click(self, event):
        """Xử lý double-click trên drive"""
        selection = self.drives_tree.selection()
        if selection:
            item = self.drives_tree.item(selection[0])
            path = item['values'][0]
            self._navigate_to(path)
    
    # Navigation methods
    def _navigate_to(self, path: str):
        """Navigate to đường dẫn"""
        if os.path.exists(path):
            self.current_path.set(path)
            if self.file_browser:
                self.file_browser.navigate_to(path)
            self._add_to_recent(path)
            self._update_status()
    
    def _navigate_to_path(self, event=None):
        """Navigate theo path trong address bar"""
        path = self.current_path.get()
        self._navigate_to(path)
    
    def _go_back(self):
        """Quay lại thư mục trước"""
        if self.file_browser:
            self.file_browser.go_back()
            self.current_path.set(self.file_browser.current_path)
    
    def _go_forward(self):
        """Tiến tới thư mục tiếp theo"""
        if self.file_browser:
            self.file_browser.go_forward()
            self.current_path.set(self.file_browser.current_path)
    
    def _go_up(self):
        """Lên thư mục cha"""
        current = self.current_path.get()
        parent = os.path.dirname(current)
        if parent != current:  # Không phải root
            self._navigate_to(parent)
    
    def _go_home(self):
        """Về thư mục home"""
        home = os.path.expanduser("~")
        self._navigate_to(home)
    
    # File operations
    def _new_folder(self):
        """Tạo thư mục mới"""
        name = tk.simpledialog.askstring("New Folder", "Enter folder name:")
        if name:
            new_path = os.path.join(self.current_path.get(), name)
            if self.dir_manager.create_directory(new_path):
                self._refresh_view()
                self.status_text.set(f"Created folder: {name}")
            else:
                messagebox.showerror("Error", f"Failed to create folder: {name}")
    
    def _new_file(self):
        """Tạo file mới"""
        name = tk.simpledialog.askstring("New File", "Enter file name:")
        if name:
            new_path = os.path.join(self.current_path.get(), name)
            if self.file_ops.create_file(new_path):
                self._refresh_view()
                self.status_text.set(f"Created file: {name}")
            else:
                messagebox.showerror("Error", f"Failed to create file: {name}")
    
    def _delete_files(self):
        """Xóa file/folder được chọn"""
        if not self.selected_files:
            return
        
        files_str = "\n".join([os.path.basename(f) for f in self.selected_files])
        if messagebox.askyesno("Confirm Delete", f"Delete the following items?\n\n{files_str}"):
            success_count = 0
            for file_path in self.selected_files:
                if os.path.isdir(file_path):
                    if self.dir_manager.delete_directory(file_path):
                        success_count += 1
                else:
                    if self.file_ops.delete_file(file_path):
                        success_count += 1
            
            self._refresh_view()
            self.status_text.set(f"Deleted {success_count}/{len(self.selected_files)} items")
    
    def _copy_files(self):
        """Copy files to clipboard"""
        if self.selected_files:
            self.clipboard_files = self.selected_files.copy()
            self.clipboard_operation = 'copy'
            self.status_text.set(f"Copied {len(self.selected_files)} items")
    
    def _cut_files(self):
        """Cut files to clipboard"""
        if self.selected_files:
            self.clipboard_files = self.selected_files.copy()
            self.clipboard_operation = 'cut'
            self.status_text.set(f"Cut {len(self.selected_files)} items")
    
    def _paste_files(self):
        """Paste files from clipboard"""
        if not self.clipboard_files:
            return
        
        dest_dir = self.current_path.get()
        success_count = 0
        
        for src_path in self.clipboard_files:
            dest_path = os.path.join(dest_dir, os.path.basename(src_path))
            
            try:
                if self.clipboard_operation == 'copy':
                    if os.path.isdir(src_path):
                        if self.dir_manager.copy_directory(src_path, dest_path):
                            success_count += 1
                    else:
                        if self.file_ops.copy_file(src_path, dest_path):
                            success_count += 1
                elif self.clipboard_operation == 'cut':
                    if self.file_ops.move_file(src_path, dest_path):
                        success_count += 1
            except Exception as e:
                self.logger.error(f"Error pasting {src_path}: {str(e)}")
        
        if self.clipboard_operation == 'cut':
            self.clipboard_files.clear()
        
        self._refresh_view()
        self.status_text.set(f"Pasted {success_count} items")
    
    # Utility methods
    def _update_status(self):
        """Cập nhật status bar"""
        try:
            if self.file_browser:
                file_count = len(self.file_browser.files)
                folder_count = len(self.file_browser.folders)
                selected_count = len(self.selected_files)
                
                if selected_count > 0:
                    self.info_label.config(text=f"{selected_count} selected | {file_count} files, {folder_count} folders")
                else:
                    self.info_label.config(text=f"{file_count} files, {folder_count} folders")
        except:
            pass
    
    def _refresh_view(self):
        """Refresh file browser"""
        if self.file_browser:
            self.file_browser.refresh()
            self._update_status()
    
    def _add_to_recent(self, path: str):
        """Thêm vào recent locations"""
        # Remove if already exists
        for item in self.recent_tree.get_children():
            if self.recent_tree.item(item)['values'][0] == path:
                self.recent_tree.delete(item)
                break
        
        # Add to top
        self.recent_tree.insert('', 0, text=os.path.basename(path), values=[path])
        
        # Keep only last 10 items
        children = self.recent_tree.get_children()
        if len(children) > 10:
            self.recent_tree.delete(children[-1])
    
    def _show_preview(self, file_path: str):
        """Hiển thị preview file"""
        if not self.preview_visible:
            self.content_paned.add(self.preview_frame)
            self.preview_visible = True
        
        # Clear previous preview
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        # Create preview based on file type
        self._create_file_preview(file_path)
    
    def _create_file_preview(self, file_path: str):
        """Tạo preview cho file"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext in ['.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md']:
            self._create_text_preview(file_path)
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            self._create_image_preview(file_path)
        else:
            self._create_info_preview(file_path)
    
    def _create_text_preview(self, file_path: str):
        """Tạo text preview"""
        try:
            preview_text = tk.Text(self.preview_frame, wrap=tk.WORD, height=10)
            preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1000)  # First 1000 chars
                preview_text.insert(tk.END, content)
                if len(content) == 1000:
                    preview_text.insert(tk.END, "\n\n... (truncated)")
            
            preview_text.config(state=tk.DISABLED)
        except Exception as e:
            ttk.Label(self.preview_frame, text=f"Cannot preview: {str(e)}").pack(pady=20)
    
    def _create_image_preview(self, file_path: str):
        """Tạo image preview"""
        try:
            from PIL import Image, ImageTk
            
            # Load and resize image
            img = Image.open(file_path)
            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img)
            
            # Display image
            label = ttk.Label(self.preview_frame, image=photo)
            label.image = photo  # Keep reference
            label.pack(pady=20)
            
        except Exception as e:
            ttk.Label(self.preview_frame, text=f"Cannot preview image: {str(e)}").pack(pady=20)
    
    def _create_info_preview(self, file_path: str):
        """Tạo info preview cho file không preview được"""
        info_frame = ttk.Frame(self.preview_frame)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # File info
        stat = os.stat(file_path)
        info_text = f"""
File: {os.path.basename(file_path)}
Size: {self._format_size(stat.st_size)}
Type: {self.file_executor.get_mime_type(file_path) or 'Unknown'}
Modified: {self._format_time(stat.st_mtime)}
        """
        
        ttk.Label(info_frame, text=info_text.strip(), justify=tk.LEFT).pack(anchor=tk.W)
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
    
    def _format_time(self, timestamp: float) -> str:
        """Format timestamp"""
        import datetime
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    
    # Menu action methods
    def _open_selected(self):
        """Mở file/folder được chọn"""
        if self.selected_files:
            for file_path in self.selected_files:
                self.file_executor.execute_file(file_path)
    
    def _open_with(self):
        """Mở file với ứng dụng được chọn"""
        if not self.selected_files or len(self.selected_files) != 1:
            messagebox.showwarning("Warning", "Please select exactly one file")
            return
        
        self._open_with_dialog(self.selected_files[0])
    
    def _open_with_dialog(self, file_path: str):
        """Hiện dialog chọn ứng dụng"""
        # Get available applications
        associations = self.file_executor.get_file_associations()
        file_ext = Path(file_path).suffix.lower()
        apps = associations.get(file_ext, ['open_file'])
        
        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Open With")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"Choose application to open:\n{os.path.basename(file_path)}").pack(pady=10)
        
        app_var = tk.StringVar(value=apps[0])
        for app in apps:
            ttk.Radiobutton(dialog, text=app.replace('_', ' ').title(), variable=app_var, value=app).pack(anchor=tk.W, padx=20)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def open_with_selected():
            self.file_executor.execute_file(file_path, app_var.get())
            dialog.destroy()
        
        ttk.Button(button_frame, text="Open", command=open_with_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _rename_file(self):
        """Đổi tên file"""
        if not self.selected_files or len(self.selected_files) != 1:
            messagebox.showwarning("Warning", "Please select exactly one file")
            return
        
        old_path = self.selected_files[0]
        old_name = os.path.basename(old_path)
        
        new_name = tk.simpledialog.askstring("Rename", "Enter new name:", initialvalue=old_name)
        if new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            if self.file_ops.move_file(old_path, new_path):
                self._refresh_view()
                self.status_text.set(f"Renamed to: {new_name}")
            else:
                messagebox.showerror("Error", f"Failed to rename to: {new_name}")
    
    def _show_properties(self):
        """Hiển thị properties dialog"""
        if not self.selected_files:
            return
        
        # Create properties dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Properties")
        dialog.geometry("400x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create notebook for tabs
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for file_path in self.selected_files[:5]:  # Limit to 5 files
            self._create_properties_tab(notebook, file_path)
    
    def _create_properties_tab(self, notebook: ttk.Notebook, file_path: str):
        """Tạo tab properties cho file"""
        tab_frame = ttk.Frame(notebook)
        notebook.add(tab_frame, text=os.path.basename(file_path))
        
        # Create scrollable text widget
        text_widget = tk.Text(tab_frame, wrap=tk.WORD, font=('Consolas', 9))
        scrollbar = ttk.Scrollbar(tab_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Get file properties
        try:
            stat = os.stat(file_path)
            properties = f"""
Name: {os.path.basename(file_path)}
Location: {os.path.dirname(file_path)}
Size: {self._format_size(stat.st_size)}
Type: {self.file_executor.get_mime_type(file_path) or 'Unknown'}

Created: {self._format_time(stat.st_ctime)}
Modified: {self._format_time(stat.st_mtime)}
Accessed: {self._format_time(stat.st_atime)}

Permissions: {oct(stat.st_mode)[-3:]}
Owner ID: {stat.st_uid}
Group ID: {stat.st_gid}
            """
            
            # Add hash for files
            if os.path.isfile(file_path) and stat.st_size < 100 * 1024 * 1024:  # < 100MB
                try:
                    md5_hash = self.file_ops.get_file_hash(file_path, 'md5')
                    sha1_hash = self.file_ops.get_file_hash(file_path, 'sha1')
                    properties += f"\nMD5: {md5_hash}\nSHA1: {sha1_hash}"
                except:
                    pass
            
            text_widget.insert(tk.END, properties.strip())
            text_widget.config(state=tk.DISABLED)
            
        except Exception as e:
            text_widget.insert(tk.END, f"Error reading properties: {str(e)}")
            text_widget.config(state=tk.DISABLED)
    
    def _select_all(self):
        """Chọn tất cả files"""
        if self.file_browser:
            self.file_browser.select_all()
    
    def _toggle_hidden_files(self):
        """Toggle hiển thị hidden files"""
        if self.file_browser:
            self.file_browser.toggle_hidden_files()
    
    def _toggle_extensions(self):
        """Toggle hiển thị file extensions"""
        if self.file_browser:
            self.file_browser.toggle_extensions()
    
    def _set_view_mode(self, mode: str):
        """Đặt view mode"""
        if self.file_browser:
            self.file_browser.set_view_mode(mode)
    
    def _cycle_view_mode(self):
        """Cycle qua các view modes"""
        if self.file_browser:
            self.file_browser.cycle_view_mode()
    
    def _open_search(self):
        """Mở search dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Search")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Search input
        input_frame = ttk.Frame(dialog)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(input_frame, text="Search for:").pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(input_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        search_btn = ttk.Button(input_frame, text="Search", command=lambda: self._perform_search(dialog, search_var.get()))
        search_btn.pack(side=tk.RIGHT)
        
        # Results
        results_frame = ttk.Frame(dialog)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.search_results = ttk.Treeview(results_frame, columns=('path', 'size', 'modified'), show='tree headings')
        self.search_results.heading('#0', text='Name')
        self.search_results.heading('path', text='Path')
        self.search_results.heading('size', text='Size')
        self.search_results.heading('modified', text='Modified')
        
        search_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.search_results.yview)
        self.search_results.configure(yscrollcommand=search_scroll.set)
        
        self.search_results.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        search_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click
        self.search_results.bind('<Double-1>', self._on_search_result_double_click)
        
        search_entry.focus()
        search_entry.bind('<Return>', lambda e: self._perform_search(dialog, search_var.get()))
    
    def _perform_search(self, dialog: tk.Toplevel, query: str):
        """Thực hiện search"""
        if not query:
            return
        
        # Clear previous results
        for item in self.search_results.get_children():
            self.search_results.delete(item)
        
        # Show progress
        self.status_text.set("Searching...")
        self.progress_bar.pack(side=tk.LEFT, padx=5)
        self.root.update()
        
        # Perform search in thread
        def search_thread():
            try:
                results = self.search_engine.search(
                    query, 
                    self.current_path.get(),
                    recursive=True,
                    max_results=100
                )
                
                # Update UI in main thread
                self.root.after(0, lambda: self._update_search_results(results))
            except Exception as e:
                self.root.after(0, lambda: self.status_text.set(f"Search error: {str(e)}"))
            finally:
                self.root.after(0, lambda: self.progress_bar.pack_forget())
        
        Thread(target=search_thread, daemon=True).start()
    
    def _update_search_results(self, results: List[str]):
        """Cập nhật search results"""
        for file_path in results:
            try:
                stat = os.stat(file_path)
                name = os.path.basename(file_path)
                size = self._format_size(stat.st_size)
                modified = self._format_time(stat.st_mtime)
                
                self.search_results.insert('', 'end', text=name, values=(file_path, size, modified))
            except:
                continue
        
        self.status_text.set(f"Found {len(results)} results")
    
    def _on_search_result_double_click(self, event):
        """Xử lý double-click trên search result"""
        selection = self.search_results.selection()
        if selection:
            item = self.search_results.item(selection[0])
            file_path = item['values'][0]
            
            # Navigate to parent directory and select file
            parent_dir = os.path.dirname(file_path)
            self._navigate_to(parent_dir)
            
            # Select the file in browser
            if self.file_browser:
                self.file_browser.select_file(file_path)
    
    def _open_terminal(self):
        """Mở terminal tại thư mục hiện tại"""
        self.file_executor.open_in_terminal(self.current_path.get())
    
    def _compress_files(self):
        """Nén files được chọn"""
        if not self.selected_files:
            messagebox.showwarning("Warning", "Please select files to compress")
            return
        
        # Choose output file
        output_file = filedialog.asksaveasfilename(
            title="Save archive as",
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip"), ("TAR files", "*.tar"), ("All files", "*.*")]
        )
        
        if output_file:
            self.status_text.set("Compressing...")
            self.progress_bar.pack(side=tk.LEFT, padx=5)
            self.root.update()
            
            def compress_thread():
                try:
                    success = self.compression_manager.compress_files(self.selected_files, output_file)
                    if success:
                        self.root.after(0, lambda: self.status_text.set(f"Compressed to: {os.path.basename(output_file)}"))
                        self.root.after(0, self._refresh_view)
                    else:
                        self.root.after(0, lambda: messagebox.showerror("Error", "Compression failed"))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Compression failed: {str(e)}"))
                finally:
                    self.root.after(0, lambda: self.progress_bar.pack_forget())
            
            Thread(target=compress_thread, daemon=True).start()
    
    def _extract_archive(self):
        """Giải nén archive"""
        if not self.selected_files or len(self.selected_files) != 1:
            messagebox.showwarning("Warning", "Please select exactly one archive file")
            return
        
        archive_path = self.selected_files[0]
        if not self.compression_manager.is_archive(archive_path):
            messagebox.showwarning("Warning", "Selected file is not a supported archive")
            return
        
        # Choose output directory
        output_dir = filedialog.askdirectory(title="Extract to directory")
        if output_dir:
            self.status_text.set("Extracting...")
            self.progress_bar.pack(side=tk.LEFT, padx=5)
            self.root.update()
            
            def extract_thread():
                try:
                    success = self.compression_manager.extract_archive(archive_path, output_dir)
                    if success:
                        self.root.after(0, lambda: self.status_text.set("Extraction completed"))
                        self.root.after(0, self._refresh_view)
                    else:
                        self.root.after(0, lambda: messagebox.showerror("Error", "Extraction failed"))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Extraction failed: {str(e)}"))
                finally:
                    self.root.after(0, lambda: self.progress_bar.pack_forget())
            
            Thread(target=extract_thread, daemon=True).start()
    
    def _calculate_folder_size(self):
        """Tính kích thước thư mục"""
        if not self.selected_files:
            messagebox.showwarning("Warning", "Please select folders")
            return
        
        def calculate_thread():
            results = []
            for path in self.selected_files:
                if os.path.isdir(path):
                    size = self.dir_manager.get_directory_size(path)
                    results.append((path, size))
            
            self.root.after(0, lambda: self._show_size_results(results))
        
        self.status_text.set("Calculating sizes...")
        Thread(target=calculate_thread, daemon=True).start()
    
    def _show_size_results(self, results: List[tuple]):
        """Hiển thị kết quả tính size"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Folder Sizes")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        
        tree = ttk.Treeview(dialog, columns=('size',), show='tree headings')
        tree.heading('#0', text='Folder')
        tree.heading('size', text='Size')
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for path, size in results:
            name = os.path.basename(path)
            size_str = self._format_size(size)
            tree.insert('', 'end', text=name, values=(size_str,))
        
        self.status_text.set("Size calculation completed")
    
    def _find_duplicates(self):
        """Tìm file trùng lặp"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Find Duplicates")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        
        # Options frame
        options_frame = ttk.Frame(dialog)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        include_subdirs = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Include subdirectories", variable=include_subdirs).pack(side=tk.LEFT)
        
        find_btn = ttk.Button(options_frame, text="Find Duplicates", 
                             command=lambda: self._perform_duplicate_search(dialog, include_subdirs.get()))
        find_btn.pack(side=tk.RIGHT)
        
        # Results
        results_frame = ttk.Frame(dialog)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.duplicates_tree = ttk.Treeview(results_frame, columns=('size', 'count'), show='tree headings')
        self.duplicates_tree.heading('#0', text='File Name')
        self.duplicates_tree.heading('size', text='Size')
        self.duplicates_tree.heading('count', text='Copies')
        
        dup_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.duplicates_tree.yview)
        self.duplicates_tree.configure(yscrollcommand=dup_scroll.set)
        
        self.duplicates_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dup_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _perform_duplicate_search(self, dialog: tk.Toplevel, include_subdirs: bool):
        """Thực hiện tìm kiếm duplicates"""
        # Clear previous results
        for item in self.duplicates_tree.get_children():
            self.duplicates_tree.delete(item)
        
        def search_thread():
            try:
                duplicates = self.file_ops.find_duplicate_files(
                    self.current_path.get(),
                    recursive=include_subdirs
                )
                
                self.root.after(0, lambda: self._update_duplicate_results(duplicates))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Duplicate search failed: {str(e)}"))
        
        self.status_text.set("Searching for duplicates...")
        Thread(target=search_thread, daemon=True).start()
    
    def _update_duplicate_results(self, duplicates: Dict[str, List[str]]):
        """Cập nhật duplicate results"""
        for hash_value, file_list in duplicates.items():
            if len(file_list) > 1:
                # Add parent item
                first_file = file_list[0]
                stat = os.stat(first_file)
                size_str = self._format_size(stat.st_size)
                
                parent = self.duplicates_tree.insert('', 'end', 
                                                    text=os.path.basename(first_file),
                                                    values=(size_str, len(file_list)))
                
                # Add child items
                for file_path in file_list:
                    self.duplicates_tree.insert(parent, 'end', text=file_path, values=('', ''))
        
        self.status_text.set(f"Found {len(duplicates)} duplicate groups")
    
    def _show_shortcuts(self):
        """Hiển thị keyboard shortcuts"""
        shortcuts_text = """
Navigation:
  Alt + Left/Right  - Back/Forward
  Alt + Up         - Go up one level
  Alt + Home       - Go to home directory
  Backspace        - Go up one level

File Operations:
  Ctrl + N         - New file
  Ctrl + Shift + N - New folder
  Ctrl + C         - Copy selected files
  Ctrl + X         - Cut selected files  
  Ctrl + V         - Paste files
  Ctrl + A         - Select all
  Delete           - Delete selected files
  F2               - Rename selected file
  
View:
  F5               - Refresh view
  Ctrl + F         - Search files
  
Other:
  Enter            - Open selected file/folder
  Alt + Enter      - Show properties
  Ctrl + Q         - Exit application
        """
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Keyboard Shortcuts")
        dialog.geometry("400x500")
        dialog.transient(self.root)
        
        text_widget = tk.Text(dialog, wrap=tk.WORD, font=('Consolas', 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, shortcuts_text.strip())
        text_widget.config(state=tk.DISABLED)
    
    def _show_about(self):
        """Hiển thị about dialog"""
        about_text = """
Advanced File Manager v1.0

A powerful cross-platform file manager built with Python and Tkinter.

Features:
• File and folder operations
• Multi-tab interface  
• Built-in text editor
• Search functionality
• Archive support
• Duplicate file finder
• File preview
• Customizable interface

Created with Python and Tkinter
        """
        
        messagebox.showinfo("About", about_text.strip())
    
    def _load_settings(self):
        """Tải settings"""
        try:
            settings = self.settings.load_settings()
            
            # Apply window settings
            if 'window_size' in settings:
                self.root.geometry(settings['window_size'])
            
            if 'window_state' in settings:
                self.root.state(settings['window_state'])
                
        except Exception as e:
            self.logger.error(f"Error loading settings: {str(e)}")
    
    def _save_settings(self):
        """Lưu settings"""
        try:
            settings = {
                'window_size': self.root.geometry(),
                'window_state': self.root.state(),
                'current_path': self.current_path.get(),
            }
            
            self.settings.save_settings(settings)
        except Exception as e:
            self.logger.error(f"Error saving settings: {str(e)}")
    
    def _exit_app(self):
        """Thoát ứng dụng"""
        try:
            self._save_settings()
        except:
            pass
        
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Chạy ứng dụng"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._exit_app)
            self.root.mainloop()
        except KeyboardInterrupt:
            self._exit_app()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run application
    app = MainWindow()
    app.run()