import os
import json
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext


class ImageParserApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ImageParser OCR Application")
        self.settings = self.load_settings()

        self.image_path_var = tk.StringVar()
        self.result_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=50, height=20)

        # GUI Components
        self.setup_gui()

    def setup_gui(self):
        tk.Label(self.root, text="Image Path:").pack()
        tk.Entry(self.root, textvariable=self.image_path_var, width=50).pack()
        tk.Button(self.root, text="Browse", command=self.browse_image).pack()
        tk.Button(self.root, text="Process", command=self.process_image).pack()
        tk.Button(self.root, text="Settings", command=self.open_settings).pack()
        tk.Button(self.root, text="Capture Screen", command=self.capture_and_process_screen).pack()
        self.preprocess_var = tk.BooleanVar(value=self.settings['preprocess'])
        tk.Checkbutton(self.root, text="Enable Pre-processing", variable=self.preprocess_var).pack()
        self.result_text.pack()

    def browse_image(self):
        file_path = filedialog.askopenfilename()
        self.image_path_var.set(file_path)

    def process_image(self):
        image_path = self.image_path_var.get()
        if not image_path:
            messagebox.showerror("Error", "Please select an image file")
            return
        preprocess = self.preprocess_var.get()
        names = self.parse_image(image_path, preprocess)
        self.result_text.insert(tk.END, "\n".join(names))
        self.write_names_to_file(names, "output.txt")

    def open_settings(self):
        settings_dialog = SettingsDialog(self.root, self.settings)
        self.root.wait_window(settings_dialog.top)

    def capture_and_process_screen(self):
        # Capture screen logic here
        pass

    def load_settings(self):
        default_settings = {"tesseract_path": "C:/Program Files/Tesseract-OCR/tesseract.exe", "save_path": ".",
                            "preprocess": False}
        if os.path.exists("settings.json"):
            with open("settings.json", "r") as file:
                settings = json.load(file)
                return {**default_settings, **settings}  # Merge default settings with loaded settings
        return default_settings

    def save_settings(self):
        self.settings['preprocess'] = self.preprocess_var.get()
        with open("settings.json", "w") as file:
            json.dump(self.settings, file)

    def enhance_image(self, image):
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2)
        image = image.convert('L').filter(ImageFilter.SHARPEN)
        return image

    def parse_image(self, image_path, preprocess):
        pytesseract.pytesseract.tesseract_cmd = self.settings['tesseract_path']
        image = Image.open(image_path)
        if preprocess:
            image = self.enhance_image(image)
        text = pytesseract.image_to_string(image)
        names = self.clean_text(text)
        return names

    def clean_text(self, text):
        printable = set(chr(i) for i in range(32, 127))
        cleaned_text = "".join(filter(lambda x: x in printable, text))
        names = cleaned_text.split("\n")
        return [name.strip() for name in names if name.strip()]

    def write_names_to_file(self, names, filename):
        with open(os.path.join(self.settings['save_path'], filename), 'w') as file:
            for name in names:
                file.write(name + "\n")


class SettingsDialog:
    def __init__(self, parent, settings):
        self.top = tk.Toplevel(parent)
        self.top.title("Settings")
        self.settings = settings
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self.top, text="Tesseract Path:").pack()
        self.tesseract_path_entry = tk.Entry(self.top, width=50)
        self.tesseract_path_entry.pack()
        self.tesseract_path_entry.insert(0, self.settings['tesseract_path'])

        tk.Label(self.top, text="Save Path:").pack()
        self.save_path_entry = tk.Entry(self.top, width=50)
        self.save_path_entry.pack()
        self.save_path_entry.insert(0, self.settings['save_path'])

        tk.Button(self.top, text="Save", command=self.save_settings).pack()

    def save_settings(self):
        self.settings['tesseract_path'] = self.tesseract_path_entry.get()
        self.settings['save_path'] = self.save_path_entry.get()
        with open("settings.json", "w") as file:
            json.dump(self.settings, file)
        self.top.destroy()


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageParserApp(root)
    root.protocol("WM_DELETE_WINDOW", app.save_settings)
    root.mainloop()
