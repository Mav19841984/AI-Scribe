"""
application_settings.py

This software is released under the AGPL-3.0 license
Copyright (c) 2023-2024 Braedon Hendy

Further updates and packaging added in 2024 through the ClinicianFOCUS initiative, 
a collaboration with Dr. Braedon Hendy and Conestoga College Institute of Applied 
Learning and Technology as part of the CNERG+ applied research project, 
Unburdening Primary Healthcare: An Open-Source AI Clinician Partner Platform". 
Prof. Michael Yingbull (PI), Dr. Braedon Hendy (Partner), 
and Research Students - Software Developer Alex Simko, Pemba Sherpa (F24), and Naitik Patel.

This module contains the ApplicationSettings class, which manages the settings for an
application that involves audio processing and external API interactions, including
WhisperAudio, and OpenAI services.

"""

import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import numpy as np
from utils.file_utils import get_resource_path, get_file_path
from Model import ModelManager
import threading
from UI.Widgets.MicrophoneSelector import MicrophoneState
from utils.ip_utils import is_valid_url
from enum import Enum
import multiprocessing

class SettingsKeys(Enum):
    LOCAL_WHISPER = "Built-in Speech2Text"
    WHISPER_ENDPOINT = "Speech2Text (Whisper) Endpoint"
    WHISPER_SERVER_API_KEY = "Speech2Text (Whisper) API Key"
    WHISPER_ARCHITECTURE = "Speech2Text (Whisper) Architecture"
    WHISPER_CPU_COUNT = "Whisper CPU Thread Count (Experimental)"
    WHISPER_COMPUTE_TYPE = "Whisper Compute Type (Experimental)"
    WHISPER_BEAM_SIZE = "Whisper Beam Size (Experimental)"
    WHISPER_VAD_FILTER = "Use Whisper VAD Filter (Experimental)"
    AUDIO_PROCESSING_TIMEOUT_LENGTH = "Audio Processing Timeout (seconds)"
    SILERO_SPEECH_THRESHOLD = "Silero Speech Threshold"
    USE_TRANSLATE_TASK = "Use Translate Task"
    WHISPER_LANGUAGE_CODE = "Whisper Language Code"
    S2T_SELF_SIGNED_CERT = "S2T Server Self-Signed Certificates"
    LLM_ARCHITECTURE = "Architecture"
    USE_PRESCREEN_AI_INPUT = "Use Pre-Screen AI Input"


class Architectures(Enum):
    CPU = ("CPU", "cpu")
    CUDA = ("CUDA (Nvidia GPU)", "cuda")

    @property
    def label(self):
        return self._value_[0]

    @property
    def architecture_value(self):
        return self._value_[1]



class FeatureToggle:
    DOCKER_SETTINGS_TAB = False
    DOCKER_STATUS_BAR = False

