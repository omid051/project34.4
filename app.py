import tkinter as tk
from tkinter import ttk, font, simpledialog, messagebox
import requests
import threading
import json
import base64
import os
import random
import subprocess

# --- 🌐 تنظیمات اتصال به سرور ---
API_URL = "https://example.com/34.4/api.php"
SECRET_KEY = "secret"
# ---------------------------------
SETTINGS_FILE = "settings.json"

# Fix for DPI scaling issue on Windows
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except ImportError:
    pass

class FadingTooltip:
    """ایجاد یک پیام محو شونده برای نمایش اطلاعات"""
    def __init__(self, parent, text):
        self.parent = parent
        self.text = text

        self.win = tk.Toplevel(self.parent)
        self.win.overrideredirect(True)

        label = tk.Label(self.win, text=self.text, justify=tk.LEFT,
                         background="#28a745", foreground="white", relief=tk.SOLID, borderwidth=1,
                         font=("Segoe UI", 10, "bold"), padx=10, pady=5)
        label.pack(ipadx=1)

        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        self.win.update_idletasks()
        win_width = self.win.winfo_width()
        win_height = self.win.winfo_height()

        x = parent_x + parent_width - win_width - 20
        y = parent_y + parent_height - win_height - 20
        self.win.geometry(f'+{x}+{y}')

        self.win.after(2000, self.win.destroy)

