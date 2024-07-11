import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from PIL import Image, ImageTk, ImageEnhance, ImageFilter
import pytesseract
import re
import json
import cv2
import numpy as np
import os
import webbrowser

# Set up logging
import logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SettingsDialog(simpledialog.Dialog):
    def __init__(self, parent, title, settings):
        self.settings = settings
        super().__init__(parent, title)

    def body(self, master):
        tk.Label(master, text="In-game Name:").grid(row=0, sticky=tk.W)
        self.name_entry = tk.Entry(master)
        self.name_entry.grid(row=0, column=1)
        self.name_entry.insert(0, self.settings.get('username', ''))

        tk.Label(master, text="Tesseract-OCR Path:").grid(row=1, sticky=tk.W)
        self.tesseract_entry = tk.Entry(master)
        self.tesseract_entry.grid(row=1, column=1)
        self.tesseract_entry.insert(0, self.settings.get('tesseract_path', ''))
        self.browse_button = tk.Button(master, text="Browse", command=self.browse_tesseract)
        self.browse_button.grid(row=1, column=2)

        tk.Label(master, text="PSM Mode:").grid(row=2, sticky=tk.W)
        self.psm_var = tk.StringVar(value=self.settings.get('psm', '6'))
        self.psm_options = [str(i) for i in range(14)]
        self.psm_menu = tk.OptionMenu(master, self.psm_var, *self.psm_options)
        self.psm_menu.grid(row=2, column=1)

        tk.Label(master, text="OEM Mode:").grid(row=3, sticky=tk.W)
        self.oem_var = tk.StringVar(value=self.settings.get('oem', '3'))
        self.oem_options = ['0', '1', '2', '3']
        self.oem_menu = tk.OptionMenu(master, self.oem_var, *self.oem_options)
        self.oem_menu.grid(row=3, column=1)

        return self.name_entry

    def browse_tesseract(self):
        path = filedialog.askdirectory()
        if path:
            self.tesseract_entry.delete(0, tk.END)
            self.tesseract_entry.insert(0, path)

    def apply(self):
        self.settings['username'] = self.name_entry.get()
        self.settings['tesseract_path'] = self.tesseract_entry.get()
        self.settings['psm'] = self.psm_var.get()
        self.settings['oem'] = self.oem_var.get()

class ImageParserApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Image Parser App")
        self.root.configure(bg='black')

        # Load and display logo
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "KalSinn_Patchyt.png")
        if os.path.exists(logo_path):
            self.logo = Image.open(logo_path)
            self.logo = self.logo.resize((50, 50), Image.LANCZOS)
            self.logo_tk = ImageTk.PhotoImage(self.logo)
            self.logo_label = tk.Label(self.root, image=self.logo_tk, bg='black')
            self.logo_label.grid(row=0, column=0, padx=10, pady=10)
        else:
            print(f"Logo file not found at {logo_path}")

        self.title_label = tk.Label(self.root, text="Image Parser App", bg='black', fg='white', cursor="hand2")
        self.title_label.grid(row=0, column=1, sticky=tk.W)
        self.title_label.bind("<Button-1>", lambda e: webbrowser.open_new("http://ImageParserApp.freeap.io"))

        self.settings_button = tk.Button(self.root, text="Settings", command=self.open_settings, bg='gray', fg='black')
        self.settings_button.grid(row=1, column=0, pady=10)

        self.import_button = tk.Button(self.root, text="Import Image", command=self.import_image, bg='gray', fg='black')
        self.import_button.grid(row=1, column=1, pady=10)

        self.process_button = tk.Button(self.root, text="Process Image", command=self.process_image, bg='gray', fg='black')
        self.process_button.grid(row=1, column=2, pady=10)

        self.flag_var = tk.StringVar(value="Team")
        self.team_radio = tk.Radiobutton(self.root, text="Team", variable=self.flag_var, value="Team", bg='black', fg='white', selectcolor='black')
        self.enemy_radio = tk.Radiobutton(self.root, text="Enemy", variable=self.flag_var, value="Enemy", bg='black', fg='white', selectcolor='black')
        self.team_radio.grid(row=2, column=0, pady=5)
        self.enemy_radio.grid(row=2, column=1, pady=5)

        self.result_text = tk.Text(self.root, wrap=tk.WORD, bg='black', fg='white', state=tk.DISABLED)
        self.result_text.grid(row=3, column=0, columnspan=3, padx=10, pady=10)

        self.load_settings()
        self.check_tesseract_installation()

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = {
                'username': '',
                'tesseract_path': '',
                'psm': '6',
                'oem': '3'
            }
            self.save_settings()

    def save_settings(self):
        with open('settings.json', 'w') as f:
            json.dump(self.settings, f)

    def open_settings(self):
        dialog = SettingsDialog(self.root, "Settings", self.settings)
        self.root.wait_window(dialog)
        self.save_settings()
        self.check_tesseract_installation()

    def check_tesseract_installation(self):
        try:
            pytesseract.get_tesseract_version()
        except pytesseract.pytesseract.TesseractNotFoundError:
            if self.settings['tesseract_path']:
                pytesseract.pytesseract.tesseract_cmd = os.path.join(self.settings['tesseract_path'], 'tesseract.exe')
                try:
                    pytesseract.get_tesseract_version()
                except:
                    self.prompt_tesseract_directory()
            else:
                self.prompt_tesseract_directory()

    def prompt_tesseract_directory(self):
        tesseract_dir = filedialog.askdirectory(title="Select Tesseract-OCR Installation Directory")
        if tesseract_dir:
            tesseract_executable_path = os.path.join(tesseract_dir, 'tesseract.exe')
            if os.path.exists(tesseract_executable_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_executable_path
                self.settings['tesseract_path'] = tesseract_dir
                self.save_settings()
            else:
                messagebox.showerror("Error", "Tesseract executable not found in the selected directory.")
                self.prompt_tesseract_directory()

    def import_image(self):
        self.image_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if self.image_path:
            self.display_image(self.image_path)

    def display_image(self, image_path):
        image = Image.open(image_path)
        image.thumbnail((200, 200))
        image_tk = ImageTk.PhotoImage(image)
        self.image_label = tk.Label(self.root, image=image_tk)
        self.image_label.image = image_tk  # Keep a reference
        self.image_label.grid(row=3, column=3, padx=10, pady=10)

    def process_image(self):
        if hasattr(self, 'image_path') and self.image_path:
            lines = self.parse_image(self.image_path)
            self.display_result(lines)
            self.write_names_to_file(lines, self.flag_var.get())

    def parse_image(self, image_path):
        image = Image.open(image_path)
        enhanced_image = self.enhance_image(image)

        custom_config = f'--oem 3 --psm 6 -c preserve_interword_spaces=1'
        text = pytesseract.image_to_string(enhanced_image, config=custom_config)

        text = re.sub(r'[;:]', '', text)
        text = re.sub(r'(?<!\w)[iI](?!\w)', 'i', text)
        text = re.sub(r'(?<!\w)[O0](?!\w)', 'D', text)

        lines = [re.sub(r'\s+', ' ', line.strip()) for line in text.split('\n') if line.strip()]

        return lines

    def enhance_image(self, image):
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

        # Convert to numpy array for OpenCV processing
        open_cv_image = np.array(filtered_image)

        # Apply adaptive thresholding
        adaptive_thresh_image = cv2.adaptiveThreshold(open_cv_image, 255,
                                                      cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                      cv2.THRESH_BINARY, 11, 2)

        # Upscale the image
        upscale_factor = 2
        upscaled_image = cv2.resize(adaptive_thresh_image, None, fx=upscale_factor, fy=upscale_factor,
                                    interpolation=cv2.INTER_LINEAR)

        # Convert back to PIL Image
        enhanced_image = Image.fromarray(upscaled_image)

        return enhanced_image

    def write_names_to_file(self, names, flag):
        file_name = 'team.txt' if flag == 'Team' else 'enemy.txt'
        with open(file_name, 'w') as f:
            for name in names:
                f.write(name + '\n')
        logging.info(f"Names parsed and written to {file_name}")

    def display_result(self, lines):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete('1.0', tk.END)
        self.result_text.insert(tk.END, '\n'.join(lines))
        self.result_text.config(state=tk.DISABLED)

if __name__ == "__main__":
    app = ImageParserApp()
    app.root.mainloop()