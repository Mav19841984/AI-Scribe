import tkinter as tk
from tkinter import ttk
import UI.MainWindow as mw
from UI.SettingsWindow import FeatureToggle
from UI.SettingsWindowUI import SettingsWindowUI
from UI.MarkdownWindow import MarkdownWindow
from utils.file_utils import get_file_path
from UI.DebugWindow import DebugPrintWindow

DOCKER_CONTAINER_CHECK_INTERVAL = 10000  # Interval in milliseconds to check the Docker container status
DOCKER_DESKTOP_CHECK_INTERVAL = 10000  # Interval in milliseconds to check the Docker Desktop status

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
        self.is_status_bar_enabled = False  # Flag to indicate if the Docker status bar is enabled
        self.app_settings = settings  # Application settings
        self.logic = mw.MainWindow(self.app_settings)  # Logic to control the container behavior
        self.scribe_template = None
        self.setting_window = SettingsWindowUI(self.app_settings, self, self.root)  # Settings window
        self.root.iconbitmap(get_file_path('assets','logo.ico'))
        self.debug_window_open = False  # Flag to indicate if the debug window is open

        self.warning_bar = None # Warning bar

        self.current_docker_status_check_id = None  # ID for the current Docker status check
        self.current_container_status_check_id = None  # ID for the current container status check

    def load_main_window(self):
        """
        Load the main window of the application.
        This method initializes the main window components, including the menu bar.
        """
        self._bring_to_focus()
        self._create_menu_bar()

        # Uncomment this once the UI is refactored to this class
        # For now we need to force load it after all our widgets are created
        # inside client.py. This is a temporary solution. 
        # if (self.setting_window.settings.editable_settings['Show Welcome Message']):
        #     self._show_welcome_message()

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
        # if not feature do not do this
        if FeatureToggle.DOCKER_STATUS_BAR is not True:
            return
        
        if self.docker_status_bar is not None:
            return

        # Create the frame for the Docker status bar, placed at the bottom of the window
        self.docker_status_bar = tk.Frame(self.root, bd=1, relief=tk.SUNKEN)
        self.docker_status_bar.grid(row=4, column=0, columnspan=14, sticky='nsew')

        # Add a label to indicate Docker container status section
        self.docker_status = tk.Label(self.docker_status_bar, text="Docker Container Status:", padx=10)
        self.docker_status.pack(side=tk.LEFT)

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

        self.is_status_bar_enabled = True
        self._background_availbility_docker_check()
        self._background_check_container_status(llm_dot, whisper_dot)

    def create_warning_bar(self, text):
        """
        Create a warning bar at the bottom of the window to notify the user about microphone issues.
        
        :param text: Placeholder for text input (unused).
        :param row: The row in the grid layout where the bar is placed.
        :param column: The starting column for the grid layout.
        :param columnspan: The number of columns spanned by the warning bar.
        :param pady: Padding for the vertical edges.
        :param padx: Padding for the horizontal edges.
        :param sticky: Defines how the widget expands in the grid cell.
        """
        # Create a frame for the warning bar with a sunken border and gold background
        self.warning_bar = tk.Frame(self.root, bd=1, relief=tk.SUNKEN, background="gold")
        self.warning_bar.grid(row=4, column=0, columnspan=14, sticky='nsew')

        # Add a label to display the warning message in the warning bar
        text_label = tk.Label(
            self.warning_bar,
            text=text,
            foreground="black",  # Text color
            background="gold"    # Matches the frame's background
        )
        text_label.pack(side=tk.LEFT)

        # Add a button to allow users to close the warning bar
        close_button = tk.Button(
            self.warning_bar,
            text="X",
            command=self.destroy_warning_bar,  # Call the destroy method when clicked
            foreground="black"
        )

        close_button.pack(side=tk.RIGHT)

    def destroy_warning_bar(self):
        """
        Destroy the warning bar if it exists to remove it from the UI.
        """
        if self.warning_bar is not None:
            # Destroy the warning bar frame and set the reference to None
            self.warning_bar.destroy()
            self.warning_bar = None

    def disable_docker_ui(self):
        """
        Disable the Docker status bar UI elements.
        """
        
        if FeatureToggle.DOCKER_STATUS_BAR is not True:
            return

        
        self.is_status_bar_enabled = False
        self.docker_status.config(text="(Docker not found)")
        if self.docker_status_bar is not None:
            for child in self.docker_status_bar.winfo_children():
                child.configure(state='disabled')

    def enable_docker_ui(self):
        """
        Enable the Docker status bar UI elements.
        """

        if FeatureToggle.DOCKER_STATUS_BAR is not True:
            return
        
        self.is_status_bar_enabled = True
        self.docker_status.config(text="Docker Container Status: ")
        if self.docker_status_bar is not None:
            for child in self.docker_status_bar.winfo_children():
                child.configure(state='normal')

    def destroy_docker_status_bar(self):
        """
        Destroy the Docker status bar if it exists.
        """
        if FeatureToggle.DOCKER_STATUS_BAR is not True:
            return
            
        if self.docker_status_bar is not None:
            self.docker_status_bar.destroy()
            self.docker_status_bar = None

        # cancel the check loop as the bar no longer exists and it is waster resources.
        if self.current_docker_status_check_id is not None:
            self.root.after_cancel(self.current_docker_status_check_id)
            self.current_docker_status_check_id = None
        
        if self.current_container_status_check_id is not None:
            self.root.after_cancel(self.current_container_status_check_id)
            self.current_container_status_check_id = None

    def toggle_menu_bar(self, enable: bool):
        """
        Enable or disable the menu bar.

        :param enable: True to enable the menu bar, False to disable it.
        :type enable: bool
        """
        if enable:
            self._create_menu_bar()
        else:
            self._destroy_menu_bar()

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

    def _destroy_menu_bar(self):
        """
        Private method to destroy the menu bar.
        Destroy the menu bar if it exists.
        """
        if self.menu_bar is not None:
            self.menu_bar.destroy()
            self.menu_bar = None
            self._destroy_settings_menu()
            self._destroy_help_menu()

    def _create_settings_menu(self):
        # Add Settings menu
        setting_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Settings", menu=setting_menu)
        setting_menu.add_command(label="Settings", command=self.setting_window.open_settings_window)

    def _destroy_settings_menu(self):
        """
        Private method to destroy the Settings menu.
        Destroy the Settings menu if it exists.
        """
        if self.menu_bar is not None:
            setting_menu = self.menu_bar.nametowidget('Settings')
            if setting_menu is not None:
                setting_menu.destroy()

    def _create_help_menu(self):
        # Add Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Debug Window", command=lambda: DebugPrintWindow(self))
        help_menu.add_command(label="About", command=lambda: self._show_md_content(get_file_path('markdown','help','about.md'), 'About'))

    def _destroy_help_menu(self):
        """
        Private method to destroy the Help menu.
        Destroy the Help menu if it exists.
        """
        if self.menu_bar is not None:
            help_menu = self.menu_bar.nametowidget('Help')
            if help_menu is not None:
                help_menu.destroy()

    def disable_settings_menu(self):
        """
        Disable the Settings menu.
        """
        if self.menu_bar is not None:
            self.menu_bar.entryconfig("Settings", state="disabled")  # Disables the entire Settings menu
    
    def enable_settings_menu(self):
        """
        Enable the Settings menu.
        """
        if self.menu_bar is not None:
            self.menu_bar.entryconfig("Settings", state="normal")

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
    
    def show_welcome_message(self):
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

    def _background_availbility_docker_check(self):
        """
        Check if the Docker client is available in the background.

        This method is intended to be run in a separate thread to periodically
        check the availability of the Docker client.
        """
        print("Checking Docker availability in the background...")
        if self.logic.container_manager.check_docker_availability():
            # Enable the Docker status bar UI elements if not enabled
            if not self.is_status_bar_enabled:
                self.enable_docker_ui()
            print("Docker client is available.")
        else:
            # Disable the Docker status bar UI elements if not disabled
            if self.is_status_bar_enabled:
                self.disable_docker_ui()

            print("Docker client is not available.")

        self.current_docker_status_check_id = self.root.after(DOCKER_DESKTOP_CHECK_INTERVAL, self._background_availbility_docker_check)

    def _background_check_container_status(self, llm_dot, whisper_dot):
        """
        Check the status of Docker containers in the background.

        This method is intended to be run in a separate thread to periodically
        check the status of the LLM and Whisper containers.
        """
        if self.is_status_bar_enabled:
            self.logic.container_manager.set_status_icon_color(llm_dot, self.logic.check_llm_containers())
            self.logic.container_manager.set_status_icon_color(whisper_dot, self.logic.check_whisper_containers())
            self.current_container_status_check_id = self.root.after(DOCKER_CONTAINER_CHECK_INTERVAL, self._background_check_container_status, llm_dot, whisper_dot)