class LoginWindow:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.parent.title("Login")
        self.parent.geometry("340x240")
        self.parent.resizable(False, False)

        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.remember_me = tk.BooleanVar()

        self.load_credentials()

        main_frame = tk.Frame(self.parent, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        tk.Label(main_frame, text="Username:").grid(row=0, column=0, sticky="w", pady=5)
        tk.Entry(main_frame, textvariable=self.username).grid(row=0, column=1, sticky="ew")

        tk.Label(main_frame, text="Password:").grid(row=1, column=0, sticky="w", pady=5)
        tk.Entry(main_frame, textvariable=self.password, show="*").grid(row=1, column=1, sticky="ew")

        tk.Checkbutton(main_frame, text="Remember Me", variable=self.remember_me).grid(row=2, columnspan=2, pady=5)

        tk.Button(main_frame, text="Login", command=self.login).grid(row=3, columnspan=2, pady=10)

    def load_credentials(self):
        try:
            with open("credentials.json", "r") as f:
                creds_encoded = json.load(f)
                if creds_encoded:
                    username_encoded = creds_encoded.get("username", "")
                    password_encoded = creds_encoded.get("password", "")
                    self.username.set(base64.b64decode(username_encoded).decode())
                    self.password.set(base64.b64decode(password_encoded).decode())
                    self.remember_me.set(creds_encoded.get("remember_me", False))
        except (FileNotFoundError, ValueError, TypeError):
            pass

    def save_credentials(self):
        if self.remember_me.get():
            username_encoded = base64.b64encode(self.username.get().encode()).decode()
            password_encoded = base64.b64encode(self.password.get().encode()).decode()
            creds = {
                "username": username_encoded,
                "password": password_encoded,
                "remember_me": self.remember_me.get()
            }
            with open("credentials.json", "w") as f:
                json.dump(creds, f)
        else:
            try:
                with open("credentials.json", "w") as f:
                    json.dump({}, f)
            except FileNotFoundError:
                pass

    def login(self):
        username = self.username.get()
        password = self.password.get()

        try:
            payload = {'secret_key': SECRET_KEY, 'action': 'login', 'username': username, 'password': password}
            response = requests.post(API_URL, data=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result.get("status") == "success":
                self.save_credentials()
                self.app.username = username
                self.parent.destroy()
                self.app.run_main_app()
            else:
                messagebox.showerror("Login Failed", result.get("message", "Unknown error"))
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Network Error", f"Could not connect to the server: {e}")

class App:
    def __init__(self, root):
        self.root = root
        self.username = None
        self.run_main_app_flag = False

    def save_settings(self):
        """Save current UI settings to a file."""
        settings = {
            'refresh_min': self.refresh_min_var.get(),
            'refresh_max': self.refresh_max_var.get(),
            'desired_month': self.desired_month.get(),
            'x_min': self.x_min_var.get(),
            'x_max': self.x_max_var.get(),
            'y_min': self.y_min_var.get(),
            'y_max': self.y_max_var.get(),
            'captcha_delay': self.captcha_delay_var.get(),
            'captcha_enabled': self.captcha_enabled_var.get(),
            'disable_error_sound': self.disable_error_sound_var.get(),
            'disable_slot_sound': self.disable_slot_sound_var.get(),
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)

    def load_settings(self):
        """Load UI settings from a file."""
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
                self.refresh_min_var.set(settings.get('refresh_min', '15'))
                self.refresh_max_var.set(settings.get('refresh_max', '20'))
                self.desired_month.set(settings.get('desired_month', 'current_month'))
                self.x_min_var.set(settings.get('x_min', '310'))
                self.x_max_var.set(settings.get('x_max', '380'))
                self.y_min_var.set(settings.get('y_min', '370'))
                self.y_max_var.set(settings.get('y_max', '380'))
                self.captcha_delay_var.set(settings.get('captcha_delay', '15'))
                self.captcha_enabled_var.set(settings.get('captcha_enabled', True))
                self.disable_error_sound_var.set(settings.get('disable_error_sound', False))
                self.disable_slot_sound_var.set(settings.get('disable_slot_sound', False))
        except (FileNotFoundError, json.JSONDecodeError):
            # If file doesn't exist or is empty/corrupt, use default values
            self.refresh_min_var.set("15")
            self.refresh_max_var.set("20")
            self.desired_month.set("current_month")
            self.x_min_var.set("310")
            self.x_max_var.set("380")
            self.y_min_var.set("370")
            self.y_max_var.set("380")
            self.captcha_delay_var.set("15")
            self.captcha_enabled_var.set(True)
            self.disable_error_sound_var.set(False)
            self.disable_slot_sound_var.set(False)

    def on_closing(self):
        """Called when the main window is closing."""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.save_settings()
            for item_id, data in self.running_threads.items():
                data['stop_event'].set()
                try:
                    payload = {'secret_key': SECRET_KEY, 'action': 'update_status', 'id': item_id, 'status': 'pending', 'username': self.username}
                    requests.post(API_URL, data=payload, timeout=5)
                except requests.exceptions.RequestException as e:
                    print(f"Could not revert status for {item_id} on close: {e}")
            self.root.destroy()

    def run_main_app(self):
        if self.run_main_app_flag:
            return
        self.run_main_app_flag = True

        self.root.deiconify()

        self.root.title("TLS v34.4")
        self.root.state('zoomed') # Full screen
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(family="Segoe UI", size=10)
        self.root.option_add("*Font", self.default_font)

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Treeview", rowheight=28, fieldbackground="#f0f0f0")
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"), background="#343a40", foreground="white")
        style.map("Treeview.Heading", background=[('active', '#495057')])

        self.applicants = []
        self.running_threads = {}

        # --- متغیرهای تنظیمات ---
        self.refresh_min_var = tk.StringVar()
        self.refresh_max_var = tk.StringVar()
        self.desired_month = tk.StringVar()
        self.x_min_var = tk.StringVar()
        self.x_max_var = tk.StringVar()
        self.y_min_var = tk.StringVar()
        self.y_max_var = tk.StringVar()
        self.captcha_delay_var = tk.StringVar()
        self.captcha_enabled_var = tk.BooleanVar()
        self.disable_error_sound_var = tk.BooleanVar()
        self.disable_slot_sound_var = tk.BooleanVar()

        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)

        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))

        columns = ("row", "id", "slot_selection", "email", "visa_type", "description", "status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("row", text="Row")
        self.tree.heading("id", text="ID")
        self.tree.heading("slot_selection", text="Slot Selection")
        self.tree.heading("email", text="Email Address")
        self.tree.heading("visa_type", text="Visa Type")
        self.tree.heading("description", text="Description")
        self.tree.heading("status", text="Status")

        self.tree.column("row", width=40, anchor="center")
        self.tree.column("id", width=50, anchor="center")
        self.tree.column("slot_selection", width=120, anchor="center")
        self.tree.column("email", width=250)
        self.tree.column("visa_type", width=100, anchor="center")
        self.tree.column("description", width=200)
        self.tree.column("status", width=250, anchor="center")

        self.tree.tag_configure('booked', background='#d4edda', foreground='#155724')
        self.tree.tag_configure('pending', background='white', foreground='black')
        self.tree.tag_configure('in_progress', background='#fff3cd', foreground='#856404')
        self.tree.tag_configure('failed', background='#f8d7da', foreground='#721c24')
        self.tree.tag_configure('oddrow', background='#f2f2f2')

        self.tree.bind("<Button-3>", self.show_context_menu)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        action_frame = ttk.LabelFrame(main_frame, text="Actions", padding=(10, 10))
        action_frame.pack(fill="x")

        button_frame = ttk.Frame(action_frame)
        button_frame.pack(fill="x", pady=5)

        self.refresh_btn = ttk.Button(button_frame, text="🔄 Refresh List", command=self.load_applicants)
        self.refresh_btn.pack(side="left", padx=5, expand=True, fill="x")

        self.mark_btn = ttk.Button(button_frame, text="✅ Booked", command=self.toggle_status_to_booked)
        self.mark_btn.pack(side="left", padx=5, expand=True, fill="x")

        self.auto_start_btn = ttk.Button(button_frame, text="▶️ Start", command=self.start_auto_booking, style="Accent.TButton")
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), background="#007bff", foreground="white")
        style.map("Accent.TButton", background=[('active', '#0056b3')])
        self.auto_start_btn.pack(side="left", padx=5, expand=True, fill="x")

        self.stop_btn = ttk.Button(button_frame, text="⏹️ Stop", command=self.stop_selected_booking, state="disabled")
        self.stop_btn.pack(side="left", padx=5, expand=True, fill="x")

        self.settings_btn = ttk.Button(button_frame, text="⚙️ Settings", command=self.open_settings)
        self.settings_btn.pack(side="left", padx=5, expand=True, fill="x")

        if self.username == "omid":
            self.add_applicant_btn = ttk.Button(button_frame, text="➕ Add", command=self.open_applicant_form)
            self.add_applicant_btn.pack(side="left", padx=5, expand=True, fill="x")

            self.edit_applicant_btn = ttk.Button(button_frame, text="✏️ Edit", command=lambda: self.open_applicant_form(edit_mode=True))
            self.edit_applicant_btn.pack(side="left", padx=5, expand=True, fill="x")

        self.load_settings()
        self.load_applicants()

    def open_settings(self):
        SettingsWindow(self.root, self)

    def show_context_menu(self, event):
        selection = self.tree.identify_row(event.y)
        if selection:
            self.tree.selection_set(selection)
            item_id = self.tree.item(selection)['values'][1]
            applicant_data = next((app for app in self.applicants if str(app['id']) == str(item_id)), None)
            if not applicant_data:
                return

            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label=f"Copy Email: {applicant_data['email']}", command=lambda: self.copy_to_clipboard(applicant_data['email']))
            context_menu.add_command(label=f"Copy Password", command=lambda: self.copy_to_clipboard(applicant_data['password']))
            context_menu.post(event.x_root, event.y_root)

    def copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        FadingTooltip(self.root, f"'{text}' copied to clipboard.")

    def load_applicants(self):
        try:
            response = requests.get(f"{API_URL}?action=get_applicants", timeout=10)
            response.raise_for_status()
            self.applicants = sorted(response.json(), key=lambda x: int(x['id']))
            self.populate_treeview()
        except requests.exceptions.RequestException as e:
            FadingTooltip(self.root, f"Network Error: {e}")

    def populate_treeview(self):
        selected_ids = self.tree.selection()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, applicant in enumerate(self.applicants):
            status_text = applicant.get("status", "pending").capitalize()
            
            # Base tag for coloring based on status
            tag = "pending"
            if "In Progress" in status_text:
                tag = "in_progress"
            elif "Booked by" in status_text:
                tag = "booked"
            elif "Failed" in status_text:
                tag = "failed"
            
            # Combine with alternating row color tag
            tags = (tag,)
            if i % 2 != 0:
                tags += ('oddrow',)

            self.tree.insert("", tk.END, iid=applicant['id'], values=(
                i + 1,
                applicant['id'],
                applicant.get('slot_selection', 'random').capitalize(),
                applicant['email'],
                applicant.get('visa_type', ''),
                applicant.get('description', ''),
                status_text
            ), tags=tags)

        if selected_ids:
            self.tree.selection_set(selected_ids)

    def toggle_status_to_booked(self):
        selected_items = self.tree.selection()
        if not selected_items:
            FadingTooltip(self.root, "Please select an applicant.")
            return

        for item_id in selected_items:
            if str(item_id) in self.running_threads:
                FadingTooltip(self.root, f"Cannot change status for {item_id} while running.")
                continue

            applicant = next((app for app in self.applicants if str(app['id']) == item_id), None)
            if applicant and "Booked by" in applicant.get('status'):
                new_status = 'pending'
            else:
                new_status = f'Booked by {self.username}'

            try:
                payload = {'secret_key': SECRET_KEY, 'action': 'update_status', 'id': item_id, 'status': new_status, 'username': self.username}
                requests.post(API_URL, data=payload, timeout=10).raise_for_status()
            except requests.exceptions.RequestException as e:
                FadingTooltip(self.root, f"Error updating status for {item_id}.")

        self.load_applicants()

    def start_booking_threads(self, mode):
        selected_items = self.tree.selection()
        if not selected_items:
            FadingTooltip(self.root, "Please select at least one applicant.")
            return

        try:
            refresh_min = int(self.refresh_min_var.get())
            refresh_max = int(self.refresh_max_var.get())
            if refresh_min < 5 or refresh_max < 5 or refresh_min > refresh_max:
                FadingTooltip(self.root, "Refresh interval must be at least 5s and min <= max.")
                return

            x_min = int(self.x_min_var.get())
            x_max = int(self.x_max_var.get())
            y_min = int(self.y_min_var.get())
            y_max = int(self.y_max_var.get())
            captcha_delay = int(self.captcha_delay_var.get())
            captcha_enabled = self.captcha_enabled_var.get()
            disable_error_sound = self.disable_error_sound_var.get()
            disable_slot_sound = self.disable_slot_sound_var.get()

        except ValueError:
            FadingTooltip(self.root, "Invalid number in settings.")
            return

        self.stop_btn.config(state="normal")

        for item_id in selected_items:
            applicant = next((app for app in self.applicants if str(app['id']) == str(item_id)), None)
            if applicant and "Booked by" not in applicant.get('status'):
                try:
                    payload = {'secret_key': SECRET_KEY, 'action': 'update_status', 'id': item_id, 'status': 'in_progress', 'username': self.username}
                    requests.post(API_URL, data=payload, timeout=10).raise_for_status()
                except requests.exceptions.RequestException as e:
                    FadingTooltip(self.root, f"Error updating status for {item_id}.")
                    continue

                stop_event = threading.Event()
                month_choice = self.desired_month.get()
                slot_selection_strategy = applicant.get('slot_selection', 'random')

                thread = threading.Thread(
                    target=self.run_and_update,
                    args=(applicant, month_choice, stop_event, mode, refresh_min, refresh_max, x_min, x_max, y_min, y_max, captcha_delay, captcha_enabled, slot_selection_strategy, disable_error_sound, disable_slot_sound)
                )
                thread.daemon = True

                self.running_threads[str(item_id)] = {'thread': thread, 'stop_event': stop_event}

                thread.start()

        if not self.running_threads:
             self.stop_btn.config(state="disabled")
        self.load_applicants()

    def start_auto_booking(self):
        from booking_bot import run_booking_process
        self.run_booking_process_ref = run_booking_process
        self.start_booking_threads(mode='auto')

    def stop_selected_booking(self):
        selected_items = self.tree.selection()
        if not selected_items:
            FadingTooltip(self.root, "Please select an applicant to stop.")
            return

        for item_id in selected_items:
            if str(item_id) in self.running_threads:
                FadingTooltip(self.root, f"Stopping process for ID {item_id}...")
                self.running_threads[str(item_id)]['stop_event'].set()
                try:
                    payload = {'secret_key': SECRET_KEY, 'action': 'update_status', 'id': item_id, 'status': 'pending', 'username': self.username}
                    requests.post(API_URL, data=payload, timeout=10).raise_for_status()
                except requests.exceptions.RequestException as e:
                    FadingTooltip(self.root, f"Error updating status for {item_id}.")
            else:
                FadingTooltip(self.root, f"No active process for ID {item_id}.")
        self.load_applicants()

    def run_and_update(self, applicant, month_choice, stop_event, mode, refresh_min, refresh_max, x_min, x_max, y_min, y_max, captcha_delay, captcha_enabled, slot_selection_strategy, disable_error_sound, disable_slot_sound):
        refresh_delay = random.randint(refresh_min, refresh_max)
        success = self.run_booking_process_ref(
            email=applicant['email'],
            password=applicant['password'],
            desired_month=month_choice,
            stop_event=stop_event,
            mode=mode,
            refresh_delay=refresh_delay,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
            captcha_delay=captcha_delay,
            captcha_enabled=captcha_enabled,
            slot_selection_strategy=slot_selection_strategy,
            disable_error_sound=disable_error_sound,
            disable_slot_sound=disable_slot_sound
        )
        self.root.after(100, self.update_ui_after_run, applicant, success, stop_event.is_set(), mode)

    def update_ui_after_run(self, applicant, success, was_stopped, mode):
        applicant_id = str(applicant['id'])

        if applicant_id in self.running_threads:
            del self.running_threads[applicant_id]

        if success and mode == 'auto':
            new_status = f'Booked by {self.username}'
            payload = {'secret_key': SECRET_KEY, 'action': 'update_status', 'id': applicant_id, 'status': new_status, 'username': self.username}
            try:
                requests.post(API_URL, data=payload, timeout=10).raise_for_status()
                FadingTooltip(self.root, f"Appointment booked for {applicant['email']}!")
            except requests.exceptions.RequestException as e:
                print(f"Could not update status automatically: {e}")
        elif not was_stopped:
            FadingTooltip(self.root, f"Could not book for {applicant['email']}.")
            try:
                payload = {'secret_key': SECRET_KEY, 'action': 'update_status', 'id': applicant_id, 'status': 'pending', 'username': self.username}
                requests.post(API_URL, data=payload, timeout=10).raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"Could not update status automatically: {e}")

        if not self.running_threads:
            self.stop_btn.config(state="disabled")

        self.load_applicants()

    def open_applicant_form(self, edit_mode=False):
        selected_items = self.tree.selection()
        if edit_mode and not selected_items:
            FadingTooltip(self.root, "Please select an applicant to edit.")
            return

        applicant_data = None
        if edit_mode:
            item_id = selected_items[0]
            applicant_data = next((app for app in self.applicants if str(app['id']) == item_id), None)

        ApplicantForm(self.root, self, applicant_data, edit_mode)

