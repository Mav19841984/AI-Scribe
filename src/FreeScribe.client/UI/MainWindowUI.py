import tkinter as tk
from tkinter import ttk
import UI.MainWindow as mw
from UI.SettingsWindowUI import SettingsWindowUI
from UI.MarkdownWindow import MarkdownWindow
from utils.file_utils import get_file_path

class MainWindowUI:
    """
    This class handles the user interface (UI) for the main application window, 
    including the Docker status bar for managing the LLM and Whisper containers.

    :param root: The root Tkinter window.
    :param settings: The application settings passed to control the containers' behavior.
    """
    
    def __init__(self, root, settings):
        """
        Initialize the MainWindowUI class.

        :param root: The Tkinter root window.
        :param settings: The application settings used to control container states.
        """
        self.root = root  # Tkinter root window
        self.docker_status_bar = None  # Docker status bar frame
        self.app_settings = settings  # Application settings
        self.logic = mw.MainWindow(self.app_settings)  # Logic to control the container behavior
        self.scribe_template = None
        self.setting_window = SettingsWindowUI(self.app_settings, self)  # Settings window
        self.root.iconbitmap(get_file_path('assets','logo.ico'))

    def load_main_window(self):
        """
        Load the main window of the application.
        This method initializes the main window components, including the menu bar.
        """
        self._bring_to_focus()
        self._create_menu_bar()
        if (self.setting_window.settings.editable_settings['Show Welcome Message']):
            self._show_welcome_message()

    def _bring_to_focus(self):
        """
        Bring the main window to focus.
        """
        self.root.lift()  # Lift the window to the top
        self.root.attributes('-topmost', True)  # Set the window to be always on top
        self.root.focus_force()  # Force focus on the window
        self.root.after_idle(self.root.attributes, '-topmost', False)  # Reset the always on top attribute after idle
        

    def update_aiscribe_texts(self, event):
        if self.scribe_template is not None:
            selected_option = self.scribe_template.get()
            if selected_option in self.app_settings.scribe_template_mapping:
                self.app_settings.AISCRIBE, self.app_settings.AISCRIBE2 = self.app_settings.scribe_template_mapping[selected_option]

    def create_docker_status_bar(self):
        """
        Create a Docker status bar to display the status of the LLM and Whisper containers.
        Adds start and stop buttons for each container.
        """
        
        if self.docker_status_bar is not None:
            return

        # Create the frame for the Docker status bar, placed at the bottom of the window
        self.docker_status_bar = tk.Frame(self.root, bd=1, relief=tk.SUNKEN)
        self.docker_status_bar.grid(row=4, column=0, columnspan=14, sticky='nsew')

        # Add a label to indicate Docker container status section
        docker_status = tk.Label(self.docker_status_bar, text="Docker Container Status:", padx=10)
        docker_status.pack(side=tk.LEFT)

        # Add LLM container status label
        llm_status = tk.Label(self.docker_status_bar, text="LLM Container Status:", padx=10)
        llm_status.pack(side=tk.LEFT)

        # Add status dot for LLM (default: red)
        llm_dot = tk.Label(self.docker_status_bar, text='●', fg='red')
        self.logic.container_manager.update_container_status_icon(llm_dot, self.app_settings.editable_settings["LLM Container Name"])
        llm_dot.pack(side=tk.LEFT)

        # Add Whisper server status label
        whisper_status = tk.Label(self.docker_status_bar, text="Whisper Server Status:", padx=10)
        whisper_status.pack(side=tk.LEFT)

        # Add status dot for Whisper (default: red)
        whisper_dot = tk.Label(self.docker_status_bar, text='●', fg='red')
        self.logic.container_manager.update_container_status_icon(whisper_dot, self.app_settings.editable_settings["Whisper Container Name"])
        whisper_dot.pack(side=tk.LEFT)

        # Start button for Whisper container with a command to invoke the start method from logic
        start_whisper_button = tk.Button(self.docker_status_bar, text="Start Whisper", command=lambda: self.logic.start_whisper_container(whisper_dot, self.app_settings))
        start_whisper_button.pack(side=tk.RIGHT)

        # Start button for LLM container with a command to invoke the start method from logic
        start_llm_button = tk.Button(self.docker_status_bar, text="Start LLM", command=lambda: self.logic.start_LLM_container(llm_dot, self.app_settings))
        start_llm_button.pack(side=tk.RIGHT)

        # Stop button for Whisper container with a command to invoke the stop method from logic
        stop_whisper_button = tk.Button(self.docker_status_bar, text="Stop Whisper", command=lambda: self.logic.stop_whisper_container(whisper_dot, self.app_settings))
        stop_whisper_button.pack(side=tk.RIGHT)

        # Stop button for LLM container with a command to invoke the stop method from logic
        stop_llm_button = tk.Button(self.docker_status_bar, text="Stop LLM", command=lambda: self.logic.stop_LLM_container(llm_dot, self.app_settings))
        stop_llm_button.pack(side=tk.RIGHT)

        if self.logic.container_manager.client is not None:
            self.enable_docker_ui()
        else:
            docker_status.config(text="(Docker not found)")
            self.disable_docker_ui()

    def disable_docker_ui(self):
        """
        Disable the Docker status bar UI elements.
        """
        if self.docker_status_bar is not None:
            for child in self.docker_status_bar.winfo_children():
                child.configure(state='disabled')

    def enable_docker_ui(self):
        """
        Enable the Docker status bar UI elements.
        """
        if self.docker_status_bar is not None:
            for child in self.docker_status_bar.winfo_children():
                child.configure(state='normal')

    def destroy_docker_status_bar(self):
        """
        Destroy the Docker status bar if it exists.
        """
        if self.docker_status_bar is not None:
            self.docker_status_bar.destroy()
            self.docker_status_bar = None

    def _create_menu_bar(self):
        """
        Private method to create menu bar.
        Create a menu bar with a Help menu.
        This method sets up the menu bar at the top of the main window and adds a Help menu with an About option.
        """
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        self._create_settings_menu()
        self._create_help_menu()

    def _create_settings_menu(self):
        # Add Settings menu
        setting_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Settings", menu=setting_menu)
        setting_menu.add_command(label="Settings", command=self.setting_window.open_settings_window)

    def _create_help_menu(self):
        # Add Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=lambda: self._show_md_content(get_file_path('markdown','help','about.md'), 'About'))

    
    def _show_md_content(self, file_path: str, title: str, show_checkbox: bool = False):
        """
        Private method to display help/about information.
        Display help information in a message box.
        This method shows a message box with information about the application when the About option is selected from the Help menu.
        """

        # Callback function called when the window is closed
        def on_close(checkbox_state):
            self.setting_window.settings.editable_settings['Show Welcome Message'] = not checkbox_state
            self.setting_window.settings.save_settings_to_file()
        
        # Create a MarkdownWindow to display the content
        MarkdownWindow(self.root, title, file_path, 
                  callback=on_close if show_checkbox else None)
            

    def _on_help_window_close(self, help_window, dont_show_again: tk.BooleanVar):
        """
        Private method to handle the closing of the help window.
        Updates the 'Show Welcome Message' setting based on the checkbox state.
        """
        self.setting_window.settings.editable_settings['Show Welcome Message'] = not dont_show_again.get()
        self.setting_window.settings.save_settings_to_file()
        help_window.destroy()
    
    def _show_welcome_message(self):
        """
        Private method to display a welcome message.
        Display a welcome message when the application is launched.
        This method shows a welcome message in a message box when the application is launched.
        """
        self._show_md_content(get_file_path('markdown','welcome.md'), 'Welcome', True)
    
    def create_scribe_template(self, row=3, column=4, columnspan=3, pady=10, padx=10, sticky='nsew'):
        """
        Create a template for the Scribe application.
        """
        self.scribe_template = ttk.Combobox(self.root, values=self.app_settings.scribe_template_values, width=35, state="readonly")
        self.scribe_template.current(0)
        self.scribe_template.bind("<<ComboboxSelected>>", self.app_settings.scribe_template_values)
        self.scribe_template.grid(row=row, column=column, columnspan=columnspan, pady=pady, padx=padx, sticky=sticky)
    
    def destroy_scribe_template(self):
        """
        Destroy the Scribe template if it exists.
        """
        if self.scribe_template is not None:
            self.scribe_template.destroy()
            self.scribe_template = None

