import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from PIL import Image, ImageTk
import os
import json
import logging
import pytesseract
import webbrowser
import re
import cv2
import numpy as np

# Set up logging
logging.basicConfig(filename='image_parser.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def enhance_image(image):
    # Convert PIL Image to OpenCV format
    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    # Convert to grayscale
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

    # Apply slight Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

    # Invert the image (black text on white background)
    inverted = cv2.bitwise_not(thresh)

    # Apply slight dilation to make text more prominent
    kernel = np.ones((2, 2), np.uint8)
    dilated = cv2.dilate(inverted, kernel, iterations=1)

    # Convert back to PIL Image
    return Image.fromarray(cv2.cvtColor(dilated, cv2.COLOR_GRAY2RGB))


def parse_image(image_path, preprocess):
    image = Image.open(image_path)

    if preprocess:
        image = enhance_image(image)

    # Use Tesseract with custom configuration
    custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
    text = pytesseract.image_to_string(image, config=custom_config)

    # Post-process text
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    # Clean up lines while preserving original characters
    cleaned_lines = []
    for line in lines:
        # Remove any non-printable characters
        cleaned_line = ''.join(char for char in line if char.isprintable())
        # Remove leading/trailing whitespace
        cleaned_line = cleaned_line.strip()
        if cleaned_line:
            cleaned_lines.append(cleaned_line)

    return image, cleaned_lines


def write_names_to_file(names, flag, settings):
    file_name = os.path.join(settings['file_path'], 'team.txt' if flag == 'Team' else 'enemy.txt')
    with open(file_name, 'w') as f:
        for name in names:
            f.write(name + '\n')


def process_image(image_path, flag, settings, preprocess):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"The file {image_path} does not exist.")

    if flag not in ['Team', 'Enemy']:
        raise ValueError("The flag must be either 'Team' or 'Enemy'.")

    enhanced_image, names = parse_image(image_path, preprocess)
    write_names_to_file(names, flag, settings)
    logging.info(
        f"Names parsed and written to {'team.txt' if flag == 'Team' else 'enemy.txt'} in {settings['file_path']}.")
    return enhanced_image, names


class SettingsDialog(simpledialog.Dialog):
    def __init__(self, parent, title, settings):
        self.settings = settings
        super().__init__(parent, title)

    def body(self, master):
        tk.Label(master, text="Tesseract-OCR Path:").grid(row=0, column=0, sticky='w')
        self.tesseract_entry = tk.Entry(master, width=50)
        self.tesseract_entry.grid(row=0, column=1, padx=10, pady=5)
        self.tesseract_entry.insert(0, self.settings.get('tesseract_path', ''))

        self.browse_tesseract_button = tk.Button(master, text="Browse", command=self.browse_tesseract)
        self.browse_tesseract_button.grid(row=0, column=2, padx=10, pady=5)

        tk.Label(master, text="File Save Path:").grid(row=1, column=0, sticky='w')
        self.file_path_entry = tk.Entry(master, width=50)
        self.file_path_entry.grid(row=1, column=1, padx=10, pady=5)
        self.file_path_entry.insert(0, self.settings.get('file_path', ''))

        self.browse_file_path_button = tk.Button(master, text="Browse", command=self.browse_file_path)
        self.browse_file_path_button.grid(row=1, column=2, padx=10, pady=5)

        return self.tesseract_entry

    def browse_tesseract(self):
        path = filedialog.askdirectory()
        if path:
            self.tesseract_entry.delete(0, tk.END)
            self.tesseract_entry.insert(0, path)

    def browse_file_path(self):
        path = filedialog.askdirectory()
        if path:
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, path)

    def apply(self):
        self.settings['tesseract_path'] = self.tesseract_entry.get()
        self.settings['file_path'] = self.file_path_entry.get()


class ImageParserApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image Parser App")
        self.configure(bg='#1e1e1e')
        self.settings = self.load_settings()
        self.preprocess_var = tk.BooleanVar(value=True)

        # Load and display logo
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "KalSinn_Patchyt.png")
        if os.path.exists(logo_path):
            self.logo = Image.open(logo_path)
            self.logo = self.logo.resize((50, 50), Image.LANCZOS)
            self.logo_tk = ImageTk.PhotoImage(self.logo)
            self.logo_label = tk.Label(self, image=self.logo_tk, bg='#1e1e1e')
            self.logo_label.grid(row=0, column=0, padx=(10, 5), pady=(10, 5), sticky="w")

        self.title_label = tk.Label(self, text="Image Parser App", bg='#1e1e1e', fg='#a0a0a0',
                                    font=("Helvetica", 16, "bold"), cursor="hand2")
        self.title_label.grid(row=0, column=1, pady=(10, 5), sticky="w")
        self.title_label.bind("<Button-1>", self.open_website)

        # Buttons row
        self.buttons_frame = tk.Frame(self, bg='#1e1e1e')
        self.buttons_frame.grid(row=1, column=0, columnspan=3, pady=(10, 10))

        self.settings_button = tk.Button(self.buttons_frame, text="Settings", command=self.open_settings, bg='#3c3f41',
                                         fg='#a0a0a0')
        self.settings_button.pack(side=tk.LEFT, padx=(10, 5))

        self.browse_button = tk.Button(self.buttons_frame, text="Browse", command=self.browse_image, bg='#3c3f41',
                                       fg='#a0a0a0')
        self.browse_button.pack(side=tk.LEFT, padx=(5, 5))

        self.process_button = tk.Button(self.buttons_frame, text="Process", command=self.process_image, bg='#3c3f41',
                                        fg='#a0a0a0')
        self.process_button.pack(side=tk.LEFT, padx=(5, 10))

        self.preprocess_check = tk.Checkbutton(self, text="Enable Pre-processing", variable=self.preprocess_var,
                                               bg='#1e1e1e', fg='#a0a0a0')
        self.preprocess_check.grid(row=2, column=0, columnspan=3, pady=(5, 10))

        self.label = tk.Label(self, text="Select an image and choose a flag (Team or Enemy):", bg='#1e1e1e',
                              fg='#a0a0a0')
        self.label.grid(row=3, column=0, columnspan=3, pady=(10, 5))

        self.flag_var = tk.StringVar(value="Team")
        self.team_radio = tk.Radiobutton(self, text="Team", variable=self.flag_var, value="Team", bg='#1e1e1e',
                                         fg='#a0a0a0', selectcolor='#1e1e1e')
        self.enemy_radio = tk.Radiobutton(self, text="Enemy", variable=self.flag_var, value="Enemy", bg='#1e1e1e',
                                          fg='#a0a0a0', selectcolor='#1e1e1e')

        # Updated radio button layout
        self.team_radio.grid(row=4, column=0, padx=(0, 10), pady=(5, 10), sticky="e")
        self.enemy_radio.grid(row=4, column=1, padx=(10, 0), pady=(5, 10), sticky="w")
        self.image_path_entry = tk.Entry(self, width=50, bg='#1e1e1e', fg='#a0a0a0')
        self.image_path_entry.grid(row=5, column=0, columnspan=3, pady=(5, 10))

        # Results frame
        self.results_frame = tk.Frame(self, bg='#1e1e1e')
        self.results_frame.grid(row=6, column=0, columnspan=3, pady=(10, 10), sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_columnconfigure(1, weight=1)

        # Create a canvas and scrollbar for the results frame
        self.canvas = tk.Canvas(self.results_frame, bg='#1e1e1e', highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.results_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='#1e1e1e')

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.check_tesseract_installation()

        # Adjust the window size to fit all elements
        self.update_idletasks()
        self.minsize(self.winfo_width(), self.winfo_height())
        self.geometry(f"{self.winfo_width()}x{self.winfo_height()}")

    def open_website(self, event):
        webbrowser.open_new("http://ImageParserApp.freeap.io")

    def open_settings(self):
        dialog = SettingsDialog(self, "Settings", self.settings)
        self.wait_window(dialog)
        if dialog.settings:
            self.settings = dialog.settings
            self.save_settings()
            self.check_tesseract_installation()

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {'tesseract_path': '', 'file_path': ''}

    def save_settings(self):
        with open('settings.json', 'w') as f:
            json.dump(self.settings, f)

    def get_tesseract_path(self):
        return self.settings.get('tesseract_path', '')

    def set_tesseract_path(self, path):
        self.settings['tesseract_path'] = path
        self.save_settings()
        pytesseract.pytesseract.tesseract_cmd = os.path.join(path, 'tesseract.exe')

    def browse_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if file_path:
            self.image_path_entry.delete(0, tk.END)
            self.image_path_entry.insert(0, file_path)

    def process_image(self):
        image_path = self.image_path_entry.get()
        flag = self.flag_var.get()
        preprocess = self.preprocess_var.get()
        if not image_path:
            messagebox.showerror("Error", "Please select an image file.")
            return
        if not flag:
            messagebox.showerror("Error", "Please select a flag (Team or Enemy).")
            return
        try:
            enhanced_image, names = process_image(image_path, flag, self.settings, preprocess)
            self.display_results(enhanced_image, names)
            messagebox.showinfo("Success",
                                f"Names parsed and written to {'team.txt' if flag == 'Team' else 'enemy.txt'}.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def display_results(self, enhanced_image, names):
        # Clear previous results
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Resize image to fit the frame
        width, height = enhanced_image.size
        new_width = 300
        new_height = int(height * (new_width / width))
        resized_image = enhanced_image.resize((new_width, new_height), Image.LANCZOS)

        # Convert the image for tkinter
        tk_image = ImageTk.PhotoImage(resized_image)

        # Create and place the image label
        image_label = tk.Label(self.scrollable_frame, image=tk_image, bg='#1e1e1e')
        image_label.image = tk_image  # Keep a reference to prevent garbage collection
        image_label.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nw")

        # Create and place the names label
        names_text = "\n".join(names)
        names_label = tk.Label(self.scrollable_frame, text=names_text, bg='#1e1e1e', fg='#a0a0a0', justify=tk.LEFT)
        names_label.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nw")

    def check_tesseract_installation(self):
        tesseract_path = self.get_tesseract_path()
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = os.path.join(tesseract_path, 'tesseract.exe')
            try:
                pytesseract.get_tesseract_version()
            except pytesseract.pytesseract.TesseractNotFoundError:
                self.prompt_tesseract_directory()
        else:
            self.prompt_tesseract_directory()

    def prompt_tesseract_directory(self):
        tesseract_dir = filedialog.askdirectory(title="Select Tesseract-OCR Installation Directory")
        if tesseract_dir:
            tesseract_executable_path = os.path.join(tesseract_dir, 'tesseract.exe')
            if os.path.exists(tesseract_executable_path):
                self.set_tesseract_path(tesseract_dir)
            else:
                messagebox.showerror("Error", "Tesseract executable not found in the selected directory.")
                self.prompt_tesseract_directory()


if __name__ == "__main__":
    app = ImageParserApp()
    app.mainloop()
