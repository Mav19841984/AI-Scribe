import tkinter as tk
from tkinter import ttk
import pyaudio

class MicrophoneState:
    SELECTED_MICROPHONE_INDEX = None
    SELECTED_MICROPHONE_NAME = None

    @staticmethod
    def load_microphone_from_settings(app_settings):
        """
        Load the microphone settings from the application settings.

        Parameters
        ----------
        app_settings : dict
            Application settings including editable settings.

        Returns
        -------
        str
            The name of the currently selected microphone.
        """
        p = pyaudio.PyAudio()

        if "Current Mic" in app_settings.editable_settings:
            MicrophoneState.SELECTED_MICROPHONE_NAME = app_settings.editable_settings["Current Mic"]
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                if device_info['name'] == MicrophoneState.SELECTED_MICROPHONE_NAME:
                    MicrophoneState.SELECTED_MICROPHONE_INDEX = device_info["index"]
                    break
        else:
            MicrophoneState.SELECTED_MICROPHONE_INDEX = 0
            MicrophoneState.SELECTED_MICROPHONE_NAME = p.get_device_info_by_index(0)['name']

class MicrophoneSelector:
    """
    A class to manage microphone selection using a Tkinter UI.

    Attributes
    ----------
    PYAUDIO : pyaudio.PyAudio
        A PyAudio instance used to interact with audio devices.
    SELECTED_MICROPHONE_INDEX : int
        The index of the currently selected microphone.
    SELECTED_MICROPHONE_NAME : str
        The name of the currently selected microphone.
    """

    def __init__(self, root, row, column, app_settings):
        """
        Initialize the MicrophoneSelector class.

        Parameters
        ----------
        root : tk.Tk
            The root Tkinter instance.
        row : int
            The row position in the Tkinter grid for UI elements.
        column : int
            The column position in the Tkinter grid for UI elements.
        app_settings : dict
            Application settings including editable settings.
        """
        self.root = root
        self.settings = app_settings

        self.pyaudio = pyaudio.PyAudio()

        self.selected_index = None
        self.selected_name = None

        # Create UI elements
        self.label = tk.Label(root, text="Select a Microphone:")
        self.label.grid(row=row, column=0, pady=5, sticky="w")

        self.dropdown = ttk.Combobox(root, state="readonly", width=20)
        self.dropdown.grid(row=row, pady=5, column=1)

        # Populate microphones in the dropdown
        self.update_microphones()

        # Bind selection event
        self.dropdown.bind("<<ComboboxSelected>>", self.on_mic_selected)

    def update_microphones(self):
        """
        Update the microphone dropdown with available devices and manage selection.
        """
        # Initialize microphone mapping and list of names
        self.mic_mapping = {}
        selected_index = -1

        # Populate the microphone mapping with devices having input channels
        for i in range(self.pyaudio.get_device_count()):
            device_info = self.pyaudio.get_device_info_by_index(i)

            if device_info['maxInputChannels'] > 0:
                name = device_info['name']

                if name not in self.mic_mapping:  # Avoid duplicates
                    self.mic_mapping[name] = {
                        "index": device_info['index'],
                        "channels": device_info['maxInputChannels'],
                        "defaultSampleRate": device_info['defaultSampleRate']
                    }

                # Match the current mic setting, if applicable
                if name == self.settings.editable_settings.get("Current Mic") and selected_index == -1:
                    selected_index = device_info['index']

        # Update the dropdown menu with the microphone names
        mic_names = list(self.mic_mapping.keys())
        self.dropdown['values'] = mic_names

        if selected_index != -1:
            # Set the dropdown and selected microphone to the current mic
            self.dropdown.set(self.settings.editable_settings["Current Mic"])
            self.update_selected_microphone(selected_index)
        elif mic_names:
            # Default to the first available microphone if none is selected
            first_mic_name = mic_names[0]
            self.dropdown.set(first_mic_name)
            self.update_selected_microphone(self.mic_mapping[first_mic_name]['index'])
        else:
            # Handle the case where no microphones are available
            self.dropdown.set("No microphones available")
            self.update_selected_microphone(-1)
   
    def on_mic_selected(self, event):
        """
        Handle the event when a microphone is selected from the dropdown.

        Parameters
        ----------
        event : tk.Event
            The event object containing information about the selection.
        """
        selected_name = self.dropdown.get()
        if selected_name in self.mic_mapping:
            selected_index = self.mic_mapping[selected_name]['index']
            self.update_selected_microphone(selected_index)

    def update_selected_microphone(self, selected_index):
        """
        Update the selected microphone index and name.

        Parameters
        ----------
        selected_index : int
            The index of the selected microphone.
        """
        if selected_index >= 0:
            try:
                selected_mic = self.pyaudio.get_device_info_by_index(selected_index)
                MicrophoneState.SELECTED_MICROPHONE_INDEX = selected_mic["index"]
                MicrophoneState.SELECTED_MICROPHONE_NAME = selected_mic["name"]
                self.selected_index = selected_mic["index"]
                self.selected_name = selected_mic["name"]
            except OSError:
                # Handle cases where the selected index is invalid
                MicrophoneState.SELECTED_MICROPHONE_INDEX = None
                MicrophoneState.SELECTED_MICROPHONE_NAME = None
                self.selected_index = None
                self.selected_name = None
        else:
            MicrophoneState.SELECTED_MICROPHONE_INDEX = None
            MicrophoneState.SELECTED_MICROPHONE_NAME = None
            self.selected_index = None
            self.selected_name = None

    def close(self):
        """
        Close the Tkinter root window.
        """
        self.root.destroy()

    def get(self):
        """
        Get the name of the currently selected microphone.

        Returns
        -------
        str
            The name of the currently selected microphone.
        """
        return MicrophoneState.SELECTED_MICROPHONE_NAME
