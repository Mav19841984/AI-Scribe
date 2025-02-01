"""
This software is released under the AGPL-3.0 license
Copyright (c) 2023-2024 Braedon Hendy

Further updates and packaging added in 2024 through the ClinicianFOCUS initiative, 
a collaboration with Dr. Braedon Hendy and Conestoga College Institute of Applied 
Learning and Technology as part of the CNERG+ applied research project, 
Unburdening Primary Healthcare: An Open-Source AI Clinician Partner Platform". 
Prof. Michael Yingbull (PI), Dr. Braedon Hendy (Partner), 
and Research Students - Software Developer Alex Simko, Pemba Sherpa (F24), and Naitik Patel.

"""

import ctypes
import io
import logging
import sys
import gc
import os
from pathlib import Path
import wave
import threading
import base64
import json
import datetime
import re
import time
import queue
import atexit
import traceback
import torch
import pyaudio
import requests
import pyperclip
import speech_recognition as sr # python package is named speechrecognition
import scrubadub
import numpy as np
import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog
import tkinter.messagebox as messagebox
from faster_whisper import WhisperModel
from UI.MainWindowUI import MainWindowUI
from UI.SettingsWindow import SettingsWindow, SettingsKeys, Architectures
from UI.Widgets.CustomTextBox import CustomTextBox
from UI.LoadingWindow import LoadingWindow
from Model import  ModelManager
from utils.ip_utils import is_private_ip
from utils.file_utils import get_file_path, get_resource_path
from utils.OneInstance import OneInstance
from utils.utils import get_application_version
from UI.DebugWindow import DualOutput
from UI.Widgets.MicrophoneTestFrame import MicrophoneTestFrame
from utils.utils import window_has_running_instance, bring_to_front, close_mutex
from WhisperModel import TranscribeError
from UI.Widgets.PopupBox import PopupBox

if os.environ.get("FREESCRIBE_DEBUG"):
    LOG_LEVEL = logging.DEBUG
else:
    LOG_LEVEL = logging.INFO

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s'
)

dual = DualOutput()
sys.stdout = dual
sys.stderr = dual

APP_NAME = 'AI Medical Scribe'  # Application name
APP_TASK_MANAGER_NAME = 'freescribe-client.exe'

# check if another instance of the application is already running.
# if false, create a new instance of the application
# if true, exit the current instance
app_manager = OneInstance(APP_NAME, APP_TASK_MANAGER_NAME)

if app_manager.run():
    sys.exit(1)
else:
    root = tk.Tk()
    root.title(APP_NAME)
    
def delete_temp_file(filename):
    """
    Deletes a temporary file if it exists.

    Args:
        filename (str): The name of the file to delete.
    """
    file_path = get_resource_path(filename)
    if os.path.exists(file_path):
        try:
            print(f"Deleting temporary file: {filename}")
            os.remove(file_path)
        except OSError as e:
            print(f"Error deleting temporary file {filename}: {e}")

def on_closing():
    delete_temp_file('recording.wav')
    delete_temp_file('realtime.wav')
    close_mutex()

# Register the close_mutex function to be called on exit
atexit.register(on_closing)

# settings logic
app_settings = SettingsWindow()

#  create our ui elements and settings config
window = MainWindowUI(root, app_settings)

app_settings.set_main_window(window)

if app_settings.editable_settings["Use Docker Status Bar"]:
    window.create_docker_status_bar()

NOTE_CREATION = "Note Creation...Please Wait"

user_message = []
response_history = []
current_view = "full"
username = "user"
botname = "Assistant"
num_lines_to_keep = 20
uploaded_file_path = None
is_recording = False
is_realtimeactive = False
audio_data = []
frames = []
is_paused = False
is_flashing = False
use_aiscribe = True
is_gpt_button_active = False
p = pyaudio.PyAudio()
audio_queue = queue.Queue()
CHUNK = 512
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

# Application flags
is_audio_processing_realtime_canceled = threading.Event()
is_audio_processing_whole_canceled = threading.Event()

# Constants
DEFAULT_BUTTON_COLOUR = "SystemButtonFace"

#Thread tracking variables
REALTIME_TRANSCRIBE_THREAD_ID = None
GENERATION_THREAD_ID = None

# Global instance of whisper model
stt_local_model = None

stt_model_loading_thread_lock = threading.Lock()


def get_prompt(formatted_message):

    sampler_order = app_settings.editable_settings["sampler_order"]
    if isinstance(sampler_order, str):
        sampler_order = json.loads(sampler_order)
    return {
        "prompt": f"{formatted_message}\n",
        "use_story": app_settings.editable_settings["use_story"],
        "use_memory": app_settings.editable_settings["use_memory"],
        "use_authors_note": app_settings.editable_settings["use_authors_note"],
        "use_world_info": app_settings.editable_settings["use_world_info"],
        "max_context_length": int(app_settings.editable_settings["max_context_length"]),
        "max_length": int(app_settings.editable_settings["max_length"]),
        "rep_pen": float(app_settings.editable_settings["rep_pen"]),
        "rep_pen_range": int(app_settings.editable_settings["rep_pen_range"]),
        "rep_pen_slope": float(app_settings.editable_settings["rep_pen_slope"]),
        "temperature": float(app_settings.editable_settings["temperature"]),
        "tfs": float(app_settings.editable_settings["tfs"]),
        "top_a": float(app_settings.editable_settings["top_a"]),
        "top_k": int(app_settings.editable_settings["top_k"]),
        "top_p": float(app_settings.editable_settings["top_p"]),
        "typical": float(app_settings.editable_settings["typical"]),
        "sampler_order": sampler_order,
        "singleline": app_settings.editable_settings["singleline"],
        "frmttriminc": app_settings.editable_settings["frmttriminc"],
        "frmtrmblln": app_settings.editable_settings["frmtrmblln"]
    }

def threaded_toggle_recording():
    logging.debug(f"*** Toggle Recording - Recording status: {is_recording}, STT local model: {stt_local_model}")
    task_done_var = tk.BooleanVar(value=False)
    task_cancel_var = tk.BooleanVar(value=False)
    stt_thread = threading.Thread(target=double_check_stt_model_loading, args=(task_done_var, task_cancel_var))
    stt_thread.start()
    root.wait_variable(task_done_var)
    if task_cancel_var.get():
        logging.debug(f"double checking canceled")
        return

    thread = threading.Thread(target=toggle_recording)
    thread.start()


def double_check_stt_model_loading(task_done_var, task_cancel_var):
    stt_loading_window = None
    try:
        if is_recording:
            return
        if not app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value]:
            return
        if stt_local_model:
            return
        # if using local whisper and model is not loaded, when starting recording
        if stt_model_loading_thread_lock.locked():
            model_name = app_settings.editable_settings["Whisper Model"].strip()
            stt_loading_window = LoadingWindow(root, "Loading Voice to Text model",
                                               f"Loading {model_name} model. Please wait.",
                                               on_cancel=lambda: task_cancel_var.set(True))
            timeout = 300
            time_start = time.monotonic()
            # wait until the other loading thread is done
            while True:
                time.sleep(0.1)
                if task_cancel_var.get():
                    # user cancel
                    logging.debug(f"user canceled after {time.monotonic() - time_start} seconds")
                    return
                if time.monotonic() - time_start > timeout:
                    messagebox.showerror("Error",
                                         f"Timed out while loading local Voice to Text model after {timeout} seconds.")
                    task_cancel_var.set(True)
                    return
                if not stt_model_loading_thread_lock.locked():
                    break
            stt_loading_window.destroy()
            stt_loading_window = None
        # double check
        if stt_local_model is None:
            # mandatory loading, synchronous
            t = load_stt_model()
            t.join()

    except Exception as e:
        logging.exception(str(e))
        messagebox.showerror("Error",
                             f"An error occurred while loading Voice to Text model synchronously {type(e).__name__}: {e}")
    finally:
        if stt_loading_window:
            stt_loading_window.destroy()
        task_done_var.set(True)


