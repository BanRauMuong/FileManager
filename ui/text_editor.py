import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font
import os
import re
from datetime import datetime

class TextEditor:
    def __init__(self, parent):
        self.parent = parent
        self.current_file = None
        self.is_modified = False
        self.find_dialog = None
        self.replace_dialog = None
        
        self.setup_ui()
        self.setup_bindings()
    
    def setup_ui(self):
        # Main frame
        self.main_frame = ttk.Frame(self.parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Toolbar
        self.create_toolbar()
        
        # Text area with scrollbars
        self.create_text_area()
        
        # Status bar
        self.create_status_bar()
    
    def create_toolbar(self):
        toolbar_frame = ttk.Frame(self.main_frame)
        toolbar_frame.pack(fill=tk.X, pady=2)
        
        # File operations
        ttk.Button(toolbar_frame, text="New", command=self.new_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="Open", command=self.open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="Save", command=self.save_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="Save As", command=self.save_as_file).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Edit operations
        ttk.Button(toolbar_frame, text="Undo", command=self.undo).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="Redo", command=self.redo).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Search operations
        ttk.Button(toolbar_frame, text="Find", command=self.show_find_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar_frame, text="Replace", command=self.show_replace_dialog).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Font size
        ttk.Label(toolbar_frame, text="Font Size:").pack(side=tk.LEFT, padx=2)
        self.font_size_var = tk.StringVar(value="12")
        font_size_spinbox = ttk.Spinbox(toolbar_frame, from_=8, to=24, width=5,
                                       textvariable=self.font_size_var,
                                       command=self.change_font_size)
        font_size_spinbox.pack(side=tk.LEFT, padx=2)
        font_size_spinbox.bind('<Return>', lambda e: self.change_font_size())
        
        # Word wrap
        self.word_wrap_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar_frame, text="Word Wrap", 
                       variable=self.word_wrap_var,
                       command=self.toggle_word_wrap).pack(side=tk.LEFT, padx=10)
    
    def create_text_area(self):
        # Frame for text widget and scrollbars
        text_frame = ttk.Frame(self.main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        
        # Text widget
        self.text_widget = tk.Text(text_frame, wrap=tk.WORD, undo=True, maxundo=50)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, 
                                   command=self.text_widget.yview)
        h_scrollbar = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL,
                                   command=self.text_widget.xview)
        
        self.text_widget.configure(yscrollcommand=v_scrollbar.set,
                                  xscrollcommand=h_scrollbar.set)
        
        # Grid layout
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        self.text_widget.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Line numbers (optional)
        self.line_numbers = tk.Text(text_frame, width=4, padx=3, takefocus=0,
                                   border=0, state='disabled', wrap=tk.NONE)
        self.line_numbers.grid(row=0, column=2, sticky="ns")
        
        # Configure fonts
        self.configure_fonts()
    
    def create_status_bar(self):
        status_frame = ttk.Frame(self.main_frame)
        status_frame.pack(fill=tk.X, pady=2)
        
        # File status
        self.file_status_var = tk.StringVar(value="New File")
        ttk.Label(status_frame, textvariable=self.file_status_var).pack(side=tk.LEFT, padx=5)
        
        # Encoding
        self.encoding_var = tk.StringVar(value="UTF-8")
        ttk.Label(status_frame, textvariable=self.encoding_var).pack(side=tk.RIGHT, padx=5)
        
        # Cursor position
        self.cursor_pos_var = tk.StringVar(value="Line 1, Col 1")
        ttk.Label(status_frame, textvariable=self.cursor_pos_var).pack(side=tk.RIGHT, padx=5)
        
        # Character count
        self.char_count_var = tk.StringVar(value="0 chars")
        ttk.Label(status_frame, textvariable=self.char_count_var).pack(side=tk.RIGHT, padx=5)
    
    def setup_bindings(self):
        # File operations
        self.text_widget.bind('<Control-n>', lambda e: self.new_file())
        self.text_widget.bind('<Control-o>', lambda e: self.open_file())
        self.text_widget.bind('<Control-s>', lambda e: self.save_file())
        self.text_widget.bind('<Control-Shift-S>', lambda e: self.save_as_file())
        
        # Edit operations
        self.text_widget.bind('<Control-z>', lambda e: self.undo())
        self.text_widget.bind('<Control-y>', lambda e: self.redo())
        self.text_widget.bind('<Control-f>', lambda e: self.show_find_dialog())
        self.text_widget.bind('<Control-h>', lambda e: self.show_replace_dialog())
        
        # Text change events
        self.text_widget.bind('<KeyRelease>', self.on_text_change)
        self.text_widget.bind('<Button-1>', self.on_cursor_move)
        self.text_widget.bind('<Modified>', self.on_modified)
        
        # Focus
        self.text_widget.focus_set()
    
    def configure_fonts(self):
        """Configure fonts for text widget"""
        font_size = int(self.font_size_var.get())
        text_font = font.Font(family="Consolas", size=font_size)
        
        self.text_widget.configure(font=text_font)
        self.line_numbers.configure(font=text_font)
    
    def change_font_size(self):
        """Change font size"""
        try:
            self.configure_fonts()
            self.update_line_numbers()
        except ValueError:
            pass
    
    def toggle_word_wrap(self):
        """Toggle word wrap"""
        if self.word_wrap_var.get():
            self.text_widget.configure(wrap=tk.WORD)
        else:
            self.text_widget.configure(wrap=tk.NONE)
    
    def new_file(self):
        """Create new file"""
        if self.is_modified:
            if not self.ask_save_changes():
                return
        
        self.text_widget.delete(1.0, tk.END)
        self.current_file = None
        self.is_modified = False
        self.file_status_var.set("New File")
        self.update_title()
    
    def open_file(self, file_path=None):
        """Open file"""
        if self.is_modified:
            if not self.ask_save_changes():
                return
        
        if not file_path:
            file_path = filedialog.askopenfilename(
                title="Open File",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("Python files", "*.py"),
                    ("All files", "*.*")
                ]
            )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                self.text_widget.delete(1.0, tk.END)
                self.text_widget.insert(1.0, content)
                
                self.current_file = file_path
                self.is_modified = False
                self.file_status_var.set(os.path.basename(file_path))
                self.update_title()
                self.update_line_numbers()
                
            except Exception as e:
                messagebox.showerror("Error", f"Cannot open file: {str(e)}")
    
    def save_file(self):
        """Save current file"""
        if self.current_file:
            try:
                content = self.text_widget.get(1.0, tk.END + '-1c')
                with open(self.current_file, 'w', encoding='utf-8') as file:
                    file.write(content)
                
                self.is_modified = False
                self.file_status_var.set(os.path.basename(self.current_file))
                self.update_title()
                return True
            except Exception as e:
                messagebox.showerror("Error", f"Cannot save file: {str(e)}")
                return False
        else:
            return self.save_as_file()
    
    def save_as_file(self):
        """Save file as"""
        file_path = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("Python files", "*.py"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                content = self.text_widget.get(1.0, tk.END + '-1c')
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                
                self.current_file = file_path
                self.is_modified = False
                self.file_status_var.set(os.path.basename(file_path))
                self.update_title()
                return True
            except Exception as e:
                messagebox.showerror("Error", f"Cannot save file: {str(e)}")
                return False
        return False
    
    def undo(self):
        """Undo last change"""
        try:
            self.text_widget.edit_undo()
        except tk.TclError:
            pass
    
    def redo(self):
        """Redo last undone change"""
        try:
            self.text_widget.edit_redo()
        except tk.TclError:
            pass
    
    def show_find_dialog(self):
        """Show find dialog"""
        if self.find_dialog and self.find_dialog.winfo_exists():
            self.find_dialog.lift()
            return
        
        self.find_dialog = tk.Toplevel(self.parent)
        self.find_dialog.title("Find")
        self.find_dialog.geometry("350x100")
        self.find_dialog.resizable(False, False)
        
        # Find entry
        ttk.Label(self.find_dialog, text="Find:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.find_entry = ttk.Entry(self.find_dialog, width=30)
        self.find_entry.grid(row=0, column=1, padx=5, pady=5, columnspan=2, sticky="ew")
        self.find_entry.focus()
        
        # Options
        self.case_sensitive_var = tk.BooleanVar()
        ttk.Checkbutton(self.find_dialog, text="Case sensitive", 
                       variable=self.case_sensitive_var).grid(row=1, column=0, padx=5, sticky="w")
        
        # Buttons
        ttk.Button(self.find_dialog, text="Find Next", 
                  command=self.find_next).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(self.find_dialog, text="Find Previous", 
                  command=self.find_previous).grid(row=1, column=2, padx=5, pady=5)
        
        # Bind Enter key
        self.find_entry.bind('<Return>', lambda e: self.find_next())
        
        # Configure grid
        self.find_dialog.grid_columnconfigure(1, weight=1)
    
    def show_replace_dialog(self):
        """Show replace dialog"""
        if self.replace_dialog and self.replace_dialog.winfo_exists():
            self.replace_dialog.lift()
            return
        
        self.replace_dialog = tk.Toplevel(self.parent)
        self.replace_dialog.title("Replace")
        self.replace_dialog.geometry("400x150")
        self.replace_dialog.resizable(False, False)
        
        # Find entry
        ttk.Label(self.replace_dialog, text="Find:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.replace_find_entry = ttk.Entry(self.replace_dialog, width=30)
        self.replace_find_entry.grid(row=0, column=1, padx=5, pady=5, columnspan=3, sticky="ew")
        
        # Replace entry
        ttk.Label(self.replace_dialog, text="Replace:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.replace_entry = ttk.Entry(self.replace_dialog, width=30)
        self.replace_entry.grid(row=1, column=1, padx=5, pady=5, columnspan=3, sticky="ew")
        
        # Options
        self.replace_case_sensitive_var = tk.BooleanVar()
        ttk.Checkbutton(self.replace_dialog, text="Case sensitive", 
                       variable=self.replace_case_sensitive_var).grid(row=2, column=0, padx=5, sticky="w")
        
        # Buttons
        ttk.Button(self.replace_dialog, text="Find Next", 
                  command=self.replace_find_next).grid(row=2, column=1, padx=2, pady=5)
        ttk.Button(self.replace_dialog, text="Replace", 
                  command=self.replace_current).grid(row=2, column=2, padx=2, pady=5)
        ttk.Button(self.replace_dialog, text="Replace All", 
                  command=self.replace_all).grid(row=2, column=3, padx=2, pady=5)
        
        self.replace_find_entry.focus()
        
        # Configure grid
        self.replace_dialog.grid_columnconfigure(1, weight=1)
    
    def find_next(self):
        """Find next occurrence"""
        if not hasattr(self, 'find_entry'):
            return
        
        search_text = self.find_entry.get()
        if not search_text:
            return
        
        # Get current cursor position
        start_pos = self.text_widget.index(tk.INSERT)
        
        # Search from current position
        flags = []
        if not self.case_sensitive_var.get():
            flags.append("-nocase")
        
        try:
            pos = self.text_widget.search(search_text, start_pos, tk.END, *flags)
            if pos:
                # Select found text
                end_pos = f"{pos}+{len(search_text)}c"
                self.text_widget.tag_remove(tk.SEL, 1.0, tk.END)
                self.text_widget.tag_add(tk.SEL, pos, end_pos)
                self.text_widget.mark_set(tk.INSERT, end_pos)
                self.text_widget.see(pos)
            else:
                # Search from beginning
                pos = self.text_widget.search(search_text, 1.0, start_pos, *flags)
                if pos:
                    end_pos = f"{pos}+{len(search_text)}c"
                    self.text_widget.tag_remove(tk.SEL, 1.0, tk.END)
                    self.text_widget.tag_add(tk.SEL, pos, end_pos)
                    self.text_widget.mark_set(tk.INSERT, end_pos)
                    self.text_widget.see(pos)
                else:
                    messagebox.showinfo("Find", "Text not found")
        except tk.TclError:
            pass
    
    def find_previous(self):
        """Find previous occurrence"""
        if not hasattr(self, 'find_entry'):
            return
        
        search_text = self.find_entry.get()
        if not search_text:
            return
        
        # Get current cursor position
        start_pos = self.text_widget.index(tk.INSERT)
        
        # Search backwards from current position
        flags = ["-backwards"]
        if not self.case_sensitive_var.get():
            flags.append("-nocase")
        
        try:
            pos = self.text_widget.search(search_text, start_pos, 1.0, *flags)
            if pos:
                # Select found text
                end_pos = f"{pos}+{len(search_text)}c"
                self.text_widget.tag_remove(tk.SEL, 1.0, tk.END)
                self.text_widget.tag_add(tk.SEL, pos, end_pos)
                self.text_widget.mark_set(tk.INSERT, pos)
                self.text_widget.see(pos)
            else:
                # Search from end
                pos = self.text_widget.search(search_text, tk.END, start_pos, *flags)
                if pos:
                    end_pos = f"{pos}+{len(search_text)}c"
                    self.text_widget.tag_remove(tk.SEL, 1.0, tk.END)
                    self.text_widget.tag_add(tk.SEL, pos, end_pos)
                    self.text_widget.mark_set(tk.INSERT, pos)
                    self.text_widget.see(pos)
                else:
                    messagebox.showinfo("Find", "Text not found")
        except tk.TclError:
            pass
    
    def replace_find_next(self):
        """Find next in replace dialog"""
        if not hasattr(self, 'replace_find_entry'):
            return
        
        search_text = self.replace_find_entry.get()
        if not search_text:
            return
        
        start_pos = self.text_widget.index(tk.INSERT)
        flags = []
        if not self.replace_case_sensitive_var.get():
            flags.append("-nocase")
        
        try:
            pos = self.text_widget.search(search_text, start_pos, tk.END, *flags)
            if pos:
                end_pos = f"{pos}+{len(search_text)}c"
                self.text_widget.tag_remove(tk.SEL, 1.0, tk.END)
                self.text_widget.tag_add(tk.SEL, pos, end_pos)
                self.text_widget.mark_set(tk.INSERT, end_pos)
                self.text_widget.see(pos)
            else:
                messagebox.showinfo("Find", "Text not found")
        except tk.TclError:
            pass
    
    def replace_current(self):
        """Replace current selection"""
        if not hasattr(self, 'replace_find_entry'):
            return
        
        try:
            selection = self.text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            search_text = self.replace_find_entry.get()
            replace_text = self.replace_entry.get()
            
            if selection == search_text or (not self.replace_case_sensitive_var.get() and 
                                          selection.lower() == search_text.lower()):
                self.text_widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                self.text_widget.insert(tk.INSERT, replace_text)
                self.replace_find_next()
        except tk.TclError:
            self.replace_find_next()
    
    def replace_all(self):
        """Replace all occurrences"""
        if not hasattr(self, 'replace_find_entry'):
            return
        
        search_text = self.replace_find_entry.get()
        replace_text = self.replace_entry.get()
        
        if not search_text:
            return
        
        content = self.text_widget.get(1.0, tk.END + '-1c')
        
        if self.replace_case_sensitive_var.get():
            new_content = content.replace(search_text, replace_text)
        else:
            # Case insensitive replace
            new_content = re.sub(re.escape(search_text), replace_text, content, flags=re.IGNORECASE)
        
        if new_content != content:
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(1.0, new_content)
            count = content.count(search_text) if self.replace_case_sensitive_var.get() else len(re.findall(re.escape(search_text), content, re.IGNORECASE))
            messagebox.showinfo("Replace All", f"Replaced {count} occurrences")
        else:
            messagebox.showinfo("Replace All", "No occurrences found")
    
    def on_text_change(self, event=None):
        """Handle text change events"""
        self.update_cursor_position()
        self.update_character_count()
        self.update_line_numbers()
    
    def on_cursor_move(self, event=None):
        """Handle cursor movement"""
        self.parent.after_idle(self.update_cursor_position)
    
    def on_modified(self, event=None):
        """Handle text modification"""
        if self.text_widget.edit_modified():
            self.is_modified = True
            self.update_title()
            self.text_widget.edit_modified(False)
    
    def update_cursor_position(self):
        """Update cursor position in status bar"""
        try:
            current_pos = self.text_widget.index(tk.INSERT)
            line, col = map(int, current_pos.split('.'))
            self.cursor_pos_var.set(f"Line {line}, Col {col + 1}")
        except:
            pass
    
    def update_character_count(self):
        """Update character count in status bar"""
        try:
            content = self.text_widget.get(1.0, tk.END + '-1c')
            char_count = len(content)
            word_count = len(content.split())
            self.char_count_var.set(f"{char_count} chars, {word_count} words")
        except:
            pass
    
    def update_line_numbers(self):
        """Update line numbers"""
        self.line_numbers.config(state='normal')
        self.line_numbers.delete(1.0, tk.END)
        
        # Get number of lines in text widget
        line_count = int(self.text_widget.index('end-1c').split('.')[0])
        
        # Generate line numbers
        line_numbers_string = '\n'.join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.insert(1.0, line_numbers_string)
        
        self.line_numbers.config(state='disabled')
    
    def update_title(self):
        """Update window title"""
        title = ""
        if self.current_file:
            title = os.path.basename(self.current_file)
        else:
            title = "New File"
        
        if self.is_modified:
            title = "* " + title
        
        # This would be called by parent window
        # self.parent.title(f"Text Editor - {title}")
    
    def ask_save_changes(self):
        """Ask user to save changes"""
        if self.is_modified:
            result = messagebox.askyesnocancel(
                "Save Changes",
                "Do you want to save changes to the current file?"
            )
            if result is True:  # Yes
                return self.save_file()
            elif result is False:  # No
                return True
            else:  # Cancel
                return False
        return True
    
    def get_current_file(self):
        """Get current file path"""
        return self.current_file
    
    def get_text_content(self):
        """Get text content"""
        return self.text_widget.get(1.0, tk.END + '-1c')
    
    def set_text_content(self, content):
        """Set text content"""
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(1.0, content)
        self.update_line_numbers()
    
    def is_file_modified(self):
        """Check if file is modified"""
        return self.is_modified