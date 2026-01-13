import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import subprocess
import sys
import os
import json
import threading

CONFIG_FILE = "wnd_to_svg_gui_config.json"

class WndToSvgApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WND to SVG Converter GUI")
        self.root.geometry("600x750")

        # Variables
        self.wnd_file_var = tk.StringVar()
        self.mapped_images_var = tk.StringVar()
        self.textures_dir_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        
        self.svg_file_var = tk.StringVar()
        self.output_wnd_var = tk.StringVar()
        self.update_new_var = tk.BooleanVar(value=False)

        # Load config
        self.load_config()

        # UI Setup
        self.create_widgets()

    def create_widgets(self):
        # 1. Inputs Section
        input_frame = tk.LabelFrame(self.root, text="Configuration", padx=10, pady=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        # WND File
        tk.Label(input_frame, text="WND File:").grid(row=0, column=0, sticky="w")
        tk.Entry(input_frame, textvariable=self.wnd_file_var, width=50).grid(row=0, column=1, padx=5)
        tk.Button(input_frame, text="Browse", command=self.browse_wnd).grid(row=0, column=2)

        # Mapped Images Dir
        tk.Label(input_frame, text="Mapped Images Dir:").grid(row=1, column=0, sticky="w")
        tk.Entry(input_frame, textvariable=self.mapped_images_var, width=50).grid(row=1, column=1, padx=5)
        tk.Button(input_frame, text="Browse", command=lambda: self.browse_dir(self.mapped_images_var)).grid(row=1, column=2)

        # Textures Dir
        tk.Label(input_frame, text="Textures Dir:").grid(row=2, column=0, sticky="w")
        tk.Entry(input_frame, textvariable=self.textures_dir_var, width=50).grid(row=2, column=1, padx=5)
        tk.Button(input_frame, text="Browse", command=lambda: self.browse_dir(self.textures_dir_var)).grid(row=2, column=2)

        # Output Images Dir
        tk.Label(input_frame, text="Extracted Images Dir:").grid(row=3, column=0, sticky="w")
        tk.Entry(input_frame, textvariable=self.output_dir_var, width=50).grid(row=3, column=1, padx=5)
        tk.Button(input_frame, text="Browse", command=lambda: self.browse_dir(self.output_dir_var)).grid(row=3, column=2)

        # 2. Update Options
        update_frame = tk.LabelFrame(self.root, text="Update Options", padx=10, pady=10)
        update_frame.pack(fill="x", padx=10, pady=5)

        # SVG File (for updates)
        tk.Label(update_frame, text="SVG File (Input):").grid(row=0, column=0, sticky="w")
        tk.Entry(update_frame, textvariable=self.svg_file_var, width=50).grid(row=0, column=1, padx=5)
        tk.Button(update_frame, text="Browse", command=self.browse_svg).grid(row=0, column=2)

        # Output WND (optional)
        tk.Label(update_frame, text="Output WND (Optional):").grid(row=1, column=0, sticky="w")
        tk.Entry(update_frame, textvariable=self.output_wnd_var, width=50).grid(row=1, column=1, padx=5)
        tk.Button(update_frame, text="Save As", command=self.browse_save_wnd).grid(row=1, column=2)

        # Update New Checkbox
        tk.Checkbutton(update_frame, text="Create '_NEW.wnd' automatically (--updatenew)", variable=self.update_new_var).grid(row=2, column=0, columnspan=3, sticky="w")

        # 3. Action Buttons
        btn_frame = tk.Frame(self.root, pady=10)
        btn_frame.pack(fill="x", padx=10)

        tk.Button(btn_frame, text="Generate SVG", command=self.generate_svg, bg="#dddddd", height=2).pack(side="left", expand=True, fill="x", padx=5)
        tk.Button(btn_frame, text="Update WND", command=self.update_wnd, bg="#dddddd", height=2).pack(side="left", expand=True, fill="x", padx=5)

        # 4. Console Output
        tk.Label(self.root, text="Output Log:").pack(anchor="w", padx=10)
        self.console = scrolledtext.ScrolledText(self.root, height=15)
        self.console.pack(fill="both", expand=True, padx=10, pady=5)

        # Status Bar
        self.status = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor="w")
        self.status.pack(side="bottom", fill="x")

    def browse_wnd(self):
        initial_dir = os.getcwd()
        current_val = self.wnd_file_var.get()
        if current_val:
            if os.path.isdir(current_val):
                initial_dir = current_val
            elif os.path.exists(os.path.dirname(current_val)):
                initial_dir = os.path.dirname(current_val)
                
        filename = filedialog.askopenfilename(initialdir=initial_dir, filetypes=[("WND Files", "*.wnd"), ("All Files", "*.*")])
        if filename:
            self.wnd_file_var.set(os.path.normpath(filename))
            
            # Auto-update SVG path to match WND
            base = os.path.splitext(filename)[0]
            svg_path = base + ".svg"
            self.svg_file_var.set(os.path.normpath(svg_path))
            
            self.save_config()

    def browse_svg(self):
        initial_dir = os.getcwd()
        current_val = self.svg_file_var.get()
        if current_val:
            if os.path.isdir(current_val):
                initial_dir = current_val
            elif os.path.exists(os.path.dirname(current_val)):
                initial_dir = os.path.dirname(current_val)

        filename = filedialog.askopenfilename(initialdir=initial_dir, filetypes=[("SVG Files", "*.svg"), ("All Files", "*.*")])
        if filename:
            self.svg_file_var.set(os.path.normpath(filename))
            self.save_config()
            
    def browse_save_wnd(self):
        filename = filedialog.asksaveasfilename(defaultextension=".wnd", filetypes=[("WND Files", "*.wnd")])
        if filename:
            self.output_wnd_var.set(os.path.normpath(filename))
            self.save_config()

    def browse_dir(self, var):
        dirname = filedialog.askdirectory()
        if dirname:
            var.set(os.path.normpath(dirname))
            self.save_config()

    def load_config(self):
        # Default auto-detection
        def get_default(path):
            return os.path.abspath(path) if os.path.exists(path) else ""

        # Set initial defaults based on existence
        self.mapped_images_var.set(get_default("MappedImages"))
        self.textures_dir_var.set(get_default(os.path.join("Art", "Textures")))
        self.output_dir_var.set(get_default("extracted_images"))
        
        window_dir = get_default("Window")
        if window_dir:
            self.wnd_file_var.set(window_dir)
            self.svg_file_var.set(window_dir)

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.wnd_file_var.set(data.get("wnd_file", ""))
                    
                    # Update from config if keys exist
                    if "mapped_images_dir" in data:
                        self.mapped_images_var.set(data["mapped_images_dir"])
                    if "textures_dir" in data:
                        self.textures_dir_var.set(data["textures_dir"])
                    if "output_dir" in data:
                        self.output_dir_var.set(data["output_dir"])
                        
                    self.svg_file_var.set(data.get("svg_file", ""))
                    self.output_wnd_var.set(data.get("output_wnd", ""))
                    self.update_new_var.set(data.get("update_new", False))
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self):
        data = {
            "wnd_file": self.wnd_file_var.get(),
            "mapped_images_dir": self.mapped_images_var.get(),
            "textures_dir": self.textures_dir_var.get(),
            "output_dir": self.output_dir_var.get(),
            "svg_file": self.svg_file_var.get(),
            "output_wnd": self.output_wnd_var.get(),
            "update_new": self.update_new_var.get()
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def log(self, message):
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)

    def run_command(self, args, cwd=None):
        self.status.config(text="Running...")
        self.console.delete(1.0, tk.END)
        self.log(f"Executing: {' '.join(args)}")
        
        target_cwd = cwd if cwd else os.getcwd()
        self.log(f"Working Directory: {target_cwd}")
        
        def task():
            try:
                # Use sys.executable to ensure we use the same python interpreter
                process = subprocess.Popen(
                    args, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True,
                    cwd=target_cwd
                )
                
                stdout, stderr = process.communicate()
                
                self.root.after(0, lambda: self.log(stdout))
                if stderr:
                    self.root.after(0, lambda: self.log(f"Errors:\n{stderr}"))
                
                self.root.after(0, lambda: self.status.config(text="Done"))
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"Exception: {e}"))
                self.root.after(0, lambda: self.status.config(text="Error"))

        threading.Thread(target=task, daemon=True).start()

    def generate_svg(self):
        wnd = self.wnd_file_var.get()
        if not wnd:
            messagebox.showerror("Error", "Please select a WND file.")
            return
            
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wnd_to_svg.py")
        
        cmd = [
            sys.executable, script_path,
            wnd,
            "--mapped_images_dir", self.mapped_images_var.get(),
            "--textures_dir", self.textures_dir_var.get(),
            "--outdir", self.output_dir_var.get()
        ]
        
        # Determine output directory (CWD)
        # Priority: SVG Field (if dir or file), then WND dir, then CWD
        cwd = os.getcwd()
        svg_val = self.svg_file_var.get()
        if svg_val:
            if os.path.isdir(svg_val):
                cwd = svg_val
            elif os.path.exists(os.path.dirname(svg_val)):
                cwd = os.path.dirname(svg_val)
        elif wnd and os.path.exists(os.path.dirname(wnd)):
             cwd = os.path.dirname(wnd)
             
        self.run_command(cmd, cwd=cwd)

    def update_wnd(self):
        wnd = self.wnd_file_var.get()
        if not wnd:
            messagebox.showerror("Error", "Please select a WND file.")
            return

        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wnd_to_svg.py")

        cmd = [
            sys.executable, script_path,
            wnd,
            "--update"
        ]
        
        if self.update_new_var.get():
            cmd.append("--updatenew")
            
        svg = self.svg_file_var.get()
        if svg:
            cmd.extend(["--svg", svg])
            
        output = self.output_wnd_var.get()
        if output:
            cmd.extend(["--output", output])
            
        self.run_command(cmd)

if __name__ == "__main__":
    root = tk.Tk()
    app = WndToSvgApp(root)
    root.mainloop()