def threaded_realtime_text():
    thread = threading.Thread(target=realtime_text)
    thread.start()
    return thread

def threaded_handle_message(formatted_message):
    thread = threading.Thread(target=show_edit_transcription_popup, args=(formatted_message,))
    thread.start()
    return thread

def threaded_send_audio_to_server():
    thread = threading.Thread(target=send_audio_to_server)
    thread.start()
    return thread


def toggle_pause():
    global is_paused
    is_paused = not is_paused

    if is_paused:
        if current_view == "full":
            pause_button.config(text="Resume", bg="red")
        elif current_view == "minimal":
            pause_button.config(text="▶️", bg="red")
    else:
        if current_view == "full":
            pause_button.config(text="Pause", bg=DEFAULT_BUTTON_COLOUR)
        elif current_view == "minimal":
            pause_button.config(text="⏸️", bg=DEFAULT_BUTTON_COLOUR)
    
SILENCE_WARNING_LENGTH = 10 # seconds, warn the user after 10s of no input something might be wrong

def record_audio():
    global is_paused, frames, audio_queue

    try:
        selected_index = MicrophoneTestFrame.get_selected_microphone_index()
        stream = p.open(
            format=FORMAT, 
            channels=1, 
            rate=RATE, 
            input=True,
            frames_per_buffer=CHUNK, 
            input_device_index=int(selected_index))
    except (OSError, IOError) as e:
        messagebox.showerror("Audio Error", f"Please check your microphone settings. Error opening audio stream: {e}")
        return

    try:
        current_chunk = []
        silent_duration = 0
        silent_warning_duration = 0
        record_duration = 0
        minimum_silent_duration = int(app_settings.editable_settings["Real Time Silence Length"])
        minimum_audio_duration = int(app_settings.editable_settings["Real Time Audio Length"])
        
        while is_recording:
            if not is_paused:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                # Check for silence
                audio_buffer = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768
                
                # convert the setting from str to float
                try: 
                    speech_prob_threshold = float(app_settings.editable_settings[SettingsKeys.SILERO_SPEECH_THRESHOLD.value])
                except ValueError:
                    # default it to 0.5 on invalid error
                    speech_prob_threshold = 0.5
                
                if is_silent(audio_buffer, speech_prob_threshold ):
                    silent_duration += CHUNK / RATE
                    silent_warning_duration += CHUNK / RATE
                else:
                    current_chunk.append(data)
                    silent_duration = 0
                    silent_warning_duration = 0
                
                record_duration += CHUNK / RATE

                # Check if we need to warn if silence is long than warn time
                check_silence_warning(silent_warning_duration)

                # 1 second of silence at the end so we dont cut off speech
                if silent_duration >= minimum_silent_duration:
                    if app_settings.editable_settings["Real Time"] and current_chunk:
                        audio_queue.put(b''.join(current_chunk))
                    current_chunk = []
                    silent_duration = 0
                    record_duration = 0

        # Send any remaining audio chunk when recording stops
        if current_chunk:
            audio_queue.put(b''.join(current_chunk))
    except Exception as e:
        # Log the error message
        # TODO System logger
        # For now general catch on any problems
        print(f"An error occurred: {e}")
    finally:
        stream.stop_stream()
        stream.close()
        audio_queue.put(None)

        # If the warning bar is displayed, remove it
        if window.warning_bar is not None:
            window.destroy_warning_bar()

def check_silence_warning(silence_duration):
    """Check if silence warning should be displayed."""

    # Check if we need to warn if silence is long than warn time
    if silence_duration >= SILENCE_WARNING_LENGTH and window.warning_bar is None:
        
        window.create_warning_bar(f"No audio input detected for {SILENCE_WARNING_LENGTH} seconds. Please check your microphone input device in whisper settings and adjust your microphone cutoff level in advanced settings.")
    elif silence_duration <= SILENCE_WARNING_LENGTH and window.warning_bar is not None:
        # If the warning bar is displayed, remove it
        window.destroy_warning_bar()

silero, _silero = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')

def is_silent(data, threshold: float = 0.65):
    """Check if audio chunk contains speech using Silero VAD"""
    # Convert audio data to tensor and ensure correct format
    audio_tensor = torch.FloatTensor(data)
    if audio_tensor.dim() == 2:
        audio_tensor = audio_tensor.mean(dim=1)
    
    # Get speech probability
    speech_prob = silero(audio_tensor, 16000).item()
    return speech_prob < threshold

def realtime_text():
    global is_realtimeactive, audio_queue
    # Incase the user starts a new recording while this one the older thread is finishing.
    # This is a local flag to prevent the processing of the current audio chunk 
    # if the global flag is reset on new recording
    local_cancel_flag = False 
    if not is_realtimeactive:
        is_realtimeactive = True

        while True:
            #  break if canceled
            if is_audio_processing_realtime_canceled.is_set():
                local_cancel_flag = True
                break

            audio_data = audio_queue.get()
            if audio_data is None:
                break
            if app_settings.editable_settings["Real Time"] == True:
                print("Real Time Audio to Text")
                audio_buffer = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768
                if app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value] == True:
                    print("Local Real Time Whisper")
                    if stt_local_model is None:
                        update_gui("Local Whisper model not loaded. Please check your settings.")
                        break
                    try:
                        result = faster_whisper_transcribe(audio_buffer)
                    except Exception as e:
                        update_gui(f"\nError: {e}\n")

                    if not local_cancel_flag and not is_audio_processing_realtime_canceled.is_set():
                        update_gui(result)
                else:
                    print("Remote Real Time Whisper")
                    buffer = io.BytesIO()
                    with wave.open(buffer, 'wb') as wf:
                        wf.setnchannels(CHANNELS)
                        wf.setsampwidth(p.get_sample_size(FORMAT))
                        wf.setframerate(RATE)
                        wf.writeframes(audio_data)

                    buffer.seek(0) # Reset buffer position

                    files = {'audio': buffer}

                    headers = {
                        "Authorization": "Bearer "+app_settings.editable_settings[SettingsKeys.WHISPER_SERVER_API_KEY.value]
                    }

                    body = {
                        "use_translate": app_settings.editable_settings[SettingsKeys.USE_TRANSLATE_TASK.value],
                    }

                    if app_settings.editable_settings[SettingsKeys.WHISPER_LANGUAGE_CODE.value] not in SettingsWindow.AUTO_DETECT_LANGUAGE_CODES:
                        body["language_code"] = app_settings.editable_settings[SettingsKeys.WHISPER_LANGUAGE_CODE.value]

                    try:
                        verify = not app_settings.editable_settings[SettingsKeys.S2T_SELF_SIGNED_CERT.value]

                        print("Sending audio to server")
                        print("File informaton")
                        print("File Size: ", len(buffer.getbuffer()), "bytes")

                        response = requests.post(app_settings.editable_settings[SettingsKeys.WHISPER_ENDPOINT.value], headers=headers,files=files, verify=verify, data=body)
                            
                        print("Response from whisper with status code: ", response.status_code)

                        if response.status_code == 200:
                            text = response.json()['text']
                            if not local_cancel_flag and not is_audio_processing_realtime_canceled.is_set():
                                update_gui(text)
                        else:
                            update_gui(f"Error (HTTP Status {response.status_code}): {response.text}")
                    except Exception as e:
                        update_gui(f"Error: {e}")
                    finally:
                        #close buffer. we dont need it anymore
                        buffer.close()
            audio_queue.task_done()
    else:
        is_realtimeactive = False