class ApplicantForm:
    def __init__(self, parent, app, data=None, edit_mode=False):
        self.parent = parent
        self.app = app
        self.data = data
        self.edit_mode = edit_mode

        self.win = tk.Toplevel(self.parent)
        self.win.title("Add Applicant" if not edit_mode else "Edit Applicant")
        self.win.geometry("450x450")

        self.id_var = tk.StringVar(value=data.get('id', '') if data else '')
        self.email_var = tk.StringVar(value=data.get('email', '') if data else '')
        self.password_var = tk.StringVar(value=data.get('password', '') if data else '')
        self.description_var = tk.StringVar(value=data.get('description', '') if data else '')
        self.phone_number_var = tk.StringVar(value=data.get('phone_number', '') if data else '')
        self.visa_type_var = tk.StringVar(value=data.get('visa_type', 'Work') if data else 'Work')
        self.is_visible_var = tk.BooleanVar(value=data.get('is_visible', True) if data else True)
        self.slot_selection_var = tk.StringVar(value=data.get('slot_selection', 'fastest') if data else 'fastest')

        form_frame = ttk.Frame(self.win, padding="10")
        form_frame.pack(fill="both", expand=True)
        form_frame.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(form_frame, text="ID:").grid(row=row, column=0, sticky="w", pady=3)
        id_entry = ttk.Entry(form_frame, textvariable=self.id_var)
        id_entry.grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        ttk.Label(form_frame, text="Email:").grid(row=row, column=0, sticky="w", pady=3)
        ttk.Entry(form_frame, textvariable=self.email_var).grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        ttk.Label(form_frame, text="Password:").grid(row=row, column=0, sticky="w", pady=3)
        ttk.Entry(form_frame, textvariable=self.password_var).grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        ttk.Label(form_frame, text="Description:").grid(row=row, column=0, sticky="w", pady=3)
        ttk.Entry(form_frame, textvariable=self.description_var).grid(row=row, column=1, sticky="ew", pady=3)
        row += 1
        
        ttk.Label(form_frame, text="Phone Number:").grid(row=row, column=0, sticky="w", pady=3)
        ttk.Entry(form_frame, textvariable=self.phone_number_var).grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        ttk.Label(form_frame, text="Visa Type:").grid(row=row, column=0, sticky="w", pady=3)
        visa_types = ['Ausbildung', 'Work', 'Student', 'Visit', 'Tourism', 'Legal', 'Doctor', 'Other']
        ttk.Combobox(form_frame, textvariable=self.visa_type_var, values=visa_types, state="readonly").grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        ttk.Label(form_frame, text="Slot Selection:").grid(row=row, column=0, sticky="w", pady=3)
        slot_selection_options = { "Fastest possible time": "fastest", "Completely random": "random", "Latest possible time": "latest" }
        self.slot_selection_display_options = {v: k for k, v in slot_selection_options.items()}
        self.slot_selection_combo = ttk.Combobox(form_frame, textvariable=self.slot_selection_var, values=list(slot_selection_options.keys()), state="readonly")
        self.slot_selection_combo.grid(row=row, column=1, sticky="ew", pady=3)
        self.slot_selection_combo.set(self.slot_selection_display_options.get(self.slot_selection_var.get(), "Fastest possible time"))
        row += 1

        ttk.Checkbutton(form_frame, text="Is Visible", variable=self.is_visible_var).grid(row=row, columnspan=2, pady=5)
        row += 1

        ttk.Button(form_frame, text="Save", command=self.save_applicant).grid(row=row, columnspan=2, pady=10)

    def save_applicant(self):
        slot_selection_options = { "Fastest possible time": "fastest", "Completely random": "random", "Latest possible time": "latest" }
        
        applicant_id = self.id_var.get()
        if not applicant_id:
            messagebox.showerror("Error", "ID field cannot be empty.")
            return

        payload = {
            'secret_key': SECRET_KEY,
            'id': applicant_id,
            'email': self.email_var.get(),
            'password': self.password_var.get(),
            'description': self.description_var.get(),
            'phone_number': self.phone_number_var.get(),
            'visa_type': self.visa_type_var.get(),
            'is_visible': 1 if self.is_visible_var.get() else 0,
            'slot_selection': slot_selection_options.get(self.slot_selection_combo.get())
        }

        if self.edit_mode:
            payload['action'] = 'update_applicant'
        else:
            payload['action'] = 'add_applicant'

        try:
            response = requests.post(API_URL, data=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            if result.get("status") == "success":
                FadingTooltip(self.parent, "Applicant saved successfully.")
                self.app.load_applicants()
                self.win.destroy()
            else:
                messagebox.showerror("Error", result.get("message", "Unknown error"))
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Network Error", f"Could not connect to the server: {e}")

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("Settings")
        self.geometry("450x800")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1)

        # --- Refresh Settings ---
        refresh_frame = ttk.LabelFrame(main_frame, text="Refresh Settings", padding=(10, 10))
        refresh_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        refresh_frame.columnconfigure((1, 3), weight=1)

        ttk.Label(refresh_frame, text="Min (sec):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(refresh_frame, textvariable=self.app.refresh_min_var, width=10).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(refresh_frame, text="Max (sec):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        ttk.Entry(refresh_frame, textvariable=self.app.refresh_max_var, width=10).grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        # --- Month Selection ---
        self.month_frame = ttk.LabelFrame(main_frame, text="Month Selection", padding=(10, 10))
        self.month_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.current_month_radio = ttk.Radiobutton(self.month_frame, text="Current Month", variable=self.app.desired_month, value="current_month")
        self.current_month_radio.pack(side="left", padx=10, expand=True)
        self.next_month_radio = ttk.Radiobutton(self.month_frame, text="Next Month", variable=self.app.desired_month, value="next_month")
        self.next_month_radio.pack(side="left", padx=10, expand=True)

        # --- CAPTCHA Coordinates ---
        captcha_frame = ttk.LabelFrame(main_frame, text="CAPTCHA Click Coordinates", padding=(10, 10))
        captcha_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        captcha_frame.columnconfigure((1, 3), weight=1)

        ttk.Label(captcha_frame, text="X-Axis Min:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(captcha_frame, textvariable=self.app.x_min_var, width=10).grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ttk.Label(captcha_frame, text="X-Axis Max:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        ttk.Entry(captcha_frame, textvariable=self.app.x_max_var, width=10).grid(row=0, column=3, padx=5, pady=2, sticky="ew")
        ttk.Label(captcha_frame, text="Y-Axis Min:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        ttk.Entry(captcha_frame, textvariable=self.app.y_min_var, width=10).grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        ttk.Label(captcha_frame, text="Y-Axis Max:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        ttk.Entry(captcha_frame, textvariable=self.app.y_max_var, width=10).grid(row=1, column=3, padx=5, pady=2, sticky="ew")

        # --- CAPTCHA Settings ---
        captcha_settings_frame = ttk.LabelFrame(main_frame, text="CAPTCHA Settings", padding=(10, 10))
        captcha_settings_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        ttk.Checkbutton(captcha_settings_frame, text="Enable CAPTCHA Click", variable=self.app.captcha_enabled_var).pack(anchor="w", padx=5)
        delay_frame = ttk.Frame(captcha_settings_frame)
        delay_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(delay_frame, text="Captcha Click Delay (sec):").pack(side="left")
        ttk.Entry(delay_frame, textvariable=self.app.captcha_delay_var, width=5).pack(side="left", padx=5)

        # --- Troubleshooting ---
        kill_frame = ttk.LabelFrame(main_frame, text="Troubleshooting & Sounds", padding=(10, 10))
        kill_frame.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        ttk.Checkbutton(kill_frame, text="Disable Error Sound", variable=self.app.disable_error_sound_var).pack(anchor="w", padx=5, pady=(0,5))
        ttk.Checkbutton(kill_frame, text="Disable Slot Found Sound", variable=self.app.disable_slot_sound_var).pack(anchor="w", padx=5, pady=(0,5))
        ttk.Button(kill_frame, text="Kill All Chrome & Chromedriver Processes", command=self.kill_chrome_processes).pack(pady=5, padx=5, fill="x")

        # --- Save Button ---
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, sticky="ew", pady=(15, 0))
        button_frame.columnconfigure(0, weight=1)
        ttk.Button(button_frame, text="Save and Close", command=self.save_and_close).grid(row=0, column=0)

    def kill_chrome_processes(self):
        try:
            if os.name == 'nt':
                # For Windows
                subprocess.run('taskkill /F /IM chrome.exe /T', check=True, shell=True, capture_output=True, text=True, encoding='utf-8')
                subprocess.run('taskkill /F /IM chromedriver.exe /T', check=True, shell=True, capture_output=True, text=True, encoding='utf-8')
                FadingTooltip(self, "All Chrome and Chromedriver processes have been terminated.")
            else:
                # For macOS/Linux
                subprocess.run("pkill -f 'Google Chrome'", shell=True)
                subprocess.run("pkill -f 'chromedriver'", shell=True)
                FadingTooltip(self, "Attempted to kill Chrome and Chromedriver processes.")
        except subprocess.CalledProcessError as e:
            error_message = e.stderr or e.stdout
            if "not found" in error_message:
                 FadingTooltip(self, "No Chrome processes were found running.")
            else:
                messagebox.showerror("Error", f"Could not terminate processes.\nDetails: {error_message}", parent=self)
        except FileNotFoundError:
             messagebox.showerror("Error", "Taskkill command not found. This feature is for Windows.", parent=self)

    def save_and_close(self):
        self.app.save_settings()
        self.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    app = App(root)
    login_toplevel = tk.Toplevel(root)
    login_window = LoginWindow(login_toplevel, app)

    root.mainloop()
