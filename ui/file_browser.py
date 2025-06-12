import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import subprocess
import platform

class FileBrowser:
    def __init__(self, parent, on_file_select=None, on_directory_change=None):
        self.parent = parent
        self.on_file_select = on_file_select
        self.on_directory_change = on_directory_change
        self.current_path = os.getcwd()
        self.selected_items = []
        
        self.setup_ui()
        self.refresh_view()
    
    def setup_ui(self):
        # Frame chính
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Toolbar
        self.create_toolbar()
        
        # Address bar
        self.create_address_bar()
        
        # File tree view
        self.create_treeview()
        
        # Status bar
        self.create_status_bar()
    
    def create_toolbar(self):
        toolbar_frame = ttk.Frame(self.main_frame)
        toolbar_frame.pack(fill=tk.X, pady=2)
        
        # Navigation buttons
        self.back_btn = ttk.Button(toolbar_frame, text="◀", width=3, 
                                  command=self.go_back)
        self.back_btn.pack(side=tk.LEFT, padx=2)
        
        self.forward_btn = ttk.Button(toolbar_frame, text="▶", width=3,
                                     command=self.go_forward)
        self.forward_btn.pack(side=tk.LEFT, padx=2)
        
        self.up_btn = ttk.Button(toolbar_frame, text="↑", width=3,
                                command=self.go_up)
        self.up_btn.pack(side=tk.LEFT, padx=2)
        
        self.home_btn = ttk.Button(toolbar_frame, text="🏠", width=3,
                                  command=self.go_home)
        self.home_btn.pack(side=tk.LEFT, padx=2)
        
        # Separator
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, 
                                                             fill=tk.Y, padx=5)
        
        # View options
        self.view_var = tk.StringVar(value="details")
        self.view_combo = ttk.Combobox(toolbar_frame, textvariable=self.view_var,
                                      values=["details", "list", "icons"],
                                      state="readonly", width=10)
        self.view_combo.pack(side=tk.LEFT, padx=2)
        self.view_combo.bind("<<ComboboxSelected>>", self.change_view)
        
        # Refresh button
        self.refresh_btn = ttk.Button(toolbar_frame, text="🔄", width=3,
                                     command=self.refresh_view)
        self.refresh_btn.pack(side=tk.LEFT, padx=2)
    
    def create_address_bar(self):
        address_frame = ttk.Frame(self.main_frame)
        address_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(address_frame, text="Path:").pack(side=tk.LEFT, padx=2)
        
        self.address_var = tk.StringVar(value=self.current_path)
        self.address_entry = ttk.Entry(address_frame, textvariable=self.address_var)
        self.address_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.address_entry.bind("<Return>", self.navigate_to_path)
        
        ttk.Button(address_frame, text="Go", 
                  command=self.navigate_to_path).pack(side=tk.LEFT, padx=2)
    
    def create_treeview(self):
        # Frame cho treeview và scrollbars
        tree_frame = ttk.Frame(self.main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        
        # Treeview
        columns = ("name", "size", "type", "modified")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings")
        
        # Column headers
        self.tree.heading("#0", text="Name", anchor=tk.W)
        self.tree.heading("name", text="Name", anchor=tk.W)
        self.tree.heading("size", text="Size", anchor=tk.E)
        self.tree.heading("type", text="Type", anchor=tk.W)
        self.tree.heading("modified", text="Modified", anchor=tk.W)
        
        # Column widths
        self.tree.column("#0", width=250, minwidth=100)
        self.tree.column("name", width=250, minwidth=100)
        self.tree.column("size", width=100, minwidth=50)
        self.tree.column("type", width=100, minwidth=50)
        self.tree.column("modified", width=150, minwidth=100)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, 
                                   command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL,
                                   command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=v_scrollbar.set,
                           xscrollcommand=h_scrollbar.set)
        
        # Pack components
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind events
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
    
    def create_status_bar(self):
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.pack(fill=tk.X, pady=2)
        
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # File count
        self.file_count_var = tk.StringVar()
        self.file_count_label = ttk.Label(self.status_frame, 
                                         textvariable=self.file_count_var)
        self.file_count_label.pack(side=tk.RIGHT, padx=5)
    
    def refresh_view(self):
        """Làm mới danh sách file/folder"""
        try:
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            if not os.path.exists(self.current_path):
                self.status_var.set("Path does not exist")
                return
            
            # Get directory contents
            items = []
            try:
                for item_name in os.listdir(self.current_path):
                    item_path = os.path.join(self.current_path, item_name)
                    items.append((item_name, item_path))
            except PermissionError:
                self.status_var.set("Permission denied")
                return
            
            # Sort: directories first, then files
            items.sort(key=lambda x: (not os.path.isdir(x[1]), x[0].lower()))
            
            file_count = 0
            folder_count = 0
            
            for item_name, item_path in items:
                try:
                    is_dir = os.path.isdir(item_path)
                    stat_info = os.stat(item_path)
                    
                    # Size
                    if is_dir:
                        size_str = "<DIR>"
                        folder_count += 1
                    else:
                        size_str = self.format_size(stat_info.st_size)
                        file_count += 1
                    
                    # Type
                    if is_dir:
                        file_type = "Folder"
                        icon = "📁"
                    else:
                        ext = os.path.splitext(item_name)[1].lower()
                        file_type = ext[1:].upper() + " File" if ext else "File"
                        icon = self.get_file_icon(ext)
                    
                    # Modified time
                    modified = datetime.fromtimestamp(stat_info.st_mtime)
                    modified_str = modified.strftime("%Y-%m-%d %H:%M")
                    
                    # Insert into tree
                    self.tree.insert("", tk.END, text=f"{icon} {item_name}",
                                   values=(item_name, size_str, file_type, modified_str))
                
                except (OSError, PermissionError):
                    continue
            
            # Update status
            total_items = file_count + folder_count
            self.file_count_var.set(f"{total_items} items ({folder_count} folders, {file_count} files)")
            self.status_var.set("Ready")
            self.address_var.set(self.current_path)
            
            # Notify parent about directory change
            if self.on_directory_change:
                self.on_directory_change(self.current_path)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error refreshing view: {str(e)}")
    
    def format_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def get_file_icon(self, extension):
        """Get icon for file type"""
        icons = {
            '.txt': '📄', '.doc': '📄', '.docx': '📄', '.pdf': '📄',
            '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️',
            '.mp3': '🎵', '.wav': '🎵', '.mp4': '🎬', '.avi': '🎬',
            '.py': '🐍', '.js': '📜', '.html': '🌐', '.css': '🎨',
            '.zip': '📦', '.rar': '📦', '.7z': '📦',
            '.exe': '⚙️', '.msi': '⚙️'
        }
        return icons.get(extension, '📄')
    
    def on_double_click(self, event):
        """Handle double-click event"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        item_name = item['values'][0]
        item_path = os.path.join(self.current_path, item_name)
        
        if os.path.isdir(item_path):
            self.navigate_to(item_path)
        else:
            self.open_file(item_path)
    
    def on_select(self, event):
        """Handle selection change"""
        selection = self.tree.selection()
        self.selected_items = []
        
        for item_id in selection:
            item = self.tree.item(item_id)
            item_name = item['values'][0]
            item_path = os.path.join(self.current_path, item_name)
            self.selected_items.append(item_path)
        
        if self.on_file_select and self.selected_items:
            self.on_file_select(self.selected_items[0])
    
    def navigate_to(self, path):
        """Navigate to specified path"""
        if os.path.exists(path) and os.path.isdir(path):
            self.current_path = os.path.abspath(path)
            self.refresh_view()
    
    def navigate_to_path(self, event=None):
        """Navigate to path from address bar"""
        path = self.address_var.get().strip()
        if path:
            self.navigate_to(path)
    
    def go_back(self):
        """Go to previous directory"""
        # Simple implementation - could be enhanced with history
        parent = os.path.dirname(self.current_path)
        if parent != self.current_path:
            self.navigate_to(parent)
    
    def go_forward(self):
        """Go to next directory (placeholder)"""
        pass  # Would need to implement navigation history
    
    def go_up(self):
        """Go to parent directory"""
        parent = os.path.dirname(self.current_path)
        if parent != self.current_path:
            self.navigate_to(parent)
    
    def go_home(self):
        """Go to home directory"""
        home = os.path.expanduser("~")
        self.navigate_to(home)
    
    def change_view(self, event=None):
        """Change view mode"""
        # Placeholder for different view modes
        pass
    
    def open_file(self, file_path):
        """Open file with default application"""
        try:
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', file_path])
            else:  # Linux
                subprocess.run(['xdg-open', file_path])
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open file: {str(e)}")
    
    def show_context_menu(self, event):
        """Show context menu"""
        # Select item at cursor position
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
        
        # Create context menu
        context_menu = tk.Menu(self.parent, tearoff=0)
        
        if item_id:
            context_menu.add_command(label="Open", command=self.open_selected)
            context_menu.add_command(label="Rename", command=self.rename_selected)
            context_menu.add_separator()
            context_menu.add_command(label="Copy", command=self.copy_selected)
            context_menu.add_command(label="Cut", command=self.cut_selected)
            context_menu.add_separator()
            context_menu.add_command(label="Delete", command=self.delete_selected)
            context_menu.add_separator()
            context_menu.add_command(label="Properties", command=self.show_properties)
        else:
            context_menu.add_command(label="New Folder", command=self.create_new_folder)
            context_menu.add_separator()
            context_menu.add_command(label="Paste", command=self.paste_here)
            context_menu.add_separator()
            context_menu.add_command(label="Refresh", command=self.refresh_view)
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def open_selected(self):
        """Open selected item"""
        if self.selected_items:
            item_path = self.selected_items[0]
            if os.path.isdir(item_path):
                self.navigate_to(item_path)
            else:
                self.open_file(item_path)
    
    def rename_selected(self):
        """Rename selected item"""
        # Placeholder - would show rename dialog
        messagebox.showinfo("Info", "Rename functionality not implemented yet")
    
    def copy_selected(self):
        """Copy selected items"""
        # Placeholder - would implement clipboard operations
        messagebox.showinfo("Info", "Copy functionality not implemented yet")
    
    def cut_selected(self):
        """Cut selected items"""
        # Placeholder - would implement clipboard operations
        messagebox.showinfo("Info", "Cut functionality not implemented yet")
    
    def delete_selected(self):
        """Delete selected items"""
        if not self.selected_items:
            return
        
        items_text = "\n".join([os.path.basename(item) for item in self.selected_items])
        if messagebox.askyesno("Confirm Delete", 
                              f"Are you sure you want to delete:\n{items_text}"):
            # Placeholder - would implement file deletion
            messagebox.showinfo("Info", "Delete functionality not implemented yet")
    
    def show_properties(self):
        """Show properties of selected item"""
        # Placeholder - would show properties dialog
        messagebox.showinfo("Info", "Properties functionality not implemented yet")
    
    def create_new_folder(self):
        """Create new folder"""
        # Placeholder - would show create folder dialog
        messagebox.showinfo("Info", "New folder functionality not implemented yet")
    
    def paste_here(self):
        """Paste items to current directory"""
        # Placeholder - would implement paste from clipboard
        messagebox.showinfo("Info", "Paste functionality not implemented yet")
    
    def get_current_path(self):
        """Get current directory path"""
        return self.current_path
    
    def get_selected_items(self):
        """Get list of selected items"""
        return self.selected_items