def update_gui(text):
    user_input.scrolled_text.insert(tk.END, text + '\n')
    user_input.scrolled_text.see(tk.END)

def save_audio():
    global frames
    if frames:
        with wave.open(get_resource_path("recording.wav"), 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
        frames = []  # Clear recorded data

    if app_settings.editable_settings["Real Time"] == True and is_audio_processing_realtime_canceled.is_set() is False:
        send_and_receive()
    elif app_settings.editable_settings["Real Time"] == False and is_audio_processing_whole_canceled.is_set() is False:
        threaded_send_audio_to_server()

def toggle_recording():
    global is_recording, recording_thread, DEFAULT_BUTTON_COLOUR, audio_queue, current_view, REALTIME_TRANSCRIBE_THREAD_ID, frames

    # Reset the cancel flags going into a fresh recording
    if not is_recording:
        is_audio_processing_realtime_canceled.clear()
        is_audio_processing_whole_canceled.clear()

    if is_paused:
        toggle_pause()

    realtime_thread = threaded_realtime_text()

    if not is_recording:
        disable_recording_ui_elements()
        REALTIME_TRANSCRIBE_THREAD_ID = realtime_thread.ident
        user_input.scrolled_text.configure(state='normal')
        user_input.scrolled_text.delete("1.0", tk.END)
        if not app_settings.editable_settings["Real Time"]:
            user_input.scrolled_text.insert(tk.END, "Recording")
        response_display.scrolled_text.configure(state='normal')
        response_display.scrolled_text.delete("1.0", tk.END)
        response_display.scrolled_text.configure(fg='black')
        response_display.scrolled_text.configure(state='disabled')
        is_recording = True

        # reset frames before new recording so old data is not used
        frames = []
        recording_thread = threading.Thread(target=record_audio)
        recording_thread.start()


        if current_view == "full":
            mic_button.config(bg="red", text="Stop\nRecording")
        elif current_view == "minimal":
            mic_button.config(bg="red", text="⏹️")
        
        start_flashing()
    else:
        enable_recording_ui_elements()
        is_recording = False
        if recording_thread.is_alive():
            recording_thread.join()  # Ensure the recording thread is terminated
        
        if app_settings.editable_settings["Real Time"] and not is_audio_processing_realtime_canceled.is_set():
            def cancel_realtime_processing(thread_id):
                """Cancels any ongoing audio processing.
                
                Sets the global flag to stop audio processing operations.
                """
                global REALTIME_TRANSCRIBE_THREAD_ID

                try:
                    kill_thread(thread_id)
                except Exception as e:
                    # Log the error message
                    # TODO System logger
                    print(f"An error occurred: {e}")
                finally:
                    REALTIME_TRANSCRIBE_THREAD_ID = None

                #empty the queue
                while not audio_queue.empty():
                    audio_queue.get()
                    audio_queue.task_done()

            loading_window = LoadingWindow(root, "Processing Audio", "Processing Audio. Please wait.", on_cancel=lambda: (cancel_processing(), cancel_realtime_processing(REALTIME_TRANSCRIBE_THREAD_ID)))

            try:
                timeout_length = int(app_settings.editable_settings[SettingsKeys.AUDIO_PROCESSING_TIMEOUT_LENGTH.value])
            except ValueError:
                # default to 3minutes
                timeout_length = 180

            timeout_timer = 0.0
            while audio_queue.empty() is False and timeout_timer < timeout_length:
                # break because cancel was requested
                if is_audio_processing_realtime_canceled.is_set():
                    break
                # increment timer
                timeout_timer += 0.1
                # round to 10 decimal places, account for floating point errors
                timeout_timer = round(timeout_timer, 10)

                # check if we should print a message every 5 seconds 
                if timeout_timer % 5 == 0:
                    print(f"Waiting for audio processing to finish. Timeout after {timeout_length} seconds. Timer: {timeout_timer}s")
                
                # Wait for 100ms before checking again, to avoid busy waiting
                time.sleep(0.1)
            
            loading_window.destroy()

            realtime_thread.join()

        save_audio()

        if current_view == "full":
            mic_button.config(bg=DEFAULT_BUTTON_COLOUR, text="Start\nRecording")
        elif current_view == "minimal":
            mic_button.config(bg=DEFAULT_BUTTON_COLOUR, text="🎤")

def disable_recording_ui_elements():
    window.disable_settings_menu()
    user_input.scrolled_text.configure(state='disabled')
    send_button.config(state='disabled')
    toggle_button.config(state='disabled')
    upload_button.config(state='disabled')
    response_display.scrolled_text.configure(state='disabled')
    timestamp_listbox.config(state='disabled')
    clear_button.config(state='disabled')

def enable_recording_ui_elements():
    window.enable_settings_menu()
    user_input.scrolled_text.configure(state='normal')
    send_button.config(state='normal')
    toggle_button.config(state='normal')
    upload_button.config(state='normal')
    timestamp_listbox.config(state='normal')
    clear_button.config(state='normal')
    

def cancel_processing():
    """Cancels any ongoing audio processing.
    
    Sets the global flag to stop audio processing operations.
    """
    print("Processing canceled.")

    if app_settings.editable_settings["Real Time"]:
        is_audio_processing_realtime_canceled.set() # Flag to terminate processing
    else:
        is_audio_processing_whole_canceled.set()  # Flag to terminate processing

def clear_application_press():
    """Resets the application state by clearing text fields and recording status."""
    reset_recording_status()  # Reset recording-related variables
    clear_all_text_fields()  # Clear UI text areas

def reset_recording_status():
    """Resets all recording-related variables and stops any active recording.
    
    Handles cleanup of recording state by:
        - Checking if recording is active
        - Canceling any processing
        - Stopping the recording thread
    """
    global is_recording, frames, audio_queue, REALTIME_TRANSCRIBE_THREAD_ID, GENERATION_THREAD_ID
    if is_recording:  # Only reset if currently recording
        cancel_processing()  # Stop any ongoing processing
        threaded_toggle_recording()  # Stop the recording thread

    # kill the generation thread if active
    if REALTIME_TRANSCRIBE_THREAD_ID:
        # Exit the current realtime thread
        try:
            kill_thread(REALTIME_TRANSCRIBE_THREAD_ID)
        except Exception as e:
            # Log the error message
            # TODO System logger
            print(f"An error occurred: {e}")
        finally:
            REALTIME_TRANSCRIBE_THREAD_ID = None

    if GENERATION_THREAD_ID:
        try:
            kill_thread(GENERATION_THREAD_ID)
        except Exception as e:
            # Log the error message
            # TODO System logger
            print(f"An error occurred: {e}")
        finally:
            GENERATION_THREAD_ID = None

def clear_all_text_fields():
    """Clears and resets all text fields in the application UI.
    
    Performs the following:
        - Clears user input field
        - Resets focus
        - Stops any flashing effects
        - Resets response display with default text
    """
    # Enable and clear user input field
    user_input.scrolled_text.configure(state='normal')
    user_input.scrolled_text.delete("1.0", tk.END)
    
    # Reset focus to main window
    user_input.scrolled_text.focus_set()
    root.focus_set()
    
    stop_flashing()  # Stop any UI flashing effects
    
    # Reset response display with default text
    response_display.scrolled_text.configure(state='normal')
    response_display.scrolled_text.delete("1.0", tk.END)
    response_display.scrolled_text.insert(tk.END, "Medical Note")
    response_display.scrolled_text.config(fg='grey')
    response_display.scrolled_text.configure(state='disabled')

def toggle_aiscribe():
    global use_aiscribe
    use_aiscribe = not use_aiscribe
    toggle_button.config(text="AI Scribe\nON" if use_aiscribe else "AI Scribe\nOFF")

def send_audio_to_server():
    """
    Sends an audio file to either a local or remote Whisper server for transcription.

    Global Variables:
    ----------------
    uploaded_file_path : str
        The path to the uploaded audio file. If `None`, the function defaults to
        'recording.wav'.

    Parameters:
    -----------
    None

    Returns:
    --------
    None

    Raises:
    -------
    ValueError
        If the `app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value]` flag is not a boolean.
    FileNotFoundError
        If the specified audio file does not exist.
    requests.exceptions.RequestException
        If there is an issue with the HTTP request to the remote server.
    """

    global uploaded_file_path
    current_thread_id = threading.current_thread().ident

    def cancel_whole_audio_process(thread_id):
        global GENERATION_THREAD_ID
        
        is_audio_processing_whole_canceled.clear()

        try:
            kill_thread(thread_id)
        except Exception as e:
            # Log the error message
            #TODO Logging the message to system logger
            print(f"An error occurred: {e}")
        finally:
            GENERATION_THREAD_ID = None
            clear_application_press()

    loading_window = LoadingWindow(root, "Processing Audio", "Processing Audio. Please wait.", on_cancel=lambda: (cancel_processing(), cancel_whole_audio_process(current_thread_id)))

    # Check if SettingsKeys.LOCAL_WHISPER is enabled in the editable settings
    if app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value] == True:
        # Inform the user that SettingsKeys.LOCAL_WHISPER.value is being used for transcription
        print(f"Using {SettingsKeys.LOCAL_WHISPER.value} for transcription.")
        # Configure the user input widget to be editable and clear its content
        user_input.scrolled_text.configure(state='normal')
        user_input.scrolled_text.delete("1.0", tk.END)

        # Display a message indicating that audio to text processing is in progress
        user_input.scrolled_text.insert(tk.END, "Audio to Text Processing...Please Wait")
        try:
            # Determine the file to send for transcription
            file_to_send = uploaded_file_path or get_resource_path('recording.wav')
            delete_file = False if uploaded_file_path else True
            uploaded_file_path = None

            # Transcribe the audio file using the loaded model
            try:
                result = faster_whisper_transcribe(file_to_send)
            except Exception as e:
                result = f"An error occurred ({type(e).__name__}): {e}"

            transcribed_text = result

            # done with file clean up
            if os.path.exists(file_to_send) and delete_file is True:
                os.remove(file_to_send)

            #check if canceled, if so do not update the UI
            if not is_audio_processing_whole_canceled.is_set():
                # Update the user input widget with the transcribed text
                user_input.scrolled_text.configure(state='normal')
                user_input.scrolled_text.delete("1.0", tk.END)
                user_input.scrolled_text.insert(tk.END, transcribed_text)

                # Send the transcribed text and receive a response
                send_and_receive()
        except Exception as e:
            # Log the error message
            # TODO: Add system eventlogger
            print(f"An error occurred: {e}")

            #log error to input window
            user_input.scrolled_text.configure(state='normal')
            user_input.scrolled_text.delete("1.0", tk.END)
            user_input.scrolled_text.insert(tk.END, f"An error occurred: {e}")
            user_input.scrolled_text.configure(state='disabled')
        finally:
            loading_window.destroy()
            
    else:
        # Inform the user that Remote Whisper is being used for transcription
        print("Using Remote Whisper for transcription.")

        # Configure the user input widget to be editable and clear its content
        user_input.scrolled_text.configure(state='normal')
        user_input.scrolled_text.delete("1.0", tk.END)

        # Display a message indicating that audio to text processing is in progress
        user_input.scrolled_text.insert(tk.END, "Audio to Text Processing...Please Wait")

        delete_file = False if uploaded_file_path else True

        # Determine the file to send for transcription
        if uploaded_file_path:
            file_to_send = uploaded_file_path
            uploaded_file_path = None
        else:
            file_to_send = get_resource_path('recording.wav')

        # Open the audio file in binary mode
        with open(file_to_send, 'rb') as f:
            files = {'audio': f}

            # Add the Bearer token to the headers for authentication
            headers = {
                "Authorization": f"Bearer {app_settings.editable_settings[SettingsKeys.WHISPER_SERVER_API_KEY.value]}"
            }

            body = {
                "use_translate": app_settings.editable_settings[SettingsKeys.USE_TRANSLATE_TASK.value],
            }

            if app_settings.editable_settings[SettingsKeys.WHISPER_LANGUAGE_CODE.value] not in SettingsWindow.AUTO_DETECT_LANGUAGE_CODES:
                body["language_code"] = app_settings.editable_settings[SettingsKeys.WHISPER_LANGUAGE_CODE.value]

            try:
                verify = not app_settings.editable_settings[SettingsKeys.S2T_SELF_SIGNED_CERT.value]

                print("Sending audio to server")
                print("File informaton")
                print(f"File: {file_to_send}")
                print("File Size: ", os.path.getsize(file_to_send))

                # Send the request without verifying the SSL certificate
                response = requests.post(app_settings.editable_settings[SettingsKeys.WHISPER_ENDPOINT.value], headers=headers, files=files, verify=verify, data=body)

                print("Response from whisper with status code: ", response.status_code)

                response.raise_for_status()

                # check if canceled, if so do not update the UI
                if not is_audio_processing_whole_canceled.is_set():
                    # Update the UI with the transcribed text
                    transcribed_text = response.json()['text']
                    user_input.scrolled_text.configure(state='normal')
                    user_input.scrolled_text.delete("1.0", tk.END)
                    user_input.scrolled_text.insert(tk.END, transcribed_text)

                    # Send the transcribed text and receive a response
                    send_and_receive()
            except Exception as e:
                # log error message
                #TODO: Implment proper logging to system
                print(f"An error occurred: {e}")
                # Display an error message to the user
                user_input.scrolled_text.configure(state='normal')
                user_input.scrolled_text.delete("1.0", tk.END)
                user_input.scrolled_text.insert(tk.END, f"An error occurred: {e}")
                user_input.scrolled_text.configure(state='disabled')
            finally:
                # done with file clean up
                f.close()
                if os.path.exists(file_to_send) and delete_file:
                    os.remove(file_to_send)
                loading_window.destroy()

