import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk, ImageEnhance, ImageFilter
import os
import json
import logging
import pytesseract
import webbrowser
import re

# Set up logging
logging.basicConfig(filename='image_parser.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def enhance_image(image):
    # Convert to grayscale
    gray_image = image.convert('L')

    # Increase contrast
    enhancer = ImageEnhance.Contrast(gray_image)
    enhanced_image = enhancer.enhance(2.0)

    # Increase sharpness
    enhancer = ImageEnhance.Sharpness(enhanced_image)
    enhanced_image = enhancer.enhance(2.0)

    # Apply median filter to reduce noise
    filtered_image = enhanced_image.filter(ImageFilter.MedianFilter(size=3))

    return filtered_image


def parse_image(image_path):
    image = Image.open(image_path)
    enhanced_image = enhance_image(image)

    # Use Tesseract with custom configuration
    custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
    text = pytesseract.image_to_string(enhanced_image, config=custom_config)

    # Post-process text to fix common OCR errors
    text = re.sub(r'[;:]', '', text)  # Remove unwanted characters
    text = re.sub(r'(?<!\w)[iI](?!\w)', 'i', text)  # Correct isolated i/I to lowercase i
    text = re.sub(r'(?<!\w)[O0](?!\w)', 'D', text)  # Correct isolated O/0 to uppercase D

    # Split text into lines and filter out empty lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    return lines


def write_names_to_file(names, flag, settings):
    file_name = os.path.join(settings['file_path'], 'team.txt' if flag == 'Team' else 'enemy.txt')
    with open(file_name, 'w') as f:
        for name in names:
            f.write(name + '\n')


def process_image(image_path, flag, settings):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"The file {image_path} does not exist.")

    if flag not in ['Team', 'Enemy']:
        raise ValueError("The flag must be either 'Team' or 'Enemy'.")

    names = parse_image(image_path)
    write_names_to_file(names, flag, settings)
    logging.info(f"Names parsed and written to {'team.txt' if flag == 'Team' else 'enemy.txt'} in {settings['file_path']}.")


# GUI Part
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

        self.settings_button = tk.Button(self.buttons_frame, text="Settings", command=self.open_settings, bg='#3c3f41', fg='#a0a0a0')
        self.settings_button.pack(side=tk.LEFT, padx=(10, 5))

        self.browse_button = tk.Button(self.buttons_frame, text="Browse", command=self.browse_image, bg='#3c3f41', fg='#a0a0a0')
        self.browse_button.pack(side=tk.LEFT, padx=(5, 5))

        self.process_button = tk.Button(self.buttons_frame, text="Process", command=self.process_image, bg='#3c3f41', fg='#a0a0a0')
        self.process_button.pack(side=tk.LEFT, padx=(5, 10))

        self.label = tk.Label(self, text="Select an image and choose a flag (Team or Enemy):", bg='#1e1e1e', fg='#a0a0a0')
        self.label.grid(row=2, column=0, columnspan=3, pady=(10, 5))

        self.flag_var = tk.StringVar(value="Team")
        self.team_radio = tk.Radiobutton(self, text="Team", variable=self.flag_var, value="Team", bg='#1e1e1e',
                                         fg='#a0a0a0', selectcolor='#1e1e1e')
        self.enemy_radio = tk.Radiobutton(self, text="Enemy", variable=self.flag_var, value="Enemy", bg='#1e1e1e',
                                          fg='#a0a0a0', selectcolor='#1e1e1e')

        # Updated radio button layout
        self.team_radio.grid(row=3, column=0, padx=(0, 10), pady=(5, 10), sticky="e")
        self.enemy_radio.grid(row=3, column=1, padx=(10, 0), pady=(5, 10), sticky="w")
        self.image_path_entry = tk.Entry(self, width=50, bg='#1e1e1e', fg='#a0a0a0')
        self.image_path_entry.grid(row=5, column=0, columnspan=3, pady=(5, 10))

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
        if not image_path:
            messagebox.showerror("Error", "Please select an image file.")
            return
        if not flag:
            messagebox.showerror("Error", "Please select a flag (Team or Enemy).")
            return
        try:
            process_image(image_path, flag, self.settings)
            messagebox.showinfo("Success",
                                f"Names parsed and written to {'team.txt' if flag == 'Team' else 'enemy.txt'}.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

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
