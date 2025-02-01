"""
SettingsWindowUI Module

This module provides a user interface for managing application settings.
It includes a class `SettingsWindowUI` that handles the creation and management
of a settings window using Tkinter.

This software is released under the AGPL-3.0 license
Copyright (c) 2023-2024 Braedon Hendy

Further updates and packaging added in 2024 through the ClinicianFOCUS initiative, 
a collaboration with Dr. Braedon Hendy and Conestoga College Institute of Applied 
Learning and Technology as part of the CNERG+ applied research project, 
Unburdening Primary Healthcare: An Open-Source AI Clinician Partner Platform". 
Prof. Michael Yingbull (PI), Dr. Braedon Hendy (Partner), 
and Research Students - Software Developer Alex Simko, Pemba Sherpa (F24), and Naitik Patel.

Classes:
    SettingsWindowUI: Manages the settings window UI.
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox
from UI.Widgets.AudioMeter import AudioMeter
import threading
from Model import Model, ModelManager
from utils.file_utils import get_file_path
from utils.utils import get_application_version
from UI.MarkdownWindow import MarkdownWindow
from UI.Widgets.MicrophoneSelector import MicrophoneSelector
from UI.SettingsWindow import SettingsKeys, FeatureToggle, Architectures, SettingsWindow


class SettingsWindowUI:
    """
    Manages the settings window UI.

    This class creates and manages a settings window using Tkinter. It includes
    methods to open the settings window, create various settings frames, and
    handle user interactions such as saving settings.

    Attributes:
        settings (ApplicationSettings): The settings object containing application settings.
        window (tk.Toplevel): The main settings window.
        main_frame (tk.Frame): The main frame containing the notebook.
        notebook (ttk.Notebook): The notebook widget containing different settings tabs.
        general_frame (ttk.Frame): The frame for general settings.
        advanced_frame (ttk.Frame): The frame for advanced settings.
        docker_settings_frame (ttk.Frame): The frame for Docker settings.
        basic_settings_frame (tk.Frame): The scrollable frame for basic settings.
        advanced_settings_frame (tk.Frame): The scrollable frame for advanced settings.
    """

    def __init__(self, settings, main_window, root):
        """
        Initializes the SettingsWindowUI.

        Args:
            settings (ApplicationSettings): The settings object containing application settings.
        """
        self.settings = settings
        self.main_window = main_window
        self.root = root
        self.settings_window = None
        self.main_frame = None
        self.notebook = None
        self.basic_frame = None
        self.advanced_frame = None
        self.docker_settings_frame = None
        self.basic_settings_frame = None
        self.advanced_settings_frame = None
        self.widgets = {}
        

    def open_settings_window(self):
        """
        Opens the settings window.

        This method initializes and displays the settings window, including
        the notebook with tabs for basic, advanced, and Docker settings.
        """
        self.settings_window = tk.Toplevel()
        self.settings_window.title("Settings")
        self.settings_window.geometry("775x400")  # Set initial window size
        self.settings_window.minsize(775, 400)    # Set minimum window size
        self.settings_window.resizable(True, True)
        self.settings_window.grab_set()
        self.settings_window.iconbitmap(get_file_path('assets','logo.ico'))

        self._display_center_to_parent()

        self.main_frame = tk.Frame(self.settings_window)
        self.main_frame.pack(expand=True, fill='both')

        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(expand=True, fill='both')

        self.general_settings_frame = ttk.Frame(self.notebook)
        self.llm_settings_frame = ttk.Frame(self.notebook)
        self.whisper_settings_frame = ttk.Frame(self.notebook)
        self.advanced_frame = ttk.Frame(self.notebook)
        self.docker_settings_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.general_settings_frame, text="General Settings")
        self.notebook.add(self.whisper_settings_frame, text="Speech-to-Text Settings")
        self.notebook.add(self.llm_settings_frame, text="AI Settings")
        self.notebook.add(self.advanced_frame, text="Advanced Settings")

        self.settings_window.protocol("WM_DELETE_WINDOW", self.close_window)


        self.llm_settings_frame = self.add_scrollbar_to_frame(self.llm_settings_frame)
        self.whisper_settings_frame = self.add_scrollbar_to_frame(self.whisper_settings_frame)
        self.advanced_settings_frame = self.add_scrollbar_to_frame(self.advanced_frame)

        # self.create_basic_settings()
        self._create_general_settings()
        self.create_llm_settings()
        self.create_whisper_settings()
        self.create_advanced_settings()

        if FeatureToggle.DOCKER_SETTINGS_TAB is True:
            self.notebook.add(self.docker_settings_frame, text="Docker Settings")
            self.create_docker_settings()
        
        self.create_buttons()

    def _display_center_to_parent(self):
        # Get parent window dimensions and position
        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()

        # Calculate the position for the settings window
        settings_width = 775
        settings_height = 400
        center_x = parent_x + (parent_width - settings_width) // 2
        center_y = parent_y + (parent_height - settings_height) // 2

        # Apply the calculated position to the settings window
        self.settings_window.geometry(f"{settings_width}x{settings_height}+{center_x}+{center_y}")

    def add_scrollbar_to_frame(self, frame):
        """
        Adds a scrollbar to a given frame.

        Args:
            frame (tk.Frame): The frame to which the scrollbar will be added.

        Returns:
            tk.Frame: The scrollable frame.
        """
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.settings_window.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        return scrollable_frame

    def create_whisper_settings(self):
        """
        Creates the Whisper settings UI elements in a two-column layout.
        Settings alternate between left and right columns for even distribution.
        """

        left_frame = ttk.Frame(self.whisper_settings_frame)
        left_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nw")

        right_frame = ttk.Frame(self.whisper_settings_frame)
        right_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nw")

        left_row = 0
        right_row = 0

        # Create the SettingsKeys.LOCAL_WHISPER button to handle custom behavior
        tk.Label(left_frame, text=f"{SettingsKeys.LOCAL_WHISPER.value}").grid(row=left_row, column=0, padx=0, pady=5, sticky="w")
        value = tk.IntVar(value=(self.settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value]))
        self.local_whisper_checkbox = tk.Checkbutton(left_frame, variable=value, command=self.toggle_remote_whisper_settings)
        self.local_whisper_checkbox.grid(row=left_row, column=1, padx=0, pady=5, sticky="w")
        self.settings.editable_settings_entries[SettingsKeys.LOCAL_WHISPER.value] = value

        left_row += 1

        left_row, right_row = self.create_editable_settings_col(left_frame, right_frame, left_row, right_row, self.settings.whisper_settings)
        # create the whisper model dropdown slection
        tk.Label(left_frame, text="Whisper Model").grid(row=3, column=0, padx=0, pady=5, sticky="w")
        whisper_models_drop_down_options = ["medium", "small", "tiny", "tiny.en", "base", "base.en", "small.en", "medium.en", "large"]
        self.whisper_models_drop_down = ttk.Combobox(left_frame, values=whisper_models_drop_down_options, width=20)
        self.whisper_models_drop_down.grid(row=3, column=1, padx=0, pady=5, sticky="w")

        try:
            # Try to set the whisper model dropdown to the current model
            self.whisper_models_drop_down.current(whisper_models_drop_down_options.index(self.settings.editable_settings["Whisper Model"]))
        except ValueError:
            # If not in list then just force set text
            self.whisper_models_drop_down.set(self.settings.editable_settings["Whisper Model"])

        self.settings.editable_settings_entries["Whisper Model"] = self.whisper_models_drop_down

        # create the whisper model dropdown slection
        # microphone_select = MicrophoneSelector(left_frame, left_row, 0, self.settings)
        # self.settings.editable_settings_entries["Current Mic"] = microphone_select

        
        right_row += 1

        # Whisper Architecture Dropdown
        self.whisper_architecture_label = tk.Label(left_frame, text=SettingsKeys.WHISPER_ARCHITECTURE.value)
        self.whisper_architecture_label.grid(row=left_row, column=0, padx=0, pady=5, sticky="w")
        whisper_architecture_options = self.settings.get_available_architectures()
        self.whisper_architecture_dropdown = ttk.Combobox(left_frame, values=whisper_architecture_options, width=20, state="readonly")
        if self.settings.editable_settings[SettingsKeys.WHISPER_ARCHITECTURE.value] in whisper_architecture_options:
            self.whisper_architecture_dropdown.current(whisper_architecture_options.index(self.settings.editable_settings[SettingsKeys.WHISPER_ARCHITECTURE.value]))
        else:
            # Default cpu
            self.whisper_architecture_dropdown.set(SettingsWindow.DEFAULT_WHISPER_ARCHITECTURE)
        
        self.whisper_architecture_dropdown.grid(row=left_row, column=1, padx=0, pady=5, sticky="w")
        self.settings.editable_settings_entries[SettingsKeys.WHISPER_ARCHITECTURE.value] = self.whisper_architecture_dropdown

        left_row += 1

        # set the state of the whisper settings based on the SettingsKeys.LOCAL_WHISPER.value checkbox once all widgets are created
        self.toggle_remote_whisper_settings()

    def toggle_remote_whisper_settings(self):
        current_state = self.settings.editable_settings_entries[SettingsKeys.LOCAL_WHISPER.value].get()
        
        for setting in self.settings.whisper_settings:
            if setting in ["Real Time", "BlankSpace"]:
                continue
            
            state = "normal" if current_state == 0 else "disabled"
            self.widgets[setting].config(state=state)
        
        # set the local option to disabled on switch to remote
        inverted_state = "disabled" if current_state == 0 else "normal"
        self.whisper_models_drop_down.config(state=inverted_state)
        self.whisper_architecture_dropdown.config(state=inverted_state)


    def create_llm_settings(self):
        """
        Creates the LLM settings UI elements in a two-column layout.
        Settings alternate between left and right columns for even distribution.
        """
        # Create left and right frames for the two columns
        left_frame = ttk.Frame(self.llm_settings_frame)
        left_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nw")
        
        right_frame = ttk.Frame(self.llm_settings_frame)
        right_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nw")

        self.llm_settings_frame.columnconfigure(0, weight=1)
        self.llm_settings_frame.columnconfigure(1, weight=1)

        left_row = 0
        right_row = 0

        # Use local llm button with custom handler
        tk.Label(left_frame, text="Local LLM").grid(row=left_row, column=0, padx=0, pady=5, sticky="w")
        value = tk.IntVar(value=(self.settings.editable_settings["Use Local LLM"]))
        self.local_llm_checkbox = tk.Checkbutton(left_frame, variable=value, command=self.toggle_remote_llm_settings)
        self.local_llm_checkbox.grid(row=left_row, column=1, padx=0, pady=5, sticky="w")
        self.settings.editable_settings_entries["Use Local LLM"] = value

        left_row += 1

        #6. GPU OR CPU SELECTION (Right Column)
        self.local_architecture_label = tk.Label(left_frame, text="Local Architecture")
        self.local_architecture_label.grid(row=left_row, column=0, padx=0, pady=5, sticky="w")
        architecture_options = self.settings.get_available_architectures()
        self.architecture_dropdown = ttk.Combobox(left_frame, values=architecture_options, width=20, state="readonly")
        if self.settings.editable_settings[SettingsKeys.LLM_ARCHITECTURE.value] in architecture_options:
            self.architecture_dropdown.current(architecture_options.index(self.settings.editable_settings[SettingsKeys.LLM_ARCHITECTURE.value]))
        else:
            # Default cpu
            self.architecture_dropdown.set(Architectures.CPU.label)

        self.architecture_dropdown.grid(row=left_row, column=1, padx=0, pady=5, sticky="w")

        # hide architecture dropdown if architecture only has one option
        if len(architecture_options) == 1:
            self.local_architecture_label.grid_forget()
            self.architecture_dropdown.grid_forget()


        left_row += 1

        # 5. Models (Left Column)
        tk.Label(left_frame, text="Models").grid(row=left_row, column=0, padx=0, pady=5, sticky="w")
        models_drop_down_options = []
        self.models_drop_down = ttk.Combobox(left_frame, values=models_drop_down_options, width=20, state="readonly")
        self.models_drop_down.grid(row=left_row, column=1, padx=0, pady=5, sticky="w")
        self.models_drop_down.bind('<<ComboboxSelected>>', self.on_model_selection_change)
        thread = threading.Thread(target=self.settings.update_models_dropdown, args=(self.models_drop_down,))
        thread.start()

        # Create custom model entry (initially hidden)
        self.custom_model_entry = tk.Entry(left_frame, width=15)
        self.custom_model_entry.insert(0, self.settings.editable_settings["Model"])

        refresh_button = ttk.Button(left_frame, text="↻", 
                                command=lambda: (self.save_settings(False), threading.Thread(target=self.settings.update_models_dropdown, args=(self.models_drop_down,)).start(), self.on_model_selection_change(None)), 
                                width=4)
        refresh_button.grid(row=left_row, column=2, padx=0, pady=5, sticky="w")

        left_row += 1

        right_frame, right_row = self.create_editable_settings(right_frame, self.settings.llm_settings, padx=0, pady=0)

        # 2. OpenAI API Key (Right Column)
        tk.Label(right_frame, text="OpenAI API Key:").grid(row=right_row, column=0, padx=0, pady=5, sticky="w")
        self.openai_api_key_entry = tk.Entry(right_frame, width=25)
        self.openai_api_key_entry.insert(0, self.settings.OPENAI_API_KEY)
        self.openai_api_key_entry.grid(row=right_row, column=1, columnspan=2, padx=0, pady=5, sticky="w")
        
        right_row += 1

        #################################################################
        #                                                               #
        #               API STYLE SELECTION                             #
        #   THIS SECTION IS COMENTED OUT FOR FUTURE RELEASE AND REVIEW. #
        #   THE ONLY API STYLE SUPPORTED FOR NOW IS OPENAI.             #
        #   THE KOBOLD API STYLE HAS BEEN REMOVED FOR SIMPLIFICATION    #
        #                                                               #
        #################################################################
        # # 3. API Style (Left Column)
        # tk.Label(right_frame, text="API Style:").grid(row=right_row, column=0, padx=0, pady=5, sticky="w")
        # api_options = ["OpenAI", "KoboldCpp"]
        # self.api_dropdown = ttk.Combobox(right_frame, values=api_options, width=15, state="readonly")
        # self.api_dropdown.current(api_options.index(self.settings.API_STYLE))
        # self.api_dropdown.grid(row=right_row, column=1, columnspan=2, padx=0, pady=5, sticky="w")
        # right_row += 1

        # set the state of the llm settings based on the local llm checkbox once all widgets are created
        self.settings_opened = True
        self.toggle_remote_llm_settings()
 
    def toggle_remote_llm_settings(self):
        current_state = self.settings.editable_settings_entries["Use Local LLM"].get()
        
        state = "normal" if current_state == 0 else "disabled"


        # toggle all manual settings based on the local llm checkbox
        self.openai_api_key_entry.config(state=state)
        # self.api_dropdown.config(state=state)

        for setting in self.settings.llm_settings:
            if setting == "BlankSpace":
                continue
            
            self.widgets[setting].config(state=state)

        inverted_state = "disabled" if current_state == 0 else "normal"
        self.architecture_dropdown.config(state=inverted_state)
        
        #flag used for determining if window was just opened so we dont spam the API.
        if not self.settings_opened:
            threading.Thread(target=self.settings.update_models_dropdown, args=(self.models_drop_down,self.settings.editable_settings_entries["Model Endpoint"].get(),)).start()
        else:
            self.settings_opened = False
            
        self.on_model_selection_change(None)

            

    def on_model_selection_change(self, event):
        """
        Handle switching between model dropdown and custom model entry.
        
        When "Custom" is selected, shows a text entry field and hides the dropdown.
        When another model is selected, shows the dropdown and hides the custom entry.
        
        Args:
            event: The dropdown selection change event
            
        Notes:
            - Uses grid_info() to check if widgets are currently displayed
            - Preserves the row position when swapping widgets
            - Resets dropdown to placeholder when showing custom entry
        """
        if self.models_drop_down.get() == "Custom" and self.custom_model_entry.grid_info() == {}:
            # Show the custom model entry below the dropdown
            self.custom_model_entry.grid(row=self.models_drop_down.grid_info()['row'], 
                        column=1, padx=0, pady=5, sticky="w")
            self.models_drop_down.set("Select a Model")
            self.models_drop_down.grid_remove()
        elif self.models_drop_down.get() != "Custom" and self.custom_model_entry.grid_info() != {}:
            # Hide the custom model entry
            self.models_drop_down.grid(row=self.custom_model_entry.grid_info()['row'], 
                        column=1, padx=0, pady=5, sticky="w")
            self.custom_model_entry.grid_remove()

    def get_selected_model(self):
        """Returns the selected model, either from dropdown or custom entry"""
        if self.models_drop_down.get() in ["Custom", "Select a Model"]:
            return self.custom_model_entry.get()
        return self.models_drop_down.get()

    def create_editable_settings_col(self, left_frame, right_frame, left_row, right_row, settings_set):
        """
        Creates editable settings in two columns.

        This method splits the settings evenly between two columns and creates the
        corresponding UI elements in the left and right frames.

        :param left_frame: The frame for the left column.
        :param right_frame: The frame for the right column.
        :param left_row: The starting row for the left column.
        :param right_row: The starting row for the right column.
        :param settings_set: The set of settings to be displayed.
        :return: The updated row indices for the left and right columns.
        """
        mid_point = (len(settings_set) + 1) // 2  # Round up for odd numbers

        # Process left column
        left_row = self._process_column(left_frame, settings_set[:mid_point], left_row)

        # Process right column
        right_row = self._process_column(right_frame, settings_set[mid_point:], right_row)

        return left_row, right_row
    
    def _process_column(self, frame, settings, start_row):
        """
        Processes a column of settings.

        This helper method creates the UI elements for a column of settings.

        :param frame: The frame for the column.
        :param settings: The settings to be displayed in the column.
        :param start_row: The starting row for the column.
        :return: The updated row index for the column.
        """
        row = start_row
        for setting_name in settings:

            if setting_name == "BlankSpace":
                row += 1
                continue

            value = self.settings.editable_settings[setting_name]
            if value in [True, False]:
                self.widgets[setting_name] = self._create_checkbox(frame, setting_name, setting_name, row)
            else:
                self.widgets[setting_name] = self._create_entry(frame, setting_name, setting_name, row)
            row += 1
        return row

    def create_advanced_settings(self):
        """Creates the advanced settings UI elements with a structured layout."""

        def create_settings_columns(settings, row):
            left_frame = ttk.Frame(self.advanced_settings_frame)
            right_frame = ttk.Frame(self.advanced_settings_frame)
            left_frame.grid(row=row, column=0, padx=10, pady=5, sticky="nw")
            right_frame.grid(row=row, column=1, padx=10, pady=5, sticky="nw")
            self.create_editable_settings_col(left_frame, right_frame, 0, 0, settings)
            return row + 1

        def create_processing_section(label_text, setting_key, text_content, row):
            frame = tk.Frame(self.advanced_settings_frame, width=800)
            frame.grid(row=row, column=0, padx=10, pady=0, sticky="nw")
            self._create_checkbox(frame, f"Use {label_text}", setting_key, 0)
            row += 1
            
            text_area, row = self._create_text_area(label_text, text_content, row)
            return text_area, row

        row = self._create_section_header("⚠️ Advanced Settings (For Advanced Users Only)", 0, text_colour="red")
        
        # General Settings
        if len(self.settings.adv_general_settings) > 0:
            row = self._create_section_header("General Settings", row, text_colour="black")
            row = create_settings_columns(self.settings.adv_general_settings, row)

        # Whisper Settings
        row = self._create_section_header("Whisper Settings", row, text_colour="black")
        left_frame = ttk.Frame(self.advanced_settings_frame)
        left_frame.grid(row=row, column=0, padx=10, pady=5, sticky="nw")
        right_frame = ttk.Frame(self.advanced_settings_frame)
        right_frame.grid(row=row, column=1, padx=10, pady=5, sticky="nw")
        
        self.create_editable_settings_col(left_frame, right_frame, 0, 0, self.settings.adv_whisper_settings)
        
        # # Audio meter
        # tk.Label(left_frame, text="Whisper Audio Cutoff").grid(row=1, column=0, padx=0, pady=0, sticky="w")
        # self.cutoff_slider = AudioMeter(left_frame, width=150, height=50, 
        #                             threshold=self.settings.editable_settings["Silence cut-off"] * 32768)
        # self.cutoff_slider.grid(row=1, column=1, padx=0, pady=0, sticky="w")
        row += 1

        # AI Settings
        row = self._create_section_header("AI Settings", row, text_colour="black")
        row = create_settings_columns(self.settings.adv_ai_settings, row)
        
        # Prompting Settings
        row = self._create_section_header("Prompting Settings", row, text_colour="black")
        self.aiscribe_text, row = self._create_text_area("Pre Prompting", self.settings.AISCRIBE, row)
        self.aiscribe2_text, row = self._create_text_area("Post Prompting", self.settings.AISCRIBE2, row)
        
        # Processing Sections
        self.preprocess_text, row = create_processing_section(
            "Pre-Processing", 
            "Use Pre-Processing",
            self.settings.editable_settings["Pre-Processing"],
            row
        )
        
        self.postprocess_text, _ = create_processing_section(
            "Post-Processing (Experimental. Use with caution.)",
            "Use Post-Processing", 
            self.settings.editable_settings["Post-Processing"],
            row
        )


    def create_docker_settings(self):
        """
        Creates the Docker settings UI elements.

        This method creates and places UI elements for Docker settings.
        """
        self.create_editable_settings(self.docker_settings_frame, self.settings.docker_settings)

    def create_editable_settings(self, frame, settings_set, start_row=0, padx=10, pady=5):
        """
        Creates editable settings UI elements.

        Args:
            frame (tk.Frame): The frame in which to create the settings.
            settings_set (list): The list of settings to create UI elements for.
            start_row (int): The starting row for placing the settings.
        """
        
        i_frame = ttk.Frame(frame)
        i_frame.grid(row=0, column=0, padx=padx, pady=pady, sticky="nw")
        row = self._process_column(i_frame, settings_set, start_row)
        return i_frame, row

    def create_buttons(self):
        """
        Creates the buttons for the settings window.

        This method creates and places buttons for saving settings, resetting to default,
        and closing the settings window.
        """
        footer_frame = tk.Frame(self.main_frame,bg="lightgray", height=30)
        footer_frame.pack(side="bottom", fill="x")

        # Place the "Help" button on the left
        tk.Button(footer_frame, text="Help", width=10, command=self.create_help_window).pack(side="left", padx=2, pady=5)

        # Place the label in the center
        version = get_application_version()
        tk.Label(footer_frame, text=f"FreeScribe Client {version}",bg="lightgray",fg="black").pack(side="left", expand=True, padx=2, pady=5)

        # Create a frame for the right-side elements
        right_frame = tk.Frame(footer_frame)
        right_frame.pack(side="right")

        # Pack all other buttons into the right frame
        tk.Button(right_frame, text="Close", width=10, command=self.close_window).pack(side="right", padx=2, pady=5)
        tk.Button(right_frame, text="Default", width=10, command=self.reset_to_default).pack(side="right", padx=2, pady=5)
        tk.Button(right_frame, text="Save", width=10, command=self.save_settings).pack(side="right", padx=2, pady=5)

    def create_help_window(self):
        """
        Creates a help window for the settings.

        Uses our markdown window class to display a markdown with help
        """
        MarkdownWindow(self.settings_window, "Help", get_file_path('markdown','help','settings.md'))

    def save_settings(self, close_window=True):
        """
        Saves the settings entered by the user.

        This method retrieves the values from the UI elements and calls the
        `save_settings` method of the `settings` object to save the settings.
        """
        self.settings.load_or_unload_model(self.settings.editable_settings["Model"],
            self.get_selected_model(),
            self.settings.editable_settings["Use Local LLM"],
            self.settings.editable_settings_entries["Use Local LLM"].get(),
            self.settings.editable_settings[SettingsKeys.LLM_ARCHITECTURE.value],
            self.architecture_dropdown.get())

        if self.get_selected_model() not in ["Loading models...", "Failed to load models"]:
            self.settings.editable_settings["Model"] = self.get_selected_model()

        self.settings.update_whisper_model()

        self.settings.editable_settings["Pre-Processing"] = self.preprocess_text.get("1.0", "end-1c") # end-1c removes the trailing newline
        self.settings.editable_settings["Post-Processing"] = self.postprocess_text.get("1.0", "end-1c") # end-1c removes the trailing newline

        # save architecture
        self.settings.editable_settings[SettingsKeys.LLM_ARCHITECTURE.value] = self.architecture_dropdown.get()

        self.settings.save_settings(
            self.openai_api_key_entry.get(),
            self.aiscribe_text.get("1.0", "end-1c"), # end-1c removes the trailing newline
            self.aiscribe2_text.get("1.0", "end-1c"), # end-1c removes the trailing newline
            self.settings_window,
            # self.api_dropdown.get(),
            self.settings.editable_settings["Silence cut-off"], # Save the old one for whisper audio cutoff, will be removed in future, left in incase we go back to old cut off
            # self.cutoff_slider.threshold / 32768, # old threshold 
        )

        if self.settings.editable_settings["Use Docker Status Bar"] and self.main_window.docker_status_bar is None:
            self.main_window.create_docker_status_bar()
        elif not self.settings.editable_settings["Use Docker Status Bar"] and self.main_window.docker_status_bar is not None:
            self.main_window.destroy_docker_status_bar()

        if self.settings.editable_settings["Enable Scribe Template"]:
            self.main_window.create_scribe_template()
        else:
            self.main_window.destroy_scribe_template()

        if close_window:
            self.close_window()


    def reset_to_default(self):
        """
        Resets the settings to their default values.

        This method calls the `clear_settings_file` method of the `settings` object
        to reset the settings to their default values.
        """
        self.settings.clear_settings_file(self.settings_window)

    def _create_general_settings(self):
        """
        Creates the general settings UI elements.

        This method creates and places UI elements for general settings.
        """
        frame, row = self.create_editable_settings(self.general_settings_frame, self.settings.general_settings)
        
        # Add a note at the bottom of the general settings frame
        note_text = (
        "NOTE: To protect personal health information (PHI), we recommend using a local network.\n"
        "The 'Show Scrub PHI' feature is only applicable for local LLMs and private networks.\n"
        "For internet-facing endpoints, this feature will always be enabled, regardless of the 'Show Scrub PHI' setting."
    )

        # Create a frame to hold the note labels
        note_frame = tk.Frame(self.general_settings_frame)
        note_frame.grid(padx=10, pady=5, sticky="w")

        # Add the red * label
        star_label = tk.Label(note_frame, text="*", fg="red", font=("Arial", 10, "bold"))
        star_label.grid(row=0, column=0, sticky="w")

        # Add the rest of the text in black (bold and underlined)
        note_label = tk.Label(
            note_frame,
            text=note_text,
            fg="black",  # Set text color to black
            font=("Arial", 8, "bold underline"),  # Set font to bold and underlined
            wraplength=400,
            justify="left"
        )
        note_label.grid(row=0, column=1, sticky="w")

    def _create_checkbox(self, frame, label, setting_name, row_idx, setting_key=None):
        """
        Creates a checkbox in the given frame.

        This method creates a label and a checkbox in the given frame for editing.

        Args:
            frame (tk.Frame): The frame in which to create the checkbox.
            label (str): The label to display next to the checkbox.
            setting_name (str): The name of the setting to edit.
            row_idx (int): The row index at which to place the checkbox.
        """
        tk.Label(frame, text=label).grid(row=row_idx, column=0, padx=0, pady=5, sticky="w")
        value = tk.IntVar(value=int(self.settings.editable_settings[setting_name]))
        checkbox = tk.Checkbutton(frame, variable=value)
        checkbox.grid(row=row_idx, column=1, padx=0, pady=5, sticky="w")
        self.settings.editable_settings_entries[setting_name] = value
        return checkbox

    def _create_entry(self, frame, label, setting_name, row_idx):
        """
        Creates an entry field in the given frame.

        This method creates a label and an entry field in the given frame for editing.
        
        Args:
            frame (tk.Frame): The frame in which to create the entry field.
            label (str): The label to display next to the entry field.
            setting_name (str): The name of the setting to edit.
            row_idx (int): The row index at which to place the entry field.
        """
        tk.Label(frame, text=label).grid(row=row_idx, column=0, padx=0, pady=5, sticky="w")
        value = self.settings.editable_settings[setting_name]
        entry = tk.Entry(frame, width=25)
        entry.insert(0, str(value))
        entry.grid(row=row_idx, column=1, padx=0, pady=5, sticky="w")
        self.settings.editable_settings_entries[setting_name] = entry
        return entry

    def _create_section_header(self, text, row, text_colour="black"):
        """
        Creates a section header label in the advanced settings frame.
        
        Args:
            text (str): Text to display in the header
            row (int): Grid row position to place the header
            text_colour (str): Color of header text (default "black")
            
        Returns:
            int: Next available grid row number
        """
        ttk.Label(
            self.advanced_settings_frame, 
            text=text,
            font=("TkDefaultFont", 10, "bold"),
            foreground=text_colour
        ).grid(row=row, column=0, columnspan=2, padx=10, 
            pady=(5 if text.startswith("⚠️") else 0, 10 if text.startswith("⚠️") else 0), 
            sticky="w")
        return row + 1

    def _create_text_area(self, label_text, text_content, row):
        """
        Creates a labeled text area widget in the advanced settings frame.
        
        Args:
            label_text (str): Label text to display above text area
            text_content (str): Initial text to populate the text area
            row (int): Starting grid row position
            
        Returns:
            tuple: (Text widget object, next available grid row number)
        """
        tk.Label(self.advanced_settings_frame, text=label_text).grid(
            row=row, column=0, padx=10, pady=5, sticky="w")
        row += 1
        text_area = tk.Text(self.advanced_settings_frame, height=10, width=50)
        text_area.insert(tk.END, text_content)
        text_area.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        return text_area, row + 1

    def close_window(self):
        """
        Cleans up the settings window.

        This method destroys the settings window and clears the settings entries.
        """
        self.settings_window.unbind_all("<MouseWheel>") # Unbind mouse wheel event causing errors
        self.settings_window.unbind_all("<Configure>") # Unbind the configure event causing errors
        
        if hasattr(self, "cutoff_slider"):
            if self.cutoff_slider is not None:
                self.cutoff_slider.destroy()

        self.settings_window.destroy()