def kill_thread(thread_id):
    """
    Terminate a thread with a given thread ID.

    This function forcibly terminates a thread by raising a `SystemExit` exception in its context.
    **Use with caution**, as this method is not safe and can lead to unpredictable behavior, 
    including corruption of shared resources or deadlocks.

    :param thread_id: The ID of the thread to terminate.
    :type thread_id: int
    :raises ValueError: If the thread ID is invalid.
    :raises SystemError: If the operation fails due to an unexpected state.
    """
    # Call the C function `PyThreadState_SetAsyncExc` to asynchronously raise
    # an exception in the target thread's context.
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(thread_id),  # The thread ID to target (converted to `long`).
        ctypes.py_object(SystemExit)  # The exception to raise in the thread.
    )

    # Check the result of the function call.
    if res == 0:
        # If 0 is returned, the thread ID is invalid.
        raise ValueError(f"Invalid thread ID: {thread_id}")
    elif res > 1:
        # If more than one thread was affected, something went wrong.
        # Reset the state to prevent corrupting other threads.
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")

def send_and_receive():
    global use_aiscribe, user_message
    user_message = user_input.scrolled_text.get("1.0", tk.END).strip()
    display_text(NOTE_CREATION)
    threaded_handle_message(user_message)

        

def display_text(text):
    response_display.scrolled_text.configure(state='normal')
    response_display.scrolled_text.delete("1.0", tk.END)
    response_display.scrolled_text.insert(tk.END, f"{text}\n")
    response_display.scrolled_text.configure(fg='black')
    response_display.scrolled_text.configure(state='disabled')

