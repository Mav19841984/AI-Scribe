import tkinter as tk
from tkinter import ttk
import pyaudio
import numpy as np
from PIL import Image, ImageTk
from utils.file_utils import get_file_path
from UI.SettingsWindowUI import SettingsWindowUI

class MicrophoneState:
    SELECTED_MICROPHONE_INDEX = None
    SELECTED_MICROPHONE_NAME = None

class MicrophoneTestFrame:
    def __init__(self, parent, p, app_settings, root):
        """
        Initialize the MicrophoneTestFrame.

        Parameters
        ----------
        parent : tk.Widget
            The parent widget where the frame will be placed.
        p : pyaudio.PyAudio
            The PyAudio instance for audio operations.
        app_settings : dict
            Application settings including editable settings.
        """
        self.root = root
        self.parent = parent
        self.p = p
        self.app_settings = app_settings
        self.stream = None  # Persistent audio stream
        self.is_stream_active = False  # Track if the stream is active

        self.setting_window = SettingsWindowUI(self.app_settings, self, self.root)  # Settings window

        # Create a frame for the microphone test
        self.frame = ttk.Frame(self.parent)
        self.frame.grid(row=1, column=0, sticky='nsew')

        # Initialize microphone list and settings
        self.initialize_microphones()

        # Create mic test UI
        self.create_mic_test_ui()

        # Start volume meter updates
        self.update_volume_meter()

        # Initialize the selected microphone
        self.initialize_selected_microphone()

    def initialize_microphones(self):
        """
        Initialize the list of available microphones.
        """
        self.mic_list = []
        self.mic_mapping = {}  # Maps microphone names to their indices

        try:
            default_input_info = self.p.get_default_input_device_info()
            self.default_input_index = default_input_info['index']
        except IOError as e:
            print(f"Failed to initialize microphone ({type(e).__name__}): {e}")
            self.default_input_index = None

        device_count = self.p.get_device_count()
        for i in range(device_count):
            device_info = self.p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                device_name = device_info['name']
                excluded_names = ["Virtual", "Output", "Wave Out", "What U Hear", "Aux", "Port", "Mix"]
                if not any(excluded_name.lower() in device_name.lower() for excluded_name in excluded_names) and device_name not in [name for _, name in self.mic_list]:
                    self.mic_list.append((i, device_name))
                    self.mic_mapping[device_name] = i
        # Load the selected microphone from settings if available
        if self.app_settings and "Current Mic" in self.app_settings.editable_settings:
            selected_name = self.app_settings.editable_settings["Current Mic"]            
            if selected_name in self.mic_mapping:
                MicrophoneState.SELECTED_MICROPHONE_NAME = selected_name
                MicrophoneState.SELECTED_MICROPHONE_INDEX = self.mic_mapping[selected_name]

    def create_mic_test_ui(self):
        """
        Create the UI elements for microphone testing.
        """
        # Frame for dropdown
        dropdown_frame = ttk.Frame(self.frame)
        dropdown_frame.grid(row=0, column=0, sticky='nsew', pady=(0, 5))

        # Create a container frame for center alignment
        center_frame = ttk.Frame(dropdown_frame)
        center_frame.grid(row=0, column=0, sticky='nsew')

        # Configure the center frame to center-align the dropdown
        center_frame.grid_rowconfigure(0, weight=1)
        center_frame.grid_columnconfigure(0, weight=1)

        # Create styles for all elements
        style = ttk.Style()
        style.configure('Mic.TCombobox', padding=(5, 5, 5, 5))
        style.configure('Green.TFrame', background='#2ecc71')
        style.configure('Yellow.TFrame', background='#f1c40f')
        style.configure('Red.TFrame', background='#e74c3c')
        style.configure('Inactive.TFrame', background='#95a5a6')

        # Dropdown for microphone selection
        mic_options = [f"{name}" for _, name in self.mic_list]
        self.mic_dropdown = ttk.Combobox(
            center_frame, 
            values=mic_options, 
            state='readonly', 
            width=40,
            style='Mic.TCombobox'
        )
        self.mic_dropdown.grid(row=0, column=0, pady=(0, 5), padx=(10, 0), sticky='nsew')
        # Set the default selection
        if MicrophoneState.SELECTED_MICROPHONE_NAME:
            self.mic_dropdown.set(MicrophoneState.SELECTED_MICROPHONE_NAME)
        elif self.mic_list:
            self.mic_dropdown.current(0)
        
        # Bind selection change to save immediately
        self.mic_dropdown.bind('<<ComboboxSelected>>', self.on_mic_change)

        # Volume meter container
        meter_frame = ttk.Frame(self.frame)
        meter_frame.grid(row=1, column=0, sticky='nsew', pady=(0, 0))

        # Try to load mic icon
        try:
            mic_icon = Image.open(get_file_path('assets', 'mic_icon.png'))
            mic_icon = mic_icon.resize((24, 24))
            self.mic_photo = ImageTk.PhotoImage(mic_icon)
            mic_icon_label = ttk.Label(meter_frame, image=self.mic_photo)
            mic_icon_label.grid(row=0, column=0, padx=(5, 0), sticky='nsew')
        except Exception as e:
            print(f"Error loading microphone icon: {e}")

        # Create volume meter segments
        self.segments_frame = ttk.Frame(meter_frame)
        self.segments_frame.grid(row=0, column=1, sticky='nsew', pady=(4, 0))

        # Create segments
        self.SEGMENT_COUNT = 20
        self.segments = []
        for i in range(self.SEGMENT_COUNT):
            segment = ttk.Frame(self.segments_frame, width=10, height=20)
            segment.grid(row=0, column=i, padx=1)
            segment.grid_propagate(False)
            self.segments.append(segment)

        # Status label for feedback
        self.status_label = ttk.Label(self.frame, text="Microphone: Ready", foreground="green")
        self.status_label.grid(row=2, column=0, pady=(0, 0), padx=(10, 0), sticky='nsew')

    def initialize_selected_microphone(self):
        """
        Initialize the selected microphone and open the audio stream.
        """
        if MicrophoneState.SELECTED_MICROPHONE_INDEX is not None:
            self.update_selected_microphone(MicrophoneState.SELECTED_MICROPHONE_INDEX)
        elif self.mic_list:
            self.update_selected_microphone(self.mic_list[0][0])

    def on_mic_change(self, event):
        """
        Handle the event when a microphone is selected from the dropdown.
        """
        selected_name = self.mic_dropdown.get()
        if selected_name in self.mic_mapping:
            selected_index = self.mic_mapping[selected_name]
            self.update_selected_microphone(selected_index)
            # save the settings to the file
            self.setting_window.settings.save_settings_to_file()
            # Reopen the stream with the new device
            self.reopen_stream()  

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
                selected_mic = self.p.get_device_info_by_index(selected_index)
                MicrophoneState.SELECTED_MICROPHONE_INDEX = selected_mic["index"]
                MicrophoneState.SELECTED_MICROPHONE_NAME = selected_mic["name"]
                self.status_label.config(text="Microphone: Connected", foreground="green")
                self.app_settings.editable_settings["Current Mic"] = selected_mic["name"]

                # Close existing stream if any
                if self.stream:
                    if self.stream.is_active():
                        self.stream.stop_stream()
                    self.stream.close()
                self.stream = None
                self.is_stream_active = False
                # Open new stream with the selected microphone
                self.stream = self.p.open(
                    format=pyaudio.paInt16,  # Specifies the format of the audio data. paInt16 means 16-bit int PCM.
                    channels=1,             # Specifies the number of channels. 1 for mono, 2 for stereo.
                    rate=16000,             # Specifies the sampling rate in Hz. 16000 Hz is a common rate for speech.
                    input=True,             # Indicates that this stream will be used for input (recording).
                    frames_per_buffer=1024, # Specifies the number of samples (per channel) to read in each buffer.
                    input_device_index=selected_index  # Specifies the index of the input device to use.
                )
                self.is_stream_active = True
            except Exception as e:
                self.status_label.config(text="Error: Microphone not found", foreground="red")
                print(f"Failed to open microphone ({type(e).__name__}): {e}")
        else:
            MicrophoneState.SELECTED_MICROPHONE_INDEX = None
            MicrophoneState.SELECTED_MICROPHONE_NAME = None
            self.status_label.config(text="Error: No microphone selected", foreground="red")

    def reopen_stream(self):
        """
        Reopen the audio stream with the currently selected microphone.
        """
        # Stop and close the existing stream if it is open
        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                print(f"Error closing stream: {e}")
            finally:
                self.stream = None
                self.is_stream_active = False

        # Open a new stream with the selected microphone
        if MicrophoneState.SELECTED_MICROPHONE_INDEX is not None:
            try:
                self.stream = self.p.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=1024,
                    input_device_index=MicrophoneState.SELECTED_MICROPHONE_INDEX
                )
                self.is_stream_active = True
                self.status_label.config(text="Microphone: Connected", foreground="green")
            except Exception as e:
                self.status_label.config(text="Error: Microphone not found", foreground="red")
                print(f"Failed to open microphone ({type(e).__name__}): {e}")

    def update_volume_meter(self):
        """
        Update the volume meter based on the current microphone input.
        """
        if not self.is_stream_active:
            self.frame.after(50, self.update_volume_meter)
            return

        try:
            data = self.stream.read(1024, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(np.square(audio_data.astype(np.float64))))
            
            if np.isnan(rms) or rms <= 0:
                volume = 0
            else:
                scaling_factor = 500
                volume = min(max(int((rms / 32768) * scaling_factor), 0), 100)

            # Update segments
            active_segments = int((volume / 100) * self.SEGMENT_COUNT)
            for i, segment in enumerate(self.segments):
                if i < active_segments:
                    if i < self.SEGMENT_COUNT * 0.6:
                        segment.configure(style='Green.TFrame')
                    elif i < self.SEGMENT_COUNT * 0.8:
                        segment.configure(style='Yellow.TFrame')
                    else:
                        segment.configure(style='Red.TFrame')
                else:
                    segment.configure(style='Inactive.TFrame')

        except OSError as e:
            # Handle both Stream closed and Unanticipated host error
            if e.errno in [-9988, -9999]:
                self.status_label.config(text="Error: Microphone disconnected", foreground="red")
            else:
                # Handle any other stream errors
                self.status_label.config(text="Error: Unknown Error. Check debug log for more.", foreground="red")
            
            print(f"Error in update_volume_meter({type(e).__name__}): {e}")
            self.is_stream_active = False
            self.stream = None
            for segment in self.segments:
                segment.configure(style='Inactive.TFrame')

        self.frame.after(50, self.update_volume_meter)

    def get_selected_microphone_index():
        """
        Get the selected microphone index.
        """
        return MicrophoneState.SELECTED_MICROPHONE_INDEX

    def __del__(self):
        """
        Clean up resources when the object is destroyed.
        """
        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                print(f"Error closing stream in destructor: {e}")