class SettingsWindow():
    """
    Manages application settings related to audio processing and external API services.

    Attributes
    ----------
    OPENAI_API_KEY : str
        The API key for OpenAI integration.
    AISCRIBE : str
        Placeholder for the first AI Scribe settings.
    AISCRIBE2 : str
        Placeholder for the second AI Scribe settings.
    # API_STYLE : str FUTURE FEATURE REVISION
    #     The API style to be used (default is 'OpenAI'). FUTURE FEATURE

    editable_settings : dict
        A dictionary containing user-editable settings such as model parameters, audio 
        settings, and real-time processing configurations.
    
    Methods
    -------
    load_settings_from_file():
        Loads settings from a JSON file and updates the internal state.
    save_settings_to_file():
        Saves the current settings to a JSON file.
    save_settings(openai_api_key, aiscribe_text, aiscribe2_text, 
                  settings_window):
        Saves the current settings, including API keys, IP addresses, and user-defined parameters.
    load_aiscribe_from_file():
        Loads the first AI Scribe text from a file.
    load_aiscribe2_from_file():
        Loads the second AI Scribe text from a file.
    clear_settings_file(settings_window):
        Clears the content of settings files and closes the settings window.
    """

    CPU_INSTALL_FILE = "CPU_INSTALL.txt"
    NVIDIA_INSTALL_FILE = "NVIDIA_INSTALL.txt"
    STATE_FILES_DIR = "install_state"
    DEFAULT_WHISPER_ARCHITECTURE = Architectures.CPU.architecture_value
    DEFAULT_LLM_ARCHITECTURE = Architectures.CPU.architecture_value
    AUTO_DETECT_LANGUAGE_CODES = ["", "auto", "Auto Detect", "None", "None (Auto Detect)"]

    def __init__(self):
        """Initializes the ApplicationSettings with default values."""


        self.OPENAI_API_KEY = "None"
        # self.API_STYLE = "OpenAI" # FUTURE FEATURE REVISION
        self.main_window = None
        self.scribe_template_values = []
        self.scribe_template_mapping = {}

        
        self.general_settings = [
            "Show Welcome Message",
            "Show Scrub PHI"
        ]

        self.whisper_settings = [
            "BlankSpace", # Represents the SettingsKeys.LOCAL_WHISPER.value checkbox that is manually placed
            "Real Time",
            "BlankSpace", # Represents the model dropdown that is manually placed
            "BlankSpace", # Represents the mic dropdown
            SettingsKeys.WHISPER_ENDPOINT.value,
            SettingsKeys.WHISPER_SERVER_API_KEY.value,
            "BlankSpace", # Represents the architecture dropdown that is manually placed
            SettingsKeys.S2T_SELF_SIGNED_CERT.value,
        ]

        self.llm_settings = [
            "Model Endpoint",
            "AI Server Self-Signed Certificates",
        ]

        self.adv_ai_settings = [
            ##############################################################################################
            # Stuff that is commented is related to KobolodCPP API and not used in the current version   #
            # Maybe use it in the future? commented out for now, goes hand in hand with API style        #
            ##############################################################################################

            # "use_story",
            # "use_memory",
            # "use_authors_note",
            # "use_world_info",
            "Use best_of",
            "best_of",
            # "max_context_length",
            # "max_length",
            # "rep_pen",
            # "rep_pen_range",
            # "rep_pen_slope",
            "temperature",
            "tfs",
            # "top_a",
            "top_k",
            "top_p",
            # "typical",
            # "sampler_order",
            # "singleline",
            # "frmttriminc",
            # "frmtrmblln",
        ]

        self.adv_whisper_settings = [
            # "Real Time Audio Length",
            # "BlankSpace", # Represents the whisper cuttoff
            SettingsKeys.WHISPER_BEAM_SIZE.value,
            SettingsKeys.WHISPER_CPU_COUNT.value,
            SettingsKeys.WHISPER_VAD_FILTER.value,
            SettingsKeys.WHISPER_COMPUTE_TYPE.value,
            SettingsKeys.SILERO_SPEECH_THRESHOLD.value,
            SettingsKeys.USE_TRANSLATE_TASK.value,
            SettingsKeys.WHISPER_LANGUAGE_CODE.value,
            SettingsKeys.USE_PRESCREEN_AI_INPUT.value,
        ]


        self.adv_general_settings = [
            # "Enable Scribe Template", # Uncomment if you want to implement the feature right now removed as it doesn't have a real structured implementation
            SettingsKeys.AUDIO_PROCESSING_TIMEOUT_LENGTH.value,
        ]

        self.editable_settings = {
            "Model": "gemma2:2b-instruct-q8_0",
            "Model Endpoint": "https://localhost:3334/v1",
            "Use Local LLM": True,
            SettingsKeys.LLM_ARCHITECTURE.value: SettingsWindow.DEFAULT_LLM_ARCHITECTURE,
            "use_story": False,
            "use_memory": False,
            "use_authors_note": False,
            "use_world_info": False,
            "max_context_length": 5000,
            "max_length": 400,
            "rep_pen": 1.1,
            "rep_pen_range": 5000,
            "rep_pen_slope": 0.7,
            "temperature": 0.1,
            "tfs": 0.97,
            "top_a": 0.8,
            "top_k": 30,
            "top_p": 0.4,
            "typical": 0.19,
            "sampler_order": "[6, 0, 1, 3, 4, 2, 5]",
            "singleline": False,
            "frmttriminc": False,
            "frmtrmblln": False,
            "best_of": 2,
            "Use best_of": False,
            SettingsKeys.LOCAL_WHISPER.value: True,
            SettingsKeys.WHISPER_ENDPOINT.value: "https://localhost:2224/whisperaudio",
            SettingsKeys.WHISPER_SERVER_API_KEY.value: "",
            SettingsKeys.WHISPER_ARCHITECTURE.value: SettingsWindow.DEFAULT_WHISPER_ARCHITECTURE,
            SettingsKeys.WHISPER_BEAM_SIZE.value: 5,
            SettingsKeys.WHISPER_CPU_COUNT.value: multiprocessing.cpu_count(),
            SettingsKeys.WHISPER_VAD_FILTER.value: False,
            SettingsKeys.WHISPER_COMPUTE_TYPE.value: "float16",
            "Whisper Model": "medium",
            "Current Mic": "None",
            "Real Time": True,
            "Real Time Audio Length": 10,
            "Real Time Silence Length": 1,
            "Silence cut-off": 0.035,
            "LLM Container Name": "ollama",
            "LLM Caddy Container Name": "caddy-ollama",
            "LLM Authentication Container Name": "authentication-ollama",
            "Whisper Container Name": "speech-container",
            "Whisper Caddy Container Name": "caddy",
            "Auto Shutdown Containers on Exit": True,
            "Use Docker Status Bar": False,
            "Show Welcome Message": True,
            "Enable Scribe Template": False,
            "Use Pre-Processing": True,
            "Use Post-Processing": False, # Disabled for now causes unexcepted behaviour
            "AI Server Self-Signed Certificates": False,
            SettingsKeys.S2T_SELF_SIGNED_CERT.value: False,
            "Pre-Processing": "Please break down the conversation into a list of facts. Take the conversation and transform it to a easy to read list:\n\n",
            "Post-Processing": "\n\nUsing the provided list of facts, review the SOAP note for accuracy. Verify that all details align with the information provided in the list of facts and ensure consistency throughout. Update or adjust the SOAP note as necessary to reflect the listed facts without offering opinions or subjective commentary. Ensure that the revised note excludes a \"Notes\" section and does not include a header for the SOAP note. Provide the revised note after making any necessary corrections.",
            "Show Scrub PHI": False,
            SettingsKeys.AUDIO_PROCESSING_TIMEOUT_LENGTH.value: 180,
            SettingsKeys.SILERO_SPEECH_THRESHOLD.value: 0.5,
            SettingsKeys.USE_TRANSLATE_TASK.value: False,
            SettingsKeys.WHISPER_LANGUAGE_CODE.value: "None (Auto Detect)",
            SettingsKeys.USE_PRESCREEN_AI_INPUT.value: True,
        }

        self.docker_settings = [
            "LLM Container Name",
            "LLM Caddy Container Name",
            "LLM Authentication Container Name",
            "Whisper Container Name",
            "Whisper Caddy Container Name",
            "Auto Shutdown Containers on Exit",
            "Use Docker Status Bar",
        ]

        self.editable_settings_entries = {}

        self.load_settings_from_file()
        self.AISCRIBE = self.load_aiscribe_from_file() or "AI, please transform the following conversation into a concise SOAP note. Do not assume any medical data, vital signs, or lab values. Base the note strictly on the information provided in the conversation. Ensure that the SOAP note is structured appropriately with Subjective, Objective, Assessment, and Plan sections. Strictly extract facts from the conversation. Here's the conversation:"
        self.AISCRIBE2 = self.load_aiscribe2_from_file() or "Remember, the Subjective section should reflect the patient's perspective and complaints as mentioned in the conversation. The Objective section should only include observable or measurable data from the conversation. The Assessment should be a summary of your understanding and potential diagnoses, considering the conversation's content. The Plan should outline the proposed management, strictly based on the dialogue provided. Do not add any information that did not occur and do not make assumptions. Strictly extract facts from the conversation."

        self.get_dropdown_values_and_mapping()
        self._create_settings_and_aiscribe_if_not_exist()

        MicrophoneState.load_microphone_from_settings(self)

    def get_dropdown_values_and_mapping(self):
        """
        Reads the 'options.txt' file to populate dropdown values and their mappings.

        This function attempts to read a file named 'options.txt' to extract templates
        that consist of three lines: a title, aiscribe, and aiscribe2. These templates
        are then used to populate the dropdown values and their corresponding mappings.
        If the file is not found, default values are used instead.

        :raises FileNotFoundError: If 'options.txt' is not found, a message is printed
                                and default values are used.
        """
        self.scribe_template_values = []
        self.scribe_template_mapping = {}
        try:
            with open('options.txt', 'r') as file:
                content = file.read().strip()
            templates = content.split('\n\n')
            for template in templates:
                lines = template.split('\n')
                if len(lines) == 3:
                    title, aiscribe, aiscribe2 = lines
                    self.scribe_template_values.append(title)
                    self.scribe_template_mapping[title] = (aiscribe, aiscribe2)
        except FileNotFoundError:
            print("options.txt not found, using default values.")
            # Fallback default options if file not found
            self.scribe_template_values = ["Settings Template"]
            self.scribe_template_mapping["Settings Template"] = (self.AISCRIBE, self.AISCRIBE2)

    def load_settings_from_file(self, filename='settings.txt'):
        """
        Loads settings from a JSON file.

        The settings are read from 'settings.txt'. If the file does not exist or cannot be parsed,
        default settings will be used. The method updates the instance attributes with loaded values.

        Returns:
            tuple: A tuple containing the IPs, ports, SSL settings, and API key.
        """
        try:
            with open(get_resource_path(filename), 'r') as file:
                try:
                    settings = json.load(file)
                except json.JSONDecodeError:
                    print("Error loading settings file. Using default settings.")
                    return self.OPENAI_API_KEY

                self.OPENAI_API_KEY = settings.get("openai_api_key", self.OPENAI_API_KEY)
                # self.API_STYLE = settings.get("api_style", self.API_STYLE) # FUTURE FEATURE REVISION
                loaded_editable_settings = settings.get("editable_settings", {})
                for key, value in loaded_editable_settings.items():
                    if key in self.editable_settings:
                        self.editable_settings[key] = value

                if self.editable_settings["Use Docker Status Bar"] and self.main_window is not None:
                    self.main_window.create_docker_status_bar()
                
                if self.editable_settings["Enable Scribe Template"] and self.main_window is not None:
                    self.main_window.create_scribe_template()


                return self.OPENAI_API_KEY
        except FileNotFoundError:
            print("Settings file not found. Using default settings.")
            return self.OPENAI_API_KEY

    def save_settings_to_file(self):
        """
        Saves the current settings to a JSON file.

        The settings are written to 'settings.txt'. This includes all application settings 
        such as IP addresses, ports, SSL settings, and editable settings.

        Returns:
            None
        """
        settings = {
            "openai_api_key": self.OPENAI_API_KEY,
            "editable_settings": self.editable_settings,
            # "api_style": self.API_STYLE # FUTURE FEATURE REVISION
            "app_version": self.get_application_version()
        }
        with open(get_resource_path('settings.txt'), 'w') as file:
            json.dump(settings, file)

    def save_settings(self, openai_api_key, aiscribe_text, aiscribe2_text, settings_window,
                      silence_cutoff):
        """
        Save the current settings, including IP addresses, API keys, and user-defined parameters.

        This method writes the AI Scribe text to separate text files and updates the internal state
        of the Settings instance.

        :param str openai_api_key: The OpenAI API key for authentication.
        :param str aiscribe_text: The text for the first AI Scribe.
        :param str aiscribe2_text: The text for the second AI Scribe.
        :param tk.Toplevel settings_window: The settings window instance to be destroyed after saving.
        """
        self.OPENAI_API_KEY = openai_api_key
        # self.API_STYLE = api_style

        self.editable_settings["Silence cut-off"] = silence_cutoff

        for setting, entry in self.editable_settings_entries.items():     
            value = entry.get()
            if setting in ["max_context_length", "max_length", "rep_pen_range", "top_k"]:
                value = int(value)
            self.editable_settings[setting] = value

        self.save_settings_to_file()

        self.AISCRIBE = aiscribe_text
        self.AISCRIBE2 = aiscribe2_text

        with open(get_resource_path('aiscribe.txt'), 'w') as f:
            f.write(self.AISCRIBE)
        with open(get_resource_path('aiscribe2.txt'), 'w') as f:
            f.write(self.AISCRIBE2)
      
    def load_aiscribe_from_file(self):
        """
        Load the AI Scribe text from a file.

        :returns: The AI Scribe text, or None if the file does not exist or is empty.
        :rtype: str or None
        """
        try:
            with open(get_resource_path('aiscribe.txt'), 'r') as f:
                return f.read()
        except FileNotFoundError:
            return None

    def load_aiscribe2_from_file(self):
        """
        Load the second AI Scribe text from a file.

        :returns: The second AI Scribe text, or None if the file does not exist or is empty.
        :rtype: str or None
        """
        try:
            with open(get_resource_path('aiscribe2.txt'), 'r') as f:
                return f.read()
        except FileNotFoundError:
            return None

  
    def clear_settings_file(self, settings_window):
        """
        Clears the content of settings files and closes the settings window.

        This method attempts to open and clear the contents of three text files:
        `settings.txt`, `aiscribe.txt`, and `aiscribe2.txt`. After clearing the
        files, it displays a message box to notify the user that the settings
        have been reset and closes the `settings_window`. If an error occurs
        during this process, the exception will be caught and printed.

        :param settings_window: The settings window object to be closed after resetting.
        :type settings_window: tkinter.Toplevel or similar
        :raises Exception: If there is an issue with file handling or window destruction.

        Example usage:

        """
        try:
            # Open the files and immediately close them to clear their contents.
            open(get_resource_path('settings.txt'), 'w').close()  
            open(get_resource_path('aiscribe.txt'), 'w').close()
            open(get_resource_path('aiscribe2.txt'), 'w').close()

            # Display a message box informing the user of successful reset.
            messagebox.showinfo("Settings Reset", "Settings have been reset. Please restart.")
            print("Settings file cleared.")

            # Close the settings window.
            settings_window.destroy()
        except Exception as e:
            # Print any exception that occurs during file handling or window destruction.
            print(f"Error clearing settings files: {e}")

    def get_available_models(self,endpoint=None):
        """
        Returns a list of available models for the user to choose from.

        This method returns a list of available models that can be used with the AI Scribe
        service. The list includes the default model, `gpt-4`, as well as any other models
        that may be added in the future.

        Returns:
            list: A list of available models for the user to choose from.
        """
        
        headers = {
            "Authorization": f"Bearer {self.OPENAI_API_KEY}",
            "X-API-Key": self.OPENAI_API_KEY
        }

        endpoint = endpoint or self.editable_settings_entries["Model Endpoint"].get()

        # url validate the endpoint
        if not is_valid_url(endpoint):
            print("Invalid LLM Endpoint")
            return ["Invalid LLM Endpoint", "Custom"]

        try:
            verify = not self.editable_settings["AI Server Self-Signed Certificates"]
            response = requests.get(endpoint + "/models", headers=headers, timeout=1.0, verify=verify)
            response.raise_for_status()  # Raise an error for bad responses
            models = response.json().get("data", [])  # Extract the 'data' field
            
            if not models:
                return ["No models available", "Custom"]

            available_models = [model["id"] for model in models]
            available_models.append("Custom")
            return available_models
        except requests.RequestException as e:
            # messagebox.showerror("Error", f"Failed to fetch models: {e}. Please ensure your OpenAI API key is correct.") 
            print(e)
            return ["Failed to load models", "Custom"]

    def update_models_dropdown(self, dropdown, endpoint=None):
        """
        Updates the models dropdown with the available models.

        This method fetches the available models from the AI Scribe service and updates
        the dropdown widget in the settings window with the new list of models.
        """
        if self.editable_settings_entries["Use Local LLM"].get():
            dropdown["values"] = ["gemma-2-2b-it-Q8_0.gguf"]
            dropdown.set("gemma-2-2b-it-Q8_0.gguf")
        else:
            dropdown["values"] = ["Loading models...", "Custom"]
            dropdown.set("Loading models...")
            models = self.get_available_models(endpoint=endpoint)
            dropdown["values"] = models
            if self.editable_settings["Model"] in models:
                dropdown.set(self.editable_settings["Model"])
            else:
                dropdown.set(models[0])
        
    def set_main_window(self, window):
        """
        Set the main window instance for the settings.

        This method sets the main window instance for the settings class, allowing
        the settings to interact with the main window when necessary.

        Parameters:
            window (MainWindow): The main window instance to set.
        """
        self.main_window = window

    def load_or_unload_model(self, old_model, new_model, old_use_local_llm, new_use_local_llm, old_architecture, new_architecture):
        # Check if old model and new model are different if they are reload and make sure new model is checked.
        if old_model != new_model and new_use_local_llm == 1:
            ModelManager.unload_model()
            ModelManager.start_model_threaded(self, self.main_window.root)

        # Load the model if check box is now selected
        if old_use_local_llm == 0 and new_use_local_llm == 1:
            ModelManager.start_model_threaded(self, self.main_window.root)

        # Check if Local LLM was on and if turned off unload model.abs
        if old_use_local_llm == 1 and new_use_local_llm == 0:
            ModelManager.unload_model()

        if old_architecture != new_architecture and new_use_local_llm == 1:
            ModelManager.unload_model()
            ModelManager.start_model_threaded(self, self.main_window.root)

    def _create_settings_and_aiscribe_if_not_exist(self):
        """
        Create the settings and AI Scribe files if they do not exist.
        """
        if not os.path.exists(get_resource_path('settings.txt')):
            architectures = self.get_available_architectures()
            
            # If CUDA is available, set it as the default architecture to save in settings
            if Architectures.CUDA.label in architectures:
                print("Settings file not found. Creating default settings file with CUDA architecture.")
                self.editable_settings[SettingsKeys.WHISPER_ARCHITECTURE.value] = Architectures.CUDA.label
                self.editable_settings[SettingsKeys.LLM_ARCHITECTURE.value] = Architectures.CUDA.label
            else:
                print("Settings file not found. Creating default settings file.")

            self.save_settings_to_file()
        if not os.path.exists(get_resource_path('aiscribe.txt')):
            print("AIScribe file not found. Creating default AIScribe file.")
            with open(get_resource_path('aiscribe.txt'), 'w') as f:
                f.write(self.AISCRIBE)
        if not os.path.exists(get_resource_path('aiscribe2.txt')):
            print("AIScribe2 file not found. Creating default AIScribe2 file.")
            with open(get_resource_path('aiscribe2.txt'), 'w') as f:
                f.write(self.AISCRIBE2)

    def get_available_architectures(self):
        """
        Returns a list of available architectures for the user to choose from.

        Based on the install state files in _internal folder

        Files must be named CPU_INSTALL or NVIDIA_INSTALL

        Returns:
            list: A list of available architectures for the user to choose from.
        """
        architectures = [Architectures.CPU.label]  # CPU is always available as fallback

        # Check for NVIDIA support
        if os.path.isfile(get_file_path(self.STATE_FILES_DIR, self.NVIDIA_INSTALL_FILE)):
            architectures.append(Architectures.CUDA.label)

        return architectures

    def update_whisper_model(self):
        # save the old whisper model to compare with the new model later
        old_local_whisper = self.editable_settings[SettingsKeys.LOCAL_WHISPER.value]
        old_whisper_architecture = self.editable_settings[SettingsKeys.WHISPER_ARCHITECTURE.value]
        old_model = self.editable_settings["Whisper Model"]
        old_cpu_count = self.editable_settings[SettingsKeys.WHISPER_CPU_COUNT.value]
        old_compute_type = self.editable_settings[SettingsKeys.WHISPER_COMPUTE_TYPE.value]

        # loading the model after the window is closed to prevent the window from freezing
        # if Local Whisper is selected, compare the old model with the new model and reload the model if it has changed
        if self.editable_settings[SettingsKeys.LOCAL_WHISPER.value] and (
                old_local_whisper != self.editable_settings_entries[SettingsKeys.LOCAL_WHISPER.value].get() or 
                old_model != self.editable_settings_entries["Whisper Model"].get() or 
                old_whisper_architecture != self.editable_settings_entries[SettingsKeys.WHISPER_ARCHITECTURE.value].get() or 
                old_cpu_count != self.editable_settings_entries[SettingsKeys.WHISPER_CPU_COUNT.value].get() or
                old_compute_type != self.editable_settings_entries[SettingsKeys.WHISPER_COMPUTE_TYPE.value].get()):
            self.main_window.root.event_generate("<<LoadSttModel>>")