IS_FIRST_LOG = True
def update_gui_with_response(response_text):
    global response_history, user_message, IS_FIRST_LOG

    if IS_FIRST_LOG:
        history_frame.delete(0, tk.END)
        history_frame.config(fg='black')
        IS_FIRST_LOG = False

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    response_history.insert(0, (timestamp, user_message, response_text))

    # Update the timestamp listbox
    history_frame.delete(0, tk.END)
    for time, _, _ in response_history:
        history_frame.insert(tk.END, time)

    display_text(response_text)
    pyperclip.copy(response_text)
    stop_flashing()

def show_response(event):
    global IS_FIRST_LOG

    if IS_FIRST_LOG:
        return

    selection = event.widget.curselection()
    if selection:
        index = selection[0]
        transcript_text = response_history[index][1]
        response_text = response_history[index][2]
        user_input.scrolled_text.configure(state='normal')
        user_input.scrolled_text.config(fg='black')
        user_input.scrolled_text.delete("1.0", tk.END)
        user_input.scrolled_text.insert(tk.END, transcript_text)
        response_display.scrolled_text.configure(state='normal')
        response_display.scrolled_text.delete('1.0', tk.END)
        response_display.scrolled_text.insert('1.0', response_text)
        response_display.scrolled_text.config(fg='black')
        response_display.scrolled_text.configure(state='disabled')
        pyperclip.copy(response_text)

def send_text_to_api(edited_text):
    headers = {
        "Authorization": f"Bearer {app_settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "accept": "application/json",
    }

    payload = {}

    try:
        payload = {
            "model": app_settings.editable_settings["Model"].strip(),
            "messages": [
                {"role": "user", "content": edited_text}
            ],
            "temperature": float(app_settings.editable_settings["temperature"]),
            "top_p": float(app_settings.editable_settings["top_p"]),
            "top_k": int(app_settings.editable_settings["top_k"]),
            "tfs": float(app_settings.editable_settings["tfs"]),
        }

        if app_settings.editable_settings["best_of"]:
            payload["best_of"] = int(app_settings.editable_settings["best_of"])
            
    except ValueError as e:
        payload = {
            "model": app_settings.editable_settings["Model"].strip(),
            "messages": [
                {"role": "user", "content": edited_text}
            ],
            "temperature": 0.1,
            "top_p": 0.4,
            "top_k": 30,
            "best_of": 6,
            "tfs": 0.97,
        }

        if app_settings.editable_settings["best_of"]:
            payload["best_of"] = int(app_settings.editable_settings["best_of"])

        print(f"Error parsing settings: {e}. Using default settings.")

    try:

        if app_settings.editable_settings["Model Endpoint"].endswith('/'):
            app_settings.editable_settings["Model Endpoint"] = app_settings.editable_settings["Model Endpoint"][:-1]

        # Open API Style
        verify = not app_settings.editable_settings["AI Server Self-Signed Certificates"]
        response = requests.post(app_settings.editable_settings["Model Endpoint"]+"/chat/completions", headers=headers, json=payload, verify=verify)

        response.raise_for_status()
        response_data = response.json()
        response_text = (response_data['choices'][0]['message']['content'])
        return response_text

        #############################################################
        #                                                           #
        #                   OpenAI API Style                        #
        #           Uncomment to use API Style Selector             #
        #                                                           #
        #############################################################
        
        # if app_settings.API_STYLE == "OpenAI":                    
        # elif app_settings.API_STYLE == "KoboldCpp":
        #     prompt = get_prompt(edited_text)

        #     verify = not app_settings.editable_settings["AI Server Self-Signed Certificates"]
        #     response = requests.post(app_settings.editable_settings["Model Endpoint"] + "/api/v1/generate", json=prompt, verify=verify)

        #     if response.status_code == 200:
        #         results = response.json()['results']
        #         response_text = results[0]['text']
        #         response_text = response_text.replace("  ", " ").strip()
        #         return response_text

    except Exception as e:
        raise e

def send_text_to_localmodel(edited_text):  
    # Send prompt to local model and get response
    if ModelManager.local_model is None:
        ModelManager.setup_model(app_settings=app_settings, root=root)

        timer = 0
        while ModelManager.local_model is None and timer < 30:
            timer += 0.1
            time.sleep(0.1)
        

    return ModelManager.local_model.generate_response(
        edited_text,
        max_tokens=int(app_settings.editable_settings["max_length"]),
        temperature=float(app_settings.editable_settings["temperature"]),
        top_p=float(app_settings.editable_settings["top_p"]),
        repeat_penalty=float(app_settings.editable_settings["rep_pen"]),
    )

    
def screen_input_with_llm(conversation):
    """
    Send a conversation to a large language model (LLM) for prescreening.

    :param conversation: A string containing the conversation to be screened.
    :return: A boolean indicating whether the conversation is valid.
    """
    prompt = (
        "Go over this conversation and ensure it's a conversation with more than 50 words. "
        "Also, if it is a conversation between a doctor and a patient. Please return one word. "
        "Either True or False based. Do not give an explanation and do not format the text. "
        "Here is the conversation:\n"
    )

    # Send the prompt and conversation to the LLM for evaluation
    prescreen = send_text_to_chatgpt(f"{prompt}{conversation}")

    # Check if the response from the LLM is 'true' (case-insensitive)
    is_valid_input = prescreen.strip().lower() == "true"

    # Log the AI's response for debugging purposes
    print("Generating Input. AI Prescreen: ", prescreen)

    return is_valid_input


def display_screening_popup():
    """
    Display a popup window to inform the user of invalid input and offer options.

    :return: A boolean indicating the user's choice:
             - False if the user clicks 'Cancel'.
             - True if the user clicks 'Process Anyway!'.
    """
    # Create and display the popup window
    popup_result = PopupBox(
        parent=root,
        title="Invalid Input",
        message=(
            "Input has been flagged as invalid. Please ensure the input is a conversation with more than "
            "50 words between a doctor and a patient. Unexpected results may occur from the AI."
        ),
        button_text_1="Cancel",
        button_text_2="Process Anyway!"
    )

    # Return based on the button the user clicks
    if popup_result.response == "button_1":
        return False
    elif popup_result.response == "button_2":
        return True


def screen_input(user_message):
    """
    Screen the user's input message based on the application's settings.

    :param user_message: The message to be screened.
    :return: A boolean indicating whether the input is valid and accepted for further processing.
    """
    # Check if AI prescreening is enabled in the application settings
    if app_settings.editable_settings[SettingsKeys.USE_PRESCREEN_AI_INPUT.value]:
        # Perform AI-based prescreening
        screen_result = screen_input_with_llm(user_message)

        # If the input fails prescreening, display a popup for the user
        if not screen_result:
            return display_screening_popup()
        else:
            return True
            
    #else return true always
    return True

def send_text_to_chatgpt(edited_text): 
    if app_settings.editable_settings["Use Local LLM"]:
        return send_text_to_localmodel(edited_text)
    else:
        return send_text_to_api(edited_text)

