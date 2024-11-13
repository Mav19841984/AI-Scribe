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
from UI.MarkdownWindow import MarkdownWindow



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

    def __init__(self, settings, main_window):
        """
        Initializes the SettingsWindowUI.

        Args:
            settings (ApplicationSettings): The settings object containing application settings.
        """
        self.settings = settings
        self.main_window = main_window
        self.settings_window = None
        self.main_frame = None
        self.notebook = None
        self.basic_frame = None
        self.advanced_frame = None
        self.docker_settings_frame = None
        self.basic_settings_frame = None
        self.advanced_settings_frame = None
        

    def open_settings_window(self):
        """
        Opens the settings window.

        This method initializes and displays the settings window, including
        the notebook with tabs for basic, advanced, and Docker settings.
        """
        self.settings_window = tk.Toplevel()
        self.settings_window.title("Settings")
        self.settings_window.geometry("600x450")  # Set initial window size
        self.settings_window.minsize(600, 500)    # Set minimum window size
        self.settings_window.resizable(True, True)
        self.settings_window.grab_set()
        self.settings_window.iconbitmap(get_file_path('assets','logo.ico'))

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
        self.notebook.add(self.llm_settings_frame, text="AI Settings")
        self.notebook.add(self.whisper_settings_frame, text="Whisper Settings")
        self.notebook.add(self.advanced_frame, text="Advanced Settings")
        self.notebook.add(self.docker_settings_frame, text="Docker Settings")

        self.settings_window.protocol("WM_DELETE_WINDOW", self.close_window)


        self.llm_settings_frame = self.add_scrollbar_to_frame(self.llm_settings_frame)
        self.whisper_settings_frame = self.add_scrollbar_to_frame(self.whisper_settings_frame)
        self.advanced_settings_frame = self.add_scrollbar_to_frame(self.advanced_frame)

        # self.create_basic_settings()
        self._create_general_settings()
        self.create_llm_settings()
        self.create_whisper_settings()
        self.create_advanced_settings()
        self.create_docker_settings()
        self.create_buttons()


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


        self.create_editable_settings_col(left_frame, right_frame, left_row, right_row, self.settings.whisper_settings)

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

        left_row = 0
        right_row = 0

        # 1. LLM Preset (Left Column)
        tk.Label(left_frame, text="LLM Preset:").grid(row=left_row, column=0, padx=0, pady=5, sticky="w")
        llm_preset_options = ["JanAI", "ChatGPT", "ClinicianFocus Toolbox", "Custom"]
        self.llm_preset_dropdown = ttk.Combobox(left_frame, values=llm_preset_options, width=15, state="readonly")
        self.llm_preset_dropdown.current(llm_preset_options.index(self.settings.editable_settings["Preset"]))
        self.llm_preset_dropdown.grid(row=left_row, column=1, padx=0, pady=5, sticky="w")

        load_preset_btn = ttk.Button(left_frame, text="Load", width=5, 
                                    command=lambda: self.settings.load_settings_preset(self.llm_preset_dropdown.get(), self))
        load_preset_btn.grid(row=left_row, column=2, padx=0, pady=5, sticky="w")
        left_row += 1

        # 2. OpenAI API Key (Right Column)
        tk.Label(right_frame, text="OpenAI API Key:").grid(row=right_row, column=0, padx=0, pady=5, sticky="w")
        self.openai_api_key_entry = tk.Entry(right_frame, width=25)
        self.openai_api_key_entry.insert(0, self.settings.OPENAI_API_KEY)
        self.openai_api_key_entry.grid(row=right_row, column=1, columnspan=2, padx=0, pady=5, sticky="w")
        right_row += 1

        # 3. API Style (Left Column)
        tk.Label(left_frame, text="API Style:").grid(row=left_row, column=0, padx=0, pady=5, sticky="w")
        api_options = ["OpenAI", "KoboldCpp"]
        self.api_dropdown = ttk.Combobox(left_frame, values=api_options, width=15, state="readonly")
        self.api_dropdown.current(api_options.index(self.settings.API_STYLE))
        self.api_dropdown.grid(row=left_row, column=1, columnspan=2, padx=0, pady=5, sticky="w")
        left_row += 1

        # 4. Enable SSL (Right Column)
        self.ssl_enable_var = tk.IntVar(value=int(self.settings.SSL_ENABLE))
        tk.Label(right_frame, text="Enable SSL:").grid(row=right_row, column=0, padx=0, pady=5, sticky="w")
        self.ssl_enable_checkbox = tk.Checkbutton(right_frame, variable=self.ssl_enable_var)
        self.ssl_enable_checkbox.grid(row=right_row, column=1, columnspan=2, padx=0, pady=5, sticky="w")
        right_row += 1

        # 5. Models (Left Column)
        tk.Label(left_frame, text="Models").grid(row=left_row, column=0, padx=0, pady=5, sticky="w")
        models_drop_down_options = []
        self.models_drop_down = ttk.Combobox(left_frame, values=models_drop_down_options, width=15, state="readonly")
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

        #6. GPU OR CPU SELECTION (Right Column)
        tk.Label(right_frame, text="Local Architecture").grid(row=right_row, column=0, padx=0, pady=5, sticky="w")
        architecture_options = ["CPU", "CUDA (Nvidia GPU)"]
        self.architecture_dropdown = ttk.Combobox(right_frame, values=architecture_options, width=15, state="readonly")
        self.architecture_dropdown.current(architecture_options.index(self.settings.editable_settings["Architecture"]))

        self.architecture_dropdown.grid(row=right_row, column=1, padx=0, pady=5, sticky="w")

        
        right_row += 1

        # # Restart Local Llm Button
        # restart_llm_button = ttk.Button(right_frame, text="Restart LLM", width=15, command=lambda: self.restart_local_llm())

        # 6. Self-Signed Cert (Right Column)
        self.ssl_selfcert_var = tk.IntVar(value=int(self.settings.SSL_SELFCERT))
        tk.Label(right_frame, text="Self-Signed Cert:").grid(row=right_row, column=0, padx=0, pady=5, sticky="w")
        self.ssl_selfcert_checkbox = tk.Checkbutton(right_frame, variable=self.ssl_selfcert_var)
        self.ssl_selfcert_checkbox.grid(row=right_row, column=1, columnspan=2, padx=0, pady=5, sticky="w")
        right_row += 1
        
        self.create_editable_settings_col(left_frame, right_frame, left_row, right_row, self.settings.llm_settings)
 
    def on_model_selection_change(self, event):
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
            value = self.settings.editable_settings[setting_name]
            if value in [True, False]:
                self._create_checkbox(frame, setting_name, setting_name, row)
            else:
                self._create_entry(frame, setting_name, setting_name, row)
            row += 1
        return row

    def create_advanced_settings(self):
        """
        Creates the advanced settings UI elements.

        This method creates and places UI elements for advanced settings such as
        editable settings, pre-prompting, and post-prompting text areas.
        """
        # Create left and right frames for the two columns
        left_frame = ttk.Frame(self.advanced_settings_frame)
        left_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nw")
        
        right_frame = ttk.Frame(self.advanced_settings_frame)
        right_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nw")

        left_row = 0
        right_row = 0

        left_row, right_row = self.create_editable_settings_col(left_frame, right_frame, left_row, right_row, self.settings.advanced_settings)

        target_frame = None
        row_idx = None

        if left_row > right_row:
            target_frame = right_frame
            row_idx = right_row
        else:
            target_frame = left_frame
            row_idx = left_row

        tk.Label(target_frame, text="Whisper Audio Cutoff").grid(row=row_idx, column=0, padx=0, pady=0, sticky="w")

        # Create audio meter for silence cut-off, used for setting microphone cutoff in Whisper
        self.cutoff_slider = AudioMeter(target_frame, width=150, height=50, threshold=self.settings.editable_settings["Silence cut-off"] * 32768)
        self.cutoff_slider.grid(row=row_idx, column=1, padx=0, pady=0, sticky="w")

        row_idx += 1

        tk.Label(self.advanced_settings_frame, text="Pre Prompting").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        row_idx += 1

        self.aiscribe_text = tk.Text(self.advanced_settings_frame, height=10, width=50)
        self.aiscribe_text.insert(tk.END, self.settings.AISCRIBE)
        self.aiscribe_text.grid(row=row_idx, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        row_idx += 1

        tk.Label(self.advanced_settings_frame, text="Post Prompting").grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")

        row_idx += 1
        self.aiscribe2_text = tk.Text(self.advanced_settings_frame, height=10, width=50)
        self.aiscribe2_text.insert(tk.END, self.settings.AISCRIBE2)
        self.aiscribe2_text.grid(row=row_idx, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Pre-Processing Checkbox
        row_idx += 1

        preprocess_frame = tk.Frame(self.advanced_settings_frame, width=800)
        preprocess_frame.grid(row=row_idx, column=0, padx=10, pady=0, sticky="nw")
        self._create_checkbox(preprocess_frame, "Use Pre-Processing", "Use Pre-Processing", 0)

        # Pre-Processing Label and Text Area
        row_idx += 1
        self.preprocess_label = tk.Label(self.advanced_settings_frame, text="Pre-Processing")
        self.preprocess_label.grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        
        row_idx += 1
        self.preprocess_text = tk.Text(self.advanced_settings_frame, height=10, width=50)
        self.preprocess_text.insert(tk.END, self.settings.editable_settings["Pre-Processing"])
        self.preprocess_text.grid(row=row_idx, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Post-Processing Checkbox
        row_idx += 1

        preprocess_frame = tk.Frame(self.advanced_settings_frame, width=800)
        preprocess_frame.grid(row=row_idx, column=0, padx=10, pady=0, sticky="nw")
        self._create_checkbox(preprocess_frame, "Use Post-Processing", "Use Post-Processing", 0)

        # Post-Processing Label and Text Area
        row_idx += 1
        self.postprocess_label = tk.Label(self.advanced_settings_frame, text="Post-Processing")
        self.postprocess_label.grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")
        
        row_idx += 1
        self.postprocess_text = tk.Text(self.advanced_settings_frame, height=10, width=50)
        self.postprocess_text.insert(tk.END, self.settings.editable_settings["Post-Processing"])
        self.postprocess_text.grid(row=row_idx, column=0, columnspan=2, padx=10, pady=5, sticky="w")


    def create_docker_settings(self):
        """
        Creates the Docker settings UI elements.

        This method creates and places UI elements for Docker settings.
        """
        self.create_editable_settings(self.docker_settings_frame, self.settings.docker_settings)

    def create_editable_settings(self, frame, settings_set, start_row=0):
        """
        Creates editable settings UI elements.

        Args:
            frame (tk.Frame): The frame in which to create the settings.
            settings_set (list): The list of settings to create UI elements for.
            start_row (int): The starting row for placing the settings.
        """
        
        i_frame = ttk.Frame(frame)
        i_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nw")
        self._process_column(i_frame, settings_set, start_row)

    def create_buttons(self):
        """
        Creates the buttons for the settings window.

        This method creates and places buttons for saving settings, resetting to default,
        and closing the settings window.
        """
        tk.Button(self.main_frame, text="Save", command=self.save_settings, width=10).pack(side="right", padx=2, pady=5)
        tk.Button(self.main_frame, text="Default", width=10, command=self.reset_to_default).pack(side="right", padx=2, pady=5)
        tk.Button(self.main_frame, text="Close", width=10, command=self.close_window).pack(side="right", padx=2, pady=5)
        tk.Button(self.main_frame, text="Help", width=10, command=self.create_help_window).pack(side="left", padx=2, pady=5)

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
            self.settings.editable_settings["Architecture"],
            self.architecture_dropdown.get())

        if self.get_selected_model() not in ["Loading models...", "Failed to load models"]:
            self.settings.editable_settings["Model"] = self.get_selected_model()


        self.settings.editable_settings["Pre-Processing"] = self.preprocess_text.get("1.0", "end-1c") # end-1c removes the trailing newline
        self.settings.editable_settings["Post-Processing"] = self.postprocess_text.get("1.0", "end-1c") # end-1c removes the trailing newline

        # save architecture
        self.settings.editable_settings["Architecture"] = self.architecture_dropdown.get()

        self.settings.save_settings(
            self.openai_api_key_entry.get(),
            self.aiscribe_text.get("1.0", "end-1c"), # end-1c removes the trailing newline
            self.aiscribe2_text.get("1.0", "end-1c"), # end-1c removes the trailing newline
            self.settings_window,
            self.ssl_enable_var.get(),
            self.ssl_selfcert_var.get(),
            self.api_dropdown.get(),
            self.cutoff_slider.threshold / 32768,
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
        self.create_editable_settings(self.general_settings_frame, self.settings.general_settings)


    def _create_checkbox(self, frame, label, setting_name, row_idx):
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
        entry = tk.Entry(frame)
        entry.insert(0, str(value))
        entry.grid(row=row_idx, column=1, padx=0, pady=5, sticky="w")
        self.settings.editable_settings_entries[setting_name] = entry

    def close_window(self):
        """
        Cleans up the settings window.

        This method destroys the settings window and clears the settings entries.
        """
        self.settings_window.unbind_all("<MouseWheel>") # Unbind mouse wheel event causing errors
        self.settings_window.unbind_all("<Configure>") # Unbind the configure event causing errors

        self.settings_window.destroy()
