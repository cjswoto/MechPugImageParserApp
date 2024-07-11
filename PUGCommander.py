import tkinter as tk
from tkinter import scrolledtext, Scale, simpledialog, messagebox, Menu, filedialog
from PIL import Image, ImageTk, ImageEnhance, ImageFilter
import win32api
import win32con
import win32gui
import time
import ctypes
import os
import json
import webbrowser
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import logging
import pytesseract
import re
import keyring
import numpy as np

# Set up logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VK_CODE = {'insert': 0x2D, 'ctrl': 0x11, 'alt': 0x12}

HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001

# Define the regions for OCR (adjust these values based on your screen resolution)
TEAM_REGIONS = {
    "Your Team": (50, 150, 400, 450),
    "Your Enemy": (650, 150, 1000, 450)
}

class LoginDialog(simpledialog.Dialog):
    def body(self, master):
        tk.Label(master, text="Email:").grid(row=0)
        tk.Label(master, text="Password:").grid(row=1)

        self.email_entry = tk.Entry(master)
        self.password_entry = tk.Entry(master, show="*")
        self.remember_var = tk.BooleanVar()
        self.remember_checkbox = tk.Checkbutton(master, text="Remember me", variable=self.remember_var)

        self.email_entry.grid(row=0, column=1)
        self.password_entry.grid(row=1, column=1)
        self.remember_checkbox.grid(row=2, columnspan=2)
        return self.email_entry

    def apply(self):
        self.result = (self.email_entry.get(), self.password_entry.get(), self.remember_var.get())

class FriendEditor(simpledialog.Dialog):
    def __init__(self, parent, title, friend_name="", notes=""):
        self.friend_name = friend_name
        self.notes = notes
        super().__init__(parent, title)

    def body(self, master):
        tk.Label(master, text="Name:").grid(row=0)
        tk.Label(master, text="Notes:").grid(row=1)

        self.name_entry = tk.Entry(master)
        self.name_entry.grid(row=0, column=1)
        self.name_entry.insert(0, self.friend_name)

        self.notes_entry = tk.Text(master, height=5, width=30)
        self.notes_entry.grid(row=1, column=1)
        self.notes_entry.insert(tk.END, self.notes)

        return self.name_entry  # initial focus

    def apply(self):
        self.result = (self.name_entry.get(), self.notes_entry.get("1.0", tk.END).strip())

class SettingsDialog(simpledialog.Dialog):
    def __init__(self, parent, title, username="", tesseract_path=""):
        self.username = username
        self.tesseract_path = tesseract_path
        super().__init__(parent, title)

    def body(self, master):
        tk.Label(master, text="In-game Name:").grid(row=0)
        self.name_entry = tk.Entry(master)
        self.name_entry.grid(row=0, column=1)
        self.name_entry.insert(0, self.username)

        tk.Label(master, text="Tesseract-OCR Path:").grid(row=1)
        self.tesseract_entry = tk.Entry(master)
        self.tesseract_entry.grid(row=1, column=1)
        self.tesseract_entry.insert(0, self.tesseract_path)

        self.browse_button = tk.Button(master, text="Browse", command=self.browse_tesseract)
        self.browse_button.grid(row=1, column=2)

        return self.name_entry

    def browse_tesseract(self):
        path = filedialog.askdirectory()
        if path:
            self.tesseract_entry.delete(0, tk.END)
            self.tesseract_entry.insert(0, path)

    def apply(self):
        self.result = (self.name_entry.get(), self.tesseract_entry.get())

class OverlayWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.geometry("400x500+10+10")
        self.root.configure(bg='#1e1e1e')

        self.frame = tk.Frame(self.root, bg='#1e1e1e')
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Header frame
        self.header_frame = tk.Frame(self.frame, bg='#1e1e1e')
        self.header_frame.pack(fill=tk.X, pady=(5, 0))

        # Load and display logo
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "KalSinn_Patchyt.png")
        if os.path.exists(logo_path):
            self.logo = Image.open(logo_path)
            self.logo = self.logo.resize((50, 50), Image.LANCZOS)
            self.logo_tk = ImageTk.PhotoImage(self.logo)
            self.logo_label = tk.Label(self.header_frame, image=self.logo_tk, bg='#1e1e1e')
            self.logo_label.pack(side=tk.LEFT, padx=(5, 10))

            self.logo_label.bind("<ButtonPress-1>", self.start_move)
            self.logo_label.bind("<ButtonRelease-1>", self.stop_move)
            self.logo_label.bind("<B1-Motion>", self.do_move)
            self.logo_label.bind("<Double-Button-1>", self.close_window)
        else:
            print(f"Logo file not found at {logo_path}")

        # Title with link
        self.title_label = tk.Label(self.header_frame, text="PUG Friends by Kal Sinn",
                                    bg='#1e1e1e', fg='#a0a0a0', cursor="hand2")
        self.title_label.pack(side=tk.LEFT, pady=5)
        self.title_label.bind("<Button-1>", self.open_website)

        # Transparency slider
        self.transparency_slider = Scale(self.frame, from_=39, to=255, orient=tk.HORIZONTAL,
                                         command=self.update_transparency,
                                         bg='#1e1e1e', fg='#a0a0a0', troughcolor='#2b2b2b',
                                         highlightthickness=0, length=300)
        self.transparency_slider.set(128)
        self.transparency_slider.pack(pady=(10, 5))

        # Button frame
        self.button_frame = tk.Frame(self.frame, bg='#1e1e1e')
        self.button_frame.pack(fill=tk.X, pady=(0, 10))

        # Add friend button
        self.add_friend_button = tk.Button(self.button_frame, text="Add Friend", command=self.add_friend,
                                           bg='#3c3f41', fg='#a0a0a0', highlightthickness=0)
        self.add_friend_button.pack(side=tk.LEFT, padx=5)

        # Settings button
        self.settings_button = tk.Button(self.button_frame, text="Settings", command=self.open_settings,
                                         bg='#3c3f41', fg='#a0a0a0', highlightthickness=0)
        self.settings_button.pack(side=tk.LEFT, padx=5)

        # Import Image button
        self.import_button = tk.Button(self.button_frame, text="Import Image", command=self.import_image,
                                       bg='#3c3f41', fg='#a0a0a0', highlightthickness=0)
        self.import_button.pack(side=tk.LEFT, padx=5)

        # Clear Teams button
        self.clear_teams_button = tk.Button(self.button_frame, text="Clear Teams", command=self.clear_teams,
                                            bg='#3c3f41', fg='#a0a0a0', highlightthickness=0)
        self.clear_teams_button.pack(side=tk.LEFT, padx=5)

        # Refresh Stats button
        self.refresh_stats_button = tk.Button(self.button_frame, text="Refresh Stats", command=self.refresh_stats,
                                              bg='#3c3f41', fg='#a0a0a0', highlightthickness=0)
        self.refresh_stats_button.pack(side=tk.LEFT, padx=5)

        # Search bar
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.update_friend_list)
        self.search_entry = tk.Entry(self.frame, textvariable=self.search_var, bg='#3c3f41', fg='#a0a0a0')
        self.search_entry.pack(fill=tk.X, padx=10, pady=(0, 5))

        self.scroll_text = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD, bg='#2b2b2b', fg='#a0a0a0')
        self.scroll_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.scroll_text.bind("<Double-Button-1>", self.edit_friend)
        self.scroll_text.bind("<Button-3>", self.show_context_menu)

        self.match_players = {"Your Team": [], "Your Enemy": []}
        self.username = ""
        self.tesseract_path = ""
        self.load_settings()
        self.load_friends()
        self.populate_friend_list()

        self.window_visible = False
        self.root.withdraw()

        self.root.after_idle(self.set_overlay_transparency)
        self.root.after(100, self.check_hotkey)

        self.session = None

        # Check for Tesseract-OCR installation
        self.check_tesseract_installation()

        # Make the window resizable
        self.root.resizable(True, True)

    def check_tesseract_installation(self):
        try:
            pytesseract.get_tesseract_version()
        except pytesseract.pytesseract.TesseractNotFoundError:
            if self.tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = os.path.join(self.tesseract_path, 'tesseract.exe')
            else:
                self.prompt_tesseract_directory()

    def prompt_tesseract_directory(self):
        tesseract_dir = filedialog.askdirectory(title="Select Tesseract-OCR Installation Directory")
        if tesseract_dir:
            tesseract_executable_path = os.path.join(tesseract_dir, 'tesseract.exe')
            if os.path.exists(tesseract_executable_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_executable_path
                self.tesseract_path = tesseract_dir
                self.save_settings()
            else:
                messagebox.showerror("Error", "Tesseract executable not found in the selected directory.")
                self.prompt_tesseract_directory()

    def login(self):
        dialog = LoginDialog(self.root, "Login to MechWarrior Online")
        if dialog.result:
            email, password, remember = dialog.result
            self.session = requests.Session()
            login_url = "https://mwomercs.com/do/login"
            login_data = {
                "email": email,
                "password": password,
                "return": "/profile/leaderboards/quickplay?type=0"
            }
            response = self.session.post(login_url, data=login_data)
            if "Sign in" not in response.text:  # Simple check to see if login was successful
                if remember:
                    keyring.set_password("MWOApp", "email", email)
                    keyring.set_password("MWOApp", "password", password)
                return True
        return False

    def auto_login(self):
        email = keyring.get_password("MWOApp", "email")
        password = keyring.get_password("MWOApp", "password")
        if email and password:
            self.session = requests.Session()
            login_url = "https://mwomercs.com/do/login"
            login_data = {
                "email": email,
                "password": password,
                "return": "/profile/leaderboards/quickplay?type=0"
            }
            response = self.session.post(login_url, data=login_data)
            return "Sign in" not in response.text
        return False

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                self.username = settings.get('username', '')
                self.tesseract_path = settings.get('tesseract_path', '')
        except FileNotFoundError:
            pass

    def save_settings(self):
        with open('settings.json', 'w') as f:
            json.dump({'username': self.username, 'tesseract_path': self.tesseract_path}, f)

    def open_settings(self):
        dialog = SettingsDialog(self.root, "User Settings", self.username, self.tesseract_path)
        if dialog.result:
            self.username, self.tesseract_path = dialog.result
            self.save_settings()
            self.check_tesseract_installation()
            self.populate_friend_list()

    def load_friends(self):
        try:
            with open('friends.json', 'r') as f:
                self.friends = json.load(f)
        except FileNotFoundError:
            self.friends = {}
            self.save_friends()

    def save_friends(self):
        with open('friends.json', 'w') as f:
            json.dump(self.friends, f)

    def add_friend(self):
        dialog = FriendEditor(self.root, "Add Friend")
        if dialog.result:
            name, notes = dialog.result
            if name and name not in self.friends:
                self.friends[name] = notes
                self.save_friends()
                self.populate_friend_list()

    def edit_friend(self, event):
        index = self.scroll_text.index(f"@{event.x},{event.y}")
        line_start = self.scroll_text.index(f"{index} linestart")
        line_end = self.scroll_text.index(f"{index} lineend")
        line = self.scroll_text.get(line_start, line_end)
        name = line.split("\n")[0].strip()
        if name in self.friends:
            dialog = FriendEditor(self.root, "Edit Friend", name, self.friends[name])
            if dialog.result:
                new_name, new_notes = dialog.result
                if new_name != name:
                    del self.friends[name]
                self.friends[new_name] = new_notes
                self.save_friends()
                self.populate_friend_list()

    def delete_friend(self, name):
        if name in self.friends:
            if messagebox.askyesno("Delete Friend", f"Are you sure you want to delete {name}?"):
                del self.friends[name]
                self.save_friends()
                self.populate_friend_list()

    def show_context_menu(self, event):
        index = self.scroll_text.index(f"@{event.x},{event.y}")
        line_start = self.scroll_text.index(f"{index} linestart")
        line_end = self.scroll_text.index(f"{index} lineend")
        line = self.scroll_text.get(line_start, line_end)
        name = line.split("\n")[0].strip()

        if name in self.friends:
            menu = Menu(self.root, tearoff=0)
            menu.add_command(label="Delete", command=lambda: self.delete_friend(name))
            menu.tk_popup(event.x_root, event.y_root)

    def update_friend_list(self, *args):
        self.populate_friend_list()

    def populate_friend_list(self):
        search_query = self.search_var.get().lower()
        self.scroll_text.config(state=tk.NORMAL)
        self.scroll_text.delete('1.0', tk.END)

        # Display user's stats if available
        if self.username and self.username in self.friends:
            user_stats = self.friends[self.username]
            self.scroll_text.insert(tk.END, f"Your Stats:\n{self.username}\n{user_stats}\n\n")

        # Display match players
        for team, players in self.match_players.items():
            self.scroll_text.insert(tk.END, f"{team}:\n")
            for player in sorted(players, key=lambda x: self.get_rank(self.friends.get(x, ""))):
                if search_query in player.lower() or search_query in self.friends.get(player, "").lower():
                    stats = self.friends.get(player, "")
                    self.scroll_text.insert(tk.END, f"{player}\n{stats}\n\n")
            self.scroll_text.insert(tk.END, "\n")

        # Display other friends
        self.scroll_text.insert(tk.END, "Other Friends:\n")
        for friend, stats in sorted(self.friends.items(), key=lambda x: self.get_rank(x[1])):
            if friend not in self.match_players["Your Team"] and friend not in self.match_players["Your Enemy"]:
                if search_query in friend.lower() or search_query in stats.lower():
                    self.scroll_text.insert(tk.END, f"{friend}\n{stats}\n\n")

        self.scroll_text.config(state=tk.DISABLED)

    def get_rank(self, stats):
        match = re.search(r'Rank: (\d+)', stats)
        return int(match.group(1)) if match else float('inf')

    def toggle_window(self):
        if self.window_visible:
            self.root.withdraw()
        else:
            self.root.deiconify()
            self.force_top()
        self.window_visible = not self.window_visible

    def refresh_stats(self):
        if not self.session:
            if not self.login():
                messagebox.showerror("Login Failed", "Unable to log in to MechWarrior Online")
                return

        self.show_loading_message("Updating friend stats...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_friend = {executor.submit(self.fetch_friend_stats, friend): friend for friend in self.friends}
            for future in concurrent.futures.as_completed(future_to_friend):
                friend = future_to_friend[future]
                try:
                    stats = future.result()
                    if stats:
                        self.friends[friend] = stats
                    else:
                        self.friends[friend] = "NOT FOUND"
                except Exception as exc:
                    print(f'{friend} generated an exception: {exc}')
                    self.friends[friend] = "ERROR"

        self.save_friends()
        self.populate_friend_list()
        self.hide_loading_message()

    def show_loading_message(self, message):
        self.loading_window = tk.Toplevel(self.root)
        self.loading_window.attributes("-topmost", True)
        self.loading_window.overrideredirect(True)
        self.loading_window.geometry(f"+{self.root.winfo_x() + 50}+{self.root.winfo_y() + 50}")
        tk.Label(self.loading_window, text=message, padx=20, pady=10).pack()

    def hide_loading_message(self):
        if hasattr(self, 'loading_window'):
            self.loading_window.destroy()

    def fetch_friend_stats(self, friend_name):
        if not self.session:
            return "ERROR: Not logged in"

        url = f"https://mwomercs.com/profile/leaderboards/quickplay?type=0&user={friend_name}"
        logging.info(f"Fetching stats for {friend_name} from URL: {url}")
        try:
            response = self.session.get(url)
            logging.info(f"Response from URL: {response.text[:200]}...")
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', class_='table table-striped')
            if table:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Skip header row
                    columns = row.find_all('td')
                    if columns and columns[1].text.strip() == friend_name:
                        rank = columns[0].text.strip()
                        total_wins = columns[2].text.strip()
                        total_losses = columns[3].text.strip()
                        wl_ratio = columns[4].text.strip()
                        total_kills = columns[5].text.strip()
                        total_deaths = columns[6].text.strip()
                        kd_ratio = columns[7].text.strip()
                        games_played = columns[8].text.strip()
                        avg_match_score = columns[9].text.strip()
                        return (f"Rank: {rank}, W: {total_wins}, L: {total_losses}, W/L: {wl_ratio}, "
                                f"K: {total_kills}, D: {total_deaths}, K/D: {kd_ratio}, "
                                f"Games: {games_played}, Avg Score: {avg_match_score}")
            return "NOT FOUND"
        except requests.RequestException as e:
            logging.error(f"Error fetching stats for {friend_name}: {e}")
            return "ERROR"

    def set_overlay_transparency(self):
        self.update_transparency()

    def update_transparency(self, *args):
        alpha = self.transparency_slider.get()
        self.root.attributes('-alpha', alpha / 255)

    def check_hotkey(self):
        if (win32api.GetAsyncKeyState(VK_CODE['ctrl']) & 0x8000 and
                win32api.GetAsyncKeyState(VK_CODE['alt']) & 0x8000 and
                win32api.GetAsyncKeyState(VK_CODE['insert']) & 0x8000):
            self.toggle_window()
            time.sleep(0.3)
        self.root.after(100, self.check_hotkey)

    def force_top(self):
        hwnd = self.root.winfo_id()
        win32gui.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        ctypes.windll.user32.SetForegroundWindow(hwnd)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def close_window(self, event):
        self.root.withdraw()
        self.window_visible = False

    def open_website(self, event):
        webbrowser.open_new("http://PUGFKalSinn.free.com")

    def import_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if file_path:
            self.parse_image(file_path)

    def parse_image(self, image_path):
        image = Image.open(image_path)
        self.show_loading_message("Processing image...")

        for team, region in TEAM_REGIONS.items():
            cropped_image = image.crop(region)
            enhanced_image = self.enhance_image(cropped_image)
            text = pytesseract.image_to_string(enhanced_image, config='--psm 6')  # Set PSM to 6
            players = [line.strip() for line in text.split('\n') if line.strip()]  # Keep each line as a name
            self.match_players[team] = players

        self.update_match_players()
        self.hide_loading_message()

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
        enhanced_image = enhanced_image.filter(ImageFilter.MedianFilter(size=3))

        return enhanced_image

    def update_match_players(self):
        for team, players in self.match_players.items():
            for player in players:
                if player not in self.friends:
                    self.friends[player] = ""
        self.populate_friend_list()

    def clear_teams(self):
        self.match_players = {"Your Team": [], "Your Enemy": []}
        self.populate_friend_list()


if __name__ == "__main__":
    app = OverlayWindow()
    if not app.auto_login():
        app.login()
    try:
        app.root.mainloop()
    finally:
        if app.session:
            app.session.close()