def generate_note(formatted_message):
            try:
                if use_aiscribe:
                    # If pre-processing is enabled
                    if app_settings.editable_settings["Use Pre-Processing"]:
                        #Generate Facts List
                        list_of_facts = send_text_to_chatgpt(f"{app_settings.editable_settings['Pre-Processing']} {formatted_message}")
                        
                        #Make a note from the facts
                        medical_note = send_text_to_chatgpt(f"{app_settings.AISCRIBE} {list_of_facts} {app_settings.AISCRIBE2}")

                        # If post-processing is enabled check the note over
                        if app_settings.editable_settings["Use Post-Processing"]:
                            post_processed_note = send_text_to_chatgpt(f"{app_settings.editable_settings['Post-Processing']}\nFacts:{list_of_facts}\nNotes:{medical_note}")
                            update_gui_with_response(post_processed_note)
                        else:
                            update_gui_with_response(medical_note)

                    else: # If pre-processing is not enabled thhen just generate the note
                        medical_note = send_text_to_chatgpt(f"{app_settings.AISCRIBE} {formatted_message} {app_settings.AISCRIBE2}")

                        if app_settings.editable_settings["Use Post-Processing"]:
                            post_processed_note = send_text_to_chatgpt(f"{app_settings.editable_settings['Post-Processing']}\nNotes:{medical_note}")
                            update_gui_with_response(post_processed_note)
                        else:
                            update_gui_with_response(medical_note)
                else: # do not generate note just send text directly to AI 
                    ai_response = send_text_to_chatgpt(formatted_message)
                    update_gui_with_response(ai_response)

                return True
            except Exception as e:
                #Logg
                #TODO: Implement proper logging to system event logger
                print(f"An error occurred: {e}")
                display_text(f"An error occurred: {e}")
                return False

def show_edit_transcription_popup(formatted_message):
    scrubber = scrubadub.Scrubber()

    scrubbed_message = scrubadub.clean(formatted_message)

    pattern = r'\b\d{10}\b'     # Any 10 digit number, looks like OHIP
    cleaned_message = re.sub(pattern,'{{OHIP}}',scrubbed_message)

    if (app_settings.editable_settings["Use Local LLM"] or is_private_ip(app_settings.editable_settings["Model Endpoint"])) and not app_settings.editable_settings["Show Scrub PHI"]:
        generate_note_thread(cleaned_message)
        return
    
    popup = tk.Toplevel(root)
    popup.title("Scrub PHI Prior to GPT")
    popup.iconbitmap(get_file_path('assets','logo.ico'))
    text_area = scrolledtext.ScrolledText(popup, height=20, width=80)
    text_area.pack(padx=10, pady=10)
    text_area.insert(tk.END, cleaned_message)

    def on_proceed():
        edited_text = text_area.get("1.0", tk.END).strip()
        popup.destroy()
        generate_note_thread(edited_text)        

    proceed_button = tk.Button(popup, text="Proceed", command=on_proceed)
    proceed_button.pack(side=tk.RIGHT, padx=10, pady=10)

    # Cancel button
    cancel_button = tk.Button(popup, text="Cancel", command=popup.destroy)
    cancel_button.pack(side=tk.LEFT, padx=10, pady=10)



def generate_note_thread(text: str):
    """
    Generate a note from the given text and update the GUI with the response.

    :param text: The text to generate a note from.
    :type text: str
    """
    global GENERATION_THREAD_ID

    GENERATION_THREAD_ID = None

    def cancel_note_generation(thread_id):
        """Cancels any ongoing note generation.
        
        Sets the global flag to stop note generation operations.
        """
        global GENERATION_THREAD_ID

        try:
            if thread_id:
                kill_thread(thread_id)
        except Exception as e:
            # Log the error message
            # TODO implment system logger
            print(f"An error occurred: {e}")
        finally:
            GENERATION_THREAD_ID = None

    loading_window = LoadingWindow(root, "Generating Note.", "Generating Note. Please wait.", on_cancel=lambda: cancel_note_generation(GENERATION_THREAD_ID))
    
    # screen input
    if screen_input(text) is False:
        loading_window.destroy()
        return

    thread = threading.Thread(target=generate_note, args=(text,))
    thread.start()
    GENERATION_THREAD_ID = thread.ident

    def check_thread_status(thread, loading_window):
        if thread.is_alive():
            root.after(500, lambda: check_thread_status(thread, loading_window))
        else:
            loading_window.destroy()

    root.after(500, lambda: check_thread_status(thread, loading_window))

def upload_file():
    global uploaded_file_path
    file_path = filedialog.askopenfilename(filetypes=(("Audio files", "*.wav *.mp3 *.m4a"),))
    if file_path:
        uploaded_file_path = file_path
        threaded_send_audio_to_server()  # Add this line to process the file immediately
    start_flashing()



def start_flashing():
    global is_flashing
    is_flashing = True
    flash_circle()

def stop_flashing():
    global is_flashing
    is_flashing = False
    blinking_circle_canvas.itemconfig(circle, fill='white')  # Reset to default color

def flash_circle():
    if is_flashing:
        current_color = blinking_circle_canvas.itemcget(circle, 'fill')
        new_color = 'blue' if current_color != 'blue' else 'black'
        blinking_circle_canvas.itemconfig(circle, fill=new_color)
        root.after(1000, flash_circle)  # Adjust the flashing speed as needed

def send_and_flash():
    start_flashing()
    send_and_receive()

# Initialize variables to store window geometry for switching between views
last_full_position = None
last_minimal_position = None

def toggle_view():
    """
    Toggles the user interface between a full view and a minimal view.

    Full view includes all UI components, while minimal view limits the interface
    to essential controls, reducing screen space usage. The function also manages
    window properties, button states, and binds/unbinds hover events for transparency.
    """
    
    if current_view == "full":  # Transition to minimal view
        set_minimal_view()
    
    else:  # Transition back to full view
        set_full_view()

def set_full_view():
    """
    Configures the application to display the full view interface.

    Actions performed:
    - Reconfigure button dimensions and text.
    - Show all hidden UI components.
    - Reset window attributes such as size, transparency, and 'always on top' behavior.
    - Create the Docker status bar.
    - Restore the last known full view geometry if available.

    Global Variables:
    - current_view: Tracks the current interface state ('full' or 'minimal').
    - last_minimal_position: Saves the geometry of the window when switching from minimal view.
    """
    global current_view, last_minimal_position

    # Reset button sizes and placements for full view
    mic_button.config(width=11, height=2)
    pause_button.config(width=11, height=2)
    switch_view_button.config(width=11, height=2, text="Minimize View")

    # Show all UI components
    user_input.grid()
    send_button.grid()
    clear_button.grid()
    toggle_button.grid()
    upload_button.grid()
    response_display.grid()
    history_frame.grid()
    mic_button.grid(row=1, column=1, pady=5, padx=0,sticky='nsew')
    pause_button.grid(row=1, column=2, pady=5, padx=0,sticky='nsew')
    switch_view_button.grid(row=1, column=7, pady=5, padx=0,sticky='nsew')
    blinking_circle_canvas.grid(row=1, column=8, padx=0,pady=5)
    footer_frame.grid()

    window.toggle_menu_bar(enable=True)

    # Reconfigure button styles and text
    mic_button.config(bg="red" if is_recording else DEFAULT_BUTTON_COLOUR,
                      text="Stop\nRecording" if is_recording else "Start\nRecording")
    pause_button.config(bg="red" if is_paused else DEFAULT_BUTTON_COLOUR,
                        text="Resume" if is_paused else "Pause")

    # Unbind transparency events and reset window properties
    root.unbind('<Enter>')
    root.unbind('<Leave>')
    root.attributes('-alpha', 1.0)
    root.attributes('-topmost', False)
    root.minsize(900, 400)
    current_view = "full"

    # create docker_status bar if enabled
    if app_settings.editable_settings["Use Docker Status Bar"]:
        window.create_docker_status_bar()

    if app_settings.editable_settings["Enable Scribe Template"]:
        window.destroy_scribe_template()
        window.create_scribe_template()

    # Save minimal view geometry and restore last full view geometry
    last_minimal_position = root.geometry()
    if last_full_position is not None:
        root.geometry(last_full_position)

    # Disable to make the window an app(show taskbar icon)
    # root.attributes('-toolwindow', False)


