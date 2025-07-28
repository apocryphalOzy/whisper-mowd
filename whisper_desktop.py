#!/usr/bin/env python
"""
Whisper Desktop Application
A simple GUI for audio transcription using OpenAI Whisper
No browser required!
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
import threading
import os
from pathlib import Path

try:
    import whisper
except ImportError:
    print("ERROR: Whisper not installed!")
    print("Please run: pip install openai-whisper")
    input("Press Enter to exit...")
    exit(1)

class WhisperDesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Whisper Audio Transcription")
        self.root.geometry("800x600")
        
        # Set icon (if available)
        try:
            self.root.iconbitmap(default='icon.ico')
        except:
            pass
        
        # Variables
        self.file_path = None
        self.model = None
        self.model_size = "tiny"
        self.is_processing = False
        
        # Create GUI
        self.create_widgets()
        
        # Load model in background
        self.load_model()
    
    def create_widgets(self):
        # Title
        title_label = tk.Label(self.root, text="Whisper Audio Transcription", 
                              font=("Arial", 20, "bold"))
        title_label.pack(pady=10)
        
        # Info label
        info_label = tk.Label(self.root, 
                             text="Select an audio file (MP3, WAV, M4A, etc.) to transcribe",
                             font=("Arial", 12))
        info_label.pack(pady=5)
        
        # File selection frame
        file_frame = tk.Frame(self.root)
        file_frame.pack(pady=10)
        
        self.file_label = tk.Label(file_frame, text="No file selected", 
                                  font=("Arial", 10), fg="gray")
        self.file_label.pack(side=tk.LEFT, padx=5)
        
        select_btn = tk.Button(file_frame, text="Select Audio File", 
                              command=self.select_file,
                              bg="#4CAF50", fg="white", font=("Arial", 12),
                              padx=20, pady=5)
        select_btn.pack(side=tk.LEFT, padx=5)
        
        # Model selection
        model_frame = tk.Frame(self.root)
        model_frame.pack(pady=5)
        
        tk.Label(model_frame, text="Model:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        self.model_var = tk.StringVar(value="tiny")
        model_menu = ttk.Combobox(model_frame, textvariable=self.model_var,
                                 values=["tiny", "base", "small", "medium", "large"],
                                 state="readonly", width=10)
        model_menu.pack(side=tk.LEFT)
        model_menu.bind("<<ComboboxSelected>>", self.on_model_change)
        
        self.model_status = tk.Label(model_frame, text="Loading model...", 
                                    font=("Arial", 9), fg="orange")
        self.model_status.pack(side=tk.LEFT, padx=10)
        
        # Transcribe button
        self.transcribe_btn = tk.Button(self.root, text="Transcribe Audio", 
                                       command=self.transcribe,
                                       bg="#2196F3", fg="white", 
                                       font=("Arial", 14, "bold"),
                                       padx=30, pady=10, state=tk.DISABLED)
        self.transcribe_btn.pack(pady=20)
        
        # Progress bar
        self.progress = ttk.Progressbar(self.root, mode='indeterminate', length=400)
        self.progress.pack(pady=5)
        
        # Status label
        self.status_label = tk.Label(self.root, text="Ready", 
                                    font=("Arial", 10), fg="green")
        self.status_label.pack()
        
        # Results text area
        result_frame = tk.Frame(self.root)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(result_frame, text="Transcription Result:", 
                font=("Arial", 12, "bold")).pack(anchor=tk.W)
        
        self.result_text = scrolledtext.ScrolledText(result_frame, 
                                                     wrap=tk.WORD, 
                                                     height=15,
                                                     font=("Arial", 11))
        self.result_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Buttons frame
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        
        copy_btn = tk.Button(btn_frame, text="Copy Text", 
                            command=self.copy_text,
                            bg="#FF9800", fg="white", font=("Arial", 10),
                            padx=15, pady=5)
        copy_btn.pack(side=tk.LEFT, padx=5)
        
        save_btn = tk.Button(btn_frame, text="Save to File", 
                            command=self.save_text,
                            bg="#9C27B0", fg="white", font=("Arial", 10),
                            padx=15, pady=5)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = tk.Button(btn_frame, text="Clear", 
                             command=self.clear_text,
                             bg="#F44336", fg="white", font=("Arial", 10),
                             padx=15, pady=5)
        clear_btn.pack(side=tk.LEFT, padx=5)
    
    def load_model(self):
        """Load Whisper model in background"""
        def load():
            try:
                self.model_status.config(text=f"Loading {self.model_size} model...")
                self.model = whisper.load_model(self.model_size)
                self.model_status.config(text=f"Model loaded ({self.model_size})", fg="green")
                self.update_button_state()
            except Exception as e:
                self.model_status.config(text="Model load failed", fg="red")
                messagebox.showerror("Error", f"Failed to load model: {str(e)}")
        
        threading.Thread(target=load, daemon=True).start()
    
    def on_model_change(self, event=None):
        """Handle model selection change"""
        new_size = self.model_var.get()
        if new_size != self.model_size:
            self.model_size = new_size
            self.model = None
            self.update_button_state()
            self.load_model()
    
    def select_file(self):
        """Open file dialog to select audio file"""
        filename = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[
                ("Audio Files", "*.mp3 *.wav *.m4a *.flac *.ogg *.mp4 *.avi *.mkv"),
                ("All Files", "*.*")
            ]
        )
        
        if filename:
            self.file_path = filename
            self.file_label.config(text=os.path.basename(filename), fg="black")
            self.update_button_state()
    
    def update_button_state(self):
        """Update transcribe button state"""
        if self.file_path and self.model and not self.is_processing:
            self.transcribe_btn.config(state=tk.NORMAL)
        else:
            self.transcribe_btn.config(state=tk.DISABLED)
    
    def transcribe(self):
        """Transcribe the selected audio file"""
        if not self.file_path or not self.model:
            return
        
        self.is_processing = True
        self.transcribe_btn.config(state=tk.DISABLED)
        self.progress.start(10)
        self.status_label.config(text="Transcribing... This may take a while.", fg="orange")
        self.result_text.delete(1.0, tk.END)
        
        def process():
            try:
                # Transcribe
                result = self.model.transcribe(self.file_path)
                text = result["text"].strip()
                
                # Update GUI in main thread
                self.root.after(0, self.on_transcription_complete, text)
                
            except Exception as e:
                self.root.after(0, self.on_transcription_error, str(e))
        
        threading.Thread(target=process, daemon=True).start()
    
    def on_transcription_complete(self, text):
        """Handle successful transcription"""
        self.progress.stop()
        self.is_processing = False
        self.status_label.config(text="Transcription complete!", fg="green")
        self.result_text.insert(1.0, text)
        self.update_button_state()
    
    def on_transcription_error(self, error_msg):
        """Handle transcription error"""
        self.progress.stop()
        self.is_processing = False
        self.status_label.config(text="Transcription failed", fg="red")
        messagebox.showerror("Transcription Error", f"Failed to transcribe audio:\n{error_msg}")
        self.update_button_state()
    
    def copy_text(self):
        """Copy transcription to clipboard"""
        text = self.result_text.get(1.0, tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_label.config(text="Text copied to clipboard!", fg="green")
    
    def save_text(self):
        """Save transcription to file"""
        text = self.result_text.get(1.0, tk.END).strip()
        if not text:
            messagebox.showwarning("No Text", "No transcription to save")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(text)
                self.status_label.config(text=f"Saved to {os.path.basename(filename)}", fg="green")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save file: {str(e)}")
    
    def clear_text(self):
        """Clear the result text"""
        self.result_text.delete(1.0, tk.END)
        self.status_label.config(text="Cleared", fg="green")

def main():
    root = tk.Tk()
    app = WhisperDesktopApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()