def set_minimal_view():

    """
    Configures the application to display the minimal view interface.

    Actions performed:
    - Reconfigure button dimensions and text.
    - Hide non-essential UI components.
    - Bind transparency hover events for better focus.
    - Adjust window attributes such as size, transparency, and 'always on top' behavior.
    - Destroy and optionally recreate specific components like the Scribe template.

    Global Variables:
    - current_view: Tracks the current interface state ('full' or 'minimal').
    - last_full_position: Saves the geometry of the window when switching from full view.
    """
    global current_view, last_full_position

    # Remove all non-essential UI components
    user_input.grid_remove()
    send_button.grid_remove()
    clear_button.grid_remove()
    toggle_button.grid_remove()
    upload_button.grid_remove()
    response_display.grid_remove()
    history_frame.grid_remove()
    blinking_circle_canvas.grid_remove()
    footer_frame.grid_remove()
    # Configure minimal view button sizes and placements
    mic_button.config(width=2, height=1)
    pause_button.config(width=2, height=1)
    switch_view_button.config(width=2, height=1)

    mic_button.grid(row=0, column=0, pady=2, padx=2)
    pause_button.grid(row=0, column=1, pady=2, padx=2)
    switch_view_button.grid(row=0, column=2, pady=2, padx=2)

    # Update button text based on recording and pause states
    mic_button.config(text="⏹️" if is_recording else "🎤")
    pause_button.config(text="▶️" if is_paused else "⏸️")
    switch_view_button.config(text="⬆️")  # Minimal view indicator

    blinking_circle_canvas.grid(row=0, column=3, pady=2, padx=2)

    window.toggle_menu_bar(enable=False)

    # Update window properties for minimal view
    root.attributes('-topmost', True)
    root.minsize(125, 50)  # Smaller minimum size for minimal view
    current_view = "minimal"

    # Set hover transparency events
    def on_enter(e):
        if e.widget == root:  # Ensure the event is from the root window
            root.attributes('-alpha', 1.0)

    def on_leave(e):
        if e.widget == root:  # Ensure the event is from the root window
            root.attributes('-alpha', 0.70)

    root.bind('<Enter>', on_enter)
    root.bind('<Leave>', on_leave)

    # Destroy and re-create components as needed
    window.destroy_docker_status_bar()
    if app_settings.editable_settings["Enable Scribe Template"]:
        window.destroy_scribe_template()
        window.create_scribe_template(row=1, column=0, columnspan=3, pady=5)

    # Save full view geometry and restore last minimal view geometry
    last_full_position = root.geometry()
    if last_minimal_position:
        root.geometry(last_minimal_position)

    # Enable to make the window a tool window (no taskbar icon)
    # root.attributes('-toolwindow', True)

def copy_text(widget):
    """
    Copy text content from a tkinter widget to the system clipboard.

    Args:
        widget: A tkinter Text widget containing the text to be copied.
    """
    text = widget.get("1.0", tk.END)
    pyperclip.copy(text)

def add_placeholder(event, text_widget, placeholder_text="Text box"):
    """
    Add placeholder text to a tkinter Text widget when it's empty.

    Args:
        event: The event that triggered this function.
        text_widget: The tkinter Text widget to add placeholder text to.
        placeholder_text (str, optional): The placeholder text to display. Defaults to "Text box".
    """
    if text_widget.get("1.0", "end-1c") == "":
        text_widget.insert("1.0", placeholder_text)
        text_widget.config(fg='grey')

def remove_placeholder(event, text_widget, placeholder_text="Text box"):
    """
    Remove placeholder text from a tkinter Text widget when it gains focus.

    Args:
        event: The event that triggered this function.
        text_widget: The tkinter Text widget to remove placeholder text from.
        placeholder_text (str, optional): The placeholder text to remove. Defaults to "Text box".
    """
    if text_widget.get("1.0", "end-1c") == placeholder_text:
        text_widget.delete("1.0", "end")
        text_widget.config(fg='black')

def load_stt_model(event=None):
    """
    Initialize speech-to-text model loading in a separate thread.

    Args:
        event: Optional event parameter for binding to tkinter events.
    """
    thread = threading.Thread(target=_load_stt_model_thread)
    thread.start()
    return thread

def _load_stt_model_thread():
    """
    Internal function to load the Whisper speech-to-text model.
    
    Creates a loading window and handles the initialization of the WhisperModel
    with configured settings. Updates the global stt_local_model variable.
    
    Raises:
        Exception: Any error that occurs during model loading is caught, logged,
                  and displayed to the user via a message box.
    """
    with stt_model_loading_thread_lock:
        global stt_local_model
        model = app_settings.editable_settings["Whisper Model"].strip()
        stt_loading_window = LoadingWindow(root, "Voice to Text", f"Loading Voice to Text {model} model. Please wait.")
        print(f"Loading STT model: {model}")
        try:
            unload_stt_model()
            device_type = get_selected_whisper_architecture()
            set_cuda_paths()

            compute_type = app_settings.editable_settings[SettingsKeys.WHISPER_COMPUTE_TYPE.value]
            # Change the  compute type automatically if using a gpu one.
            if device_type == Architectures.CPU.architecture_value and compute_type == "float16":
                compute_type = "int8"


            stt_local_model = WhisperModel(
                model,
                device=device_type,
                cpu_threads=int(app_settings.editable_settings[SettingsKeys.WHISPER_CPU_COUNT.value]),
                compute_type=compute_type
            )

            print("STT model loaded successfully.")
        except Exception as e:
            print(f"An error occurred while loading STT {type(e).__name__}: {e}")
            stt_local_model = None
            messagebox.showerror("Error", f"An error occurred while loading Voice to Text {type(e).__name__}: {e}")
        finally:
            stt_loading_window.destroy()
            print("Closing STT loading window.")

def unload_stt_model():
    """
    Unload the speech-to-text model from memory.
    
    Cleans up the global stt_local_model instance and performs garbage collection
    to free up system resources.
    """
    global stt_local_model
    if stt_local_model is not None:
        print("Unloading STT model from device.")
        # no risk of temporary "stt_local_model in globals() is False" with same gc effect
        stt_local_model = None
        gc.collect()
        print("STT model unloaded successfully.")
    else:
        print("STT model is already unloaded.")

def get_selected_whisper_architecture():
    """
    Determine the appropriate device architecture for the Whisper model.
    
    Returns:
        str: The architecture value (CPU or CUDA) based on user settings.
    """
    device_type = Architectures.CPU.architecture_value
    if app_settings.editable_settings[SettingsKeys.WHISPER_ARCHITECTURE.value] == Architectures.CUDA.label:
        device_type = Architectures.CUDA.architecture_value

    return device_type

def faster_whisper_transcribe(audio):
    """
    Transcribe audio using the Faster Whisper model.
    
    Args:
        audio: Audio data to transcribe.
    
    Returns:
        str: Transcribed text or error message if transcription fails.
        
    Raises:
        Exception: Any error during transcription is caught and returned as an error message.
    """
    try:
        if stt_local_model is None:
            load_stt_model()
            raise TranscribeError("Speech2Text model not loaded. Please try again once loaded.")

        # Validate beam_size
        try:
            beam_size = int(app_settings.editable_settings[SettingsKeys.WHISPER_BEAM_SIZE.value])
            if beam_size <= 0:
                raise ValueError(f"{SettingsKeys.WHISPER_BEAM_SIZE.value} must be greater than 0 in advanced settings")
        except (ValueError, TypeError) as e:
            return f"Invalid {SettingsKeys.WHISPER_BEAM_SIZE.value} parameter. Please go into the advanced settings and ensure you have a integer greater than 0: {str(e)}"

        # Validate vad_filter
        vad_filter = bool(app_settings.editable_settings[SettingsKeys.WHISPER_VAD_FILTER.value])

        segments, info = stt_local_model.transcribe(
            audio,
            beam_size=beam_size,
            vad_filter=vad_filter,
        )

        return "".join(f"{segment.text} " for segment in segments)
    except Exception as e:
        error_message = f"Transcription failed: {str(e)}"
        print(f"Error during transcription: {str(e)}")
        raise TranscribeError(error_message) from e

def set_cuda_paths():
    """
    Configure CUDA-related environment variables and paths.
    
    Sets up the necessary environment variables for CUDA execution when CUDA
    architecture is selected. Updates CUDA_PATH, CUDA_PATH_V12_4, and PATH
    environment variables with the appropriate NVIDIA driver paths.
    """
    if (get_selected_whisper_architecture() != Architectures.CUDA.architecture_value) or (app_settings.editable_settings[SettingsKeys.LLM_ARCHITECTURE.value] != Architectures.CUDA.label):
        return

    nvidia_base_path = Path(get_file_path('nvidia-drivers'))
    
    cuda_path = nvidia_base_path / 'cuda_runtime' / 'bin'
    cublas_path = nvidia_base_path / 'cublas' / 'bin'
    cudnn_path = nvidia_base_path / 'cudnn' / 'bin'
    
    paths_to_add = [str(cuda_path), str(cublas_path), str(cudnn_path)]
    env_vars = ['CUDA_PATH', 'CUDA_PATH_V12_4', 'PATH']

    for env_var in env_vars:
        current_value = os.environ.get(env_var, '')
        new_value = os.pathsep.join(paths_to_add + ([current_value] if current_value else []))
        os.environ[env_var] = new_value

# Configure grid weights for scalability
root.grid_columnconfigure(0, weight=1, minsize= 10)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)
root.grid_columnconfigure(3, weight=1)
root.grid_columnconfigure(4, weight=1)
root.grid_columnconfigure(5, weight=1)
root.grid_columnconfigure(6, weight=1)
root.grid_columnconfigure(7, weight=1)
root.grid_columnconfigure(8, weight=1)
root.grid_columnconfigure(9, weight=1)
root.grid_columnconfigure(10, weight=1)
root.grid_columnconfigure(11, weight=1, minsize=10)
root.grid_rowconfigure(0, weight=1)
root.grid_rowconfigure(1, weight=0)
root.grid_rowconfigure(2, weight=1)
root.grid_rowconfigure(3, weight=0)
root.grid_rowconfigure(4, weight=0)


window.load_main_window()

user_input = CustomTextBox(root, height=12)
user_input.grid(row=0, column=1, columnspan=8, padx=5, pady=15, sticky='nsew')


# Insert placeholder text
user_input.scrolled_text.insert("1.0", "Transcript of Conversation")
user_input.scrolled_text.config(fg='grey')

# Bind events to remove or add the placeholder with arguments
user_input.scrolled_text.bind("<FocusIn>", lambda event: remove_placeholder(event, user_input.scrolled_text, "Transcript of Conversation"))
user_input.scrolled_text.bind("<FocusOut>", lambda event: add_placeholder(event, user_input.scrolled_text, "Transcript of Conversation"))

mic_button = tk.Button(root, text="Start\nRecording", command=lambda: (threaded_toggle_recording()), height=2, width=11)
mic_button.grid(row=1, column=1, pady=5, sticky='nsew')

send_button = tk.Button(root, text="Generate Note", command=send_and_flash, height=2, width=11)
send_button.grid(row=1, column=3, pady=5, sticky='nsew')

pause_button = tk.Button(root, text="Pause", command=toggle_pause, height=2, width=11)
pause_button.grid(row=1, column=2, pady=5, sticky='nsew')

clear_button = tk.Button(root, text="Clear", command=clear_application_press, height=2, width=11)
clear_button.grid(row=1, column=4, pady=5, sticky='nsew')

toggle_button = tk.Button(root, text="AI Scribe\nON", command=toggle_aiscribe, height=2, width=11)
toggle_button.grid(row=1, column=5, pady=5, sticky='nsew')

upload_button = tk.Button(root, text="Upload\nRecording", command=upload_file, height=2, width=11)
upload_button.grid(row=1, column=6, pady=5, sticky='nsew')

switch_view_button = tk.Button(root, text="Minimize View", command=toggle_view, height=2, width=11)
switch_view_button.grid(row=1, column=7, pady=5, sticky='nsew')

blinking_circle_canvas = tk.Canvas(root, width=20, height=20)
blinking_circle_canvas.grid(row=1, column=8, pady=5)
circle = blinking_circle_canvas.create_oval(5, 5, 15, 15, fill='white')

response_display = CustomTextBox(root, height=13, state="disabled")
response_display.grid(row=2, column=1, columnspan=8, padx=5, pady=15, sticky='nsew')

# Insert placeholder text
response_display.scrolled_text.configure(state='normal')
response_display.scrolled_text.insert("1.0", "Medical Note")
response_display.scrolled_text.config(fg='grey')
response_display.scrolled_text.configure(state='disabled')

if app_settings.editable_settings["Enable Scribe Template"]:
    window.create_scribe_template()

# Create a frame to hold both timestamp listbox and mic test
history_frame = ttk.Frame(root)
history_frame.grid(row=0, column=9, columnspan=2, rowspan=5, padx=5, pady=10, sticky='nsew')

# Configure the frame's grid
history_frame.grid_columnconfigure(0, weight=1)
history_frame.grid_rowconfigure(0, weight=4)  # Timestamp takes more space
history_frame.grid_rowconfigure(1, weight=1)  # Mic test takes less space

# Add the timestamp listbox
timestamp_listbox = tk.Listbox(history_frame, height=30)
timestamp_listbox.grid(row=0, column=0, rowspan=3,sticky='nsew')
timestamp_listbox.bind('<<ListboxSelect>>', show_response)
timestamp_listbox.insert(tk.END, "Temporary Note History")
timestamp_listbox.config(fg='grey')

# Add microphone test frame
mic_test = MicrophoneTestFrame(parent=history_frame, p=p, app_settings=app_settings, root=root)
mic_test.frame.grid(row=4, column=0, pady=10, sticky='nsew')  # Use grid to place the frame

# Add a footer frame at the bottom of the window
footer_frame = tk.Frame(root, bg="lightgray", height=30)
footer_frame.grid(row=100, column=0, columnspan=100, sticky="ew")  # Use grid instead of pack

# Add "Version 2" label in the center of the footer
version = get_application_version()
version_label = tk.Label(footer_frame, text=f"FreeScribe Client {version}",bg="lightgray",fg="black").pack(side="left", expand=True, padx=2, pady=5)

window.update_aiscribe_texts(None)
# Bind Alt+P to send_and_receive function
root.bind('<Alt-p>', lambda event: pause_button.invoke())

# Bind Alt+R to toggle_recording function
root.bind('<Alt-r>', lambda event: mic_button.invoke())

#set min size
root.minsize(900, 400)

if (app_settings.editable_settings['Show Welcome Message']):
    window.show_welcome_message()

#Wait for the UI root to be intialized then load the model. If using local llm.
if app_settings.editable_settings["Use Local LLM"]:
    root.after(100, lambda:(ModelManager.setup_model(app_settings=app_settings, root=root)))  

if app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value]:
    # Inform the user that Local Whisper is being used for transcription
    print("Using Local Whisper for transcription.")
    root.after(100, lambda: (load_stt_model()))

root.bind("<<LoadSttModel>>", load_stt_model)

root.mainloop()

p.terminate()
