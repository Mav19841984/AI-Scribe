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

import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog
import requests
import pyperclip
import wave
import threading
import numpy as np
import base64
import json
import pyaudio
import tkinter.messagebox as messagebox
import datetime
import functools
import os
import whisper # python package is named openai-whisper
from openai import OpenAI
import scrubadub
import re
import speech_recognition as sr # python package is named speechrecognition
import time
import queue
from ContainerManager import ContainerManager
import atexit
import asyncio
from UI.MainWindow import MainWindow
from UI.MainWindowUI import MainWindowUI
from UI.SettingsWindowUI import SettingsWindowUI
from UI.SettingsWindow import SettingsWindow
from UI.Widgets.CustomTextBox import CustomTextBox
from UI.LoadingWindow import LoadingWindow
from Model import Model, ModelManager
from utils.file_utils import get_file_path, get_resource_path

# GUI Setup
root = tk.Tk()
root.title("AI Medical Scribe")

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
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

# Application flags
is_audio_processing_realtime_canceled = False
is_audio_processing_whole_canceled = False

# Constants
DEFAULT_BUTTON_COLOUR = "SystemButtonFace"


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
    thread = threading.Thread(target=toggle_recording)
    thread.start()

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
    

def record_audio():
    global is_paused, frames, audio_queue
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK, input_device_index=1)
    current_chunk = []
    silent_duration = 0
    record_duration = 0
    minimum_silent_duration = int(app_settings.editable_settings["Real Time Silence Length"])
    minimum_audio_duration = int(app_settings.editable_settings["Real Time Audio Length"])
    
    while is_recording:
        if not is_paused:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            # Check for silence
            audio_buffer = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768
            if is_silent(audio_buffer, app_settings.editable_settings["Silence cut-off"]):
                silent_duration += CHUNK / RATE
            else:
                current_chunk.append(data)
                silent_duration = 0
            
            record_duration += CHUNK / RATE
            
            # If the current_chunk has at least 5 seconds of audio and 1 second of silence at the end
            if record_duration >= minimum_audio_duration and silent_duration >= minimum_silent_duration:
                if app_settings.editable_settings["Real Time"] and current_chunk:
                    audio_queue.put(b''.join(current_chunk))
                current_chunk = []
                silent_duration = 0
                record_duration = 0

    # Send any remaining audio chunk when recording stops
    if current_chunk:
        audio_queue.put(b''.join(current_chunk))

    stream.stop_stream()
    stream.close()
    audio_queue.put(None)


def is_silent(data, threshold=0.01):
    """Check if audio chunk is silent"""
    data_array = np.array(data)
    max_value = max(abs(data_array))
    return max_value < threshold

def realtime_text():
    global frames, is_realtimeactive, audio_queue, is_audio_processing_realtime_canceled
    if not is_realtimeactive:
        is_realtimeactive = True
        model = None
        if app_settings.editable_settings["Real Time"]:
            try:
                model_name = app_settings.editable_settings["Whisper Model"].strip()
                model = whisper.load_model(model_name)
            except Exception as e:
                messagebox.showerror("Model Error", f"Error loading model: {e}")
                
        while True:
            #  break if canceled
            if is_audio_processing_realtime_canceled:
                #reset the cancel state
                is_audio_processing_realtime_canceled = False
                break

            audio_data = audio_queue.get()
            if audio_data is None:
                #reset flag here cause we are done
                is_audio_processing_realtime_canceled = False
                break
            if app_settings.editable_settings["Real Time"] == True:
                print("Real Time Audio to Text")
                audio_buffer = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768
                if not is_silent(audio_buffer):
                    if app_settings.editable_settings["Local Whisper"] == True:
                        print("Local Real Time Whisper")
                        result = model.transcribe(audio_buffer, fp16=False)
                        if not is_audio_processing_realtime_canceled:
                            update_gui(result['text'])
                    else:
                        print("Remote Real Time Whisper")
                        if frames:
                            with wave.open(get_resource_path("realtime.wav"), 'wb') as wf:
                                wf.setnchannels(CHANNELS)
                                wf.setsampwidth(p.get_sample_size(FORMAT))
                                wf.setframerate(RATE)
                                wf.writeframes(b''.join(frames))
                            frames = []
                        file_to_send = get_resource_path("realtime.wav")
                        with open(file_to_send, 'rb') as f:
                            files = {'audio': f}

                            headers = {
                                "Authorization": "Bearer "+app_settings.editable_settings["Whisper Server API Key"]
                            }

                            try:
                                verify = not app_settings.editable_settings["S2T Server Self-Signed Certificates"]
                                response = requests.post(app_settings.editable_settings["Whisper Endpoint"], headers=headers,files=files, verify=verify)
                                if response.status_code == 200:
                                    text = response.json()['text']
                                    if not is_audio_processing_realtime_canceled:
                                        update_gui(text)
                                else:
                                    update_gui(f"Error (HTTP Status {response.status_code}): {response.text}")
                            except Exception as e:
                                update_gui(f"Error: {e}")
                            finally:
                                #Task done clean up file
                                if os.path.exists(file_to_send):
                                    f.close()
                                    os.remove(file_to_send)
                audio_queue.task_done()
    else:
        is_realtimeactive = False

def update_gui(text):
    user_input.scrolled_text.insert(tk.END, text + '\n')
    user_input.scrolled_text.see(tk.END)

def save_audio():
    global frames, is_audio_processing_realtime_canceled, is_audio_processing_whole_canceled
    if frames:
        with wave.open(get_resource_path("recording.wav"), 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
        frames = []  # Clear recorded data

        if app_settings.editable_settings["Real Time"] == True and is_audio_processing_realtime_canceled is False:
            send_and_receive()
        elif app_settings.editable_settings["Real Time"] == False and is_audio_processing_whole_canceled is False:
            threaded_send_audio_to_server()
        
        if app_settings.editable_settings["Real Time"] == False and is_audio_processing_whole_canceled:
            is_audio_processing_whole_canceled = False

def toggle_recording():
    global is_recording, recording_thread, DEFAULT_BUTTON_COLOUR, realtime_thread, audio_queue, current_view, is_audio_processing_realtime_canceled, is_audio_processing_whole_canceled

    # Reset the cancel flags going into a fresh recording
    if not is_recording:
        is_audio_processing_realtime_canceled = False
        is_audio_processing_whole_canceled = False

    realtime_thread = threaded_realtime_text()

    if not is_recording:
        user_input.scrolled_text.configure(state='normal')
        user_input.scrolled_text.delete("1.0", tk.END)
        if not app_settings.editable_settings["Real Time"]:
            user_input.scrolled_text.insert(tk.END, "Recording")
        response_display.scrolled_text.configure(state='normal')
        response_display.scrolled_text.delete("1.0", tk.END)
        response_display.scrolled_text.configure(fg='black')
        response_display.scrolled_text.configure(state='disabled')
        is_recording = True

        recording_thread = threading.Thread(target=record_audio)
        recording_thread.start()


        if current_view == "full":
            mic_button.config(bg="red", text="Stop\nRecording")
        elif current_view == "minimal":
            mic_button.config(bg="red", text="⏹️")
        
        start_flashing()
    else:
        is_recording = False
        if recording_thread.is_alive():
            recording_thread.join()  # Ensure the recording thread is terminated

        if app_settings.editable_settings["Real Time"]:

            loading_window = LoadingWindow(root, "Processing Audio", "Processing Audio. Please wait.", on_cancel=cancel_processing)

            timeout_timer = 0
            while audio_queue.empty() is False and timeout_timer < 180:
                # break because cancel was requested
                if is_audio_processing_realtime_canceled:
                    break
                
                timeout_timer += 0.1
                time.sleep(0.1)
            
            loading_window.destroy()

            realtime_thread.join()

        save_audio()

        if current_view == "full":
            mic_button.config(bg=DEFAULT_BUTTON_COLOUR, text="Start\nRecording")
        elif current_view == "minimal":
            mic_button.config(bg=DEFAULT_BUTTON_COLOUR, text="🎤")

        if is_audio_processing_realtime_canceled:
            #empty the queue
            while not audio_queue.empty():
                audio_queue.get()
                audio_queue.task_done()

def cancel_processing():
    """Cancels any ongoing audio processing.
    
    Sets the global flag to stop audio processing operations.
    """
    global is_audio_processing_realtime_canceled, is_audio_processing_whole_canceled

    print("Processing canceled.")

    if app_settings.editable_settings["Real Time"]:
        is_audio_processing_realtime_canceled = True  # Flag to terminate processing
    else:
        is_audio_processing_whole_canceled = True  # Flag to terminate processing

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
    global is_recording, frames, audio_queue
    if is_recording:  # Only reset if currently recording
        cancel_processing()  # Stop any ongoing processing
        threaded_toggle_recording()  # Stop the recording thread

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
        If the `app_settings.editable_settings["Local Whisper"]` flag is not a boolean.
    FileNotFoundError
        If the specified audio file does not exist.
    requests.exceptions.RequestException
        If there is an issue with the HTTP request to the remote server.
    """

    global uploaded_file_path, is_audio_processing_whole_canceled

    loading_window = LoadingWindow(root, "Processing Audio", "Processing Audio. Please wait.", on_cancel=cancel_processing)

    # Check if Local Whisper is enabled in the editable settings
    if app_settings.editable_settings["Local Whisper"] == True:
        # Inform the user that Local Whisper is being used for transcription
        print("Using Local Whisper for transcription.")
        # Configure the user input widget to be editable and clear its content
        user_input.scrolled_text.configure(state='normal')
        user_input.scrolled_text.delete("1.0", tk.END)

        # Display a message indicating that audio to text processing is in progress
        user_input.scrolled_text.insert(tk.END, "Audio to Text Processing...Please Wait")
        try:
            # Load the specified Whisper model
            model_name = app_settings.editable_settings["Whisper Model"].strip()
            model = whisper.load_model(model_name)

            # Determine the file to send for transcription
            file_to_send = uploaded_file_path or get_resource_path('recording.wav')
            delete_file = False if uploaded_file_path else True
            uploaded_file_path = None

            # Transcribe the audio file using the loaded model
            result = model.transcribe(file_to_send)
            transcribed_text = result["text"]

            # done with file clean up
            if os.path.exists(file_to_send) and delete_file is True:
                os.remove(file_to_send)

            #check if canceled, if so do not update the UI
            if not is_audio_processing_whole_canceled:
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
                "Authorization": f"Bearer {app_settings.editable_settings['Whisper Server API Key']}"
            }

            try:
                verify = not app_settings.editable_settings["S2T Server Self-Signed Certificates"]

                # Send the request without verifying the SSL certificate
                response = requests.post(app_settings.editable_settings["Whisper Endpoint"], headers=headers, files=files, verify=verify)

                response.raise_for_status()

                # check if canceled, if so do not update the UI
                if not is_audio_processing_whole_canceled:
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
                if os.path.exists(file_to_send):
                    os.remove(file_to_send)
                loading_window.destroy()

    if is_audio_processing_whole_canceled:
        # reset the state of the flag
        is_audio_processing_whole_canceled = False

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
        timestamp_listbox.delete(0, tk.END)
        timestamp_listbox.config(fg='black')
        IS_FIRST_LOG = False

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    response_history.insert(0, (timestamp, user_message, response_text))

    # Update the timestamp listbox
    timestamp_listbox.delete(0, tk.END)
    for time, _, _ in response_history:
        timestamp_listbox.insert(tk.END, time)

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

        if app_settings.API_STYLE == "OpenAI":
            verify = not app_settings.editable_settings["AI Server Self-Signed Certificates"]
            response = requests.post(app_settings.editable_settings["Model Endpoint"]+"/chat/completions", headers=headers, json=payload, verify=verify)

            response.raise_for_status()
            response_data = response.json()
            response_text = (response_data['choices'][0]['message']['content'])
            return response_text
        elif app_settings.API_STYLE == "KoboldCpp":
            prompt = get_prompt(edited_text)

            verify = not app_settings.editable_settings["AI Server Self-Signed Certificates"]
            response = requests.post(app_settings.editable_settings["Model Endpoint"] + "/api/v1/generate", json=prompt, verify=verify)

            if response.status_code == 200:
                results = response.json()['results']
                response_text = results[0]['text']
                response_text = response_text.replace("  ", " ").strip()
                return response_text

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

    


def send_text_to_chatgpt(edited_text):  
    if app_settings.editable_settings["Use Local LLM"]:
        return send_text_to_localmodel(edited_text)
    else:
        return send_text_to_api(edited_text)

def generate_note(formatted_message):
            try:
                # If note generation is on
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
    popup = tk.Toplevel(root)
    popup.title("Scrub PHI Prior to GPT")
    popup.iconbitmap(get_file_path('assets','logo.ico'))
    text_area = scrolledtext.ScrolledText(popup, height=20, width=80)
    text_area.pack(padx=10, pady=10)

    scrubber = scrubadub.Scrubber()

    scrubbed_message = scrubadub.clean(formatted_message)

    pattern = r'\b\d{10}\b'     # Any 10 digit number, looks like OHIP
    cleaned_message = re.sub(pattern,'{{OHIP}}',scrubbed_message)
    text_area.insert(tk.END, cleaned_message)

    def on_proceed():

        loading_window = LoadingWindow(root, "Generating Note.", "Generating Note. Please wait.")
        global use_aiscribe
        edited_text = text_area.get("1.0", tk.END).strip()
        popup.destroy()
        
        thread = threading.Thread(target=generate_note, args=(edited_text,))
        thread.start()

        def check_thread_status(thread, loading_window):
            if thread.is_alive():
                root.after(500, lambda: check_thread_status(thread, loading_window))
            else:
                loading_window.destroy()

        root.after(500, lambda: check_thread_status(thread, loading_window))

    proceed_button = tk.Button(popup, text="Proceed", command=on_proceed)
    proceed_button.pack(side=tk.RIGHT, padx=10, pady=10)

    # Cancel button
    cancel_button = tk.Button(popup, text="Cancel", command=popup.destroy)
    cancel_button.pack(side=tk.LEFT, padx=10, pady=10)


def upload_file():
    global uploaded_file_path
    file_path = filedialog.askopenfilename(filetypes=(("Audio files", "*.wav *.mp3"),))
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
    timestamp_listbox.grid()
    mic_button.grid(row=1, column=1, pady=5, padx=0,sticky='nsew')
    pause_button.grid(row=1, column=2, pady=5, padx=0,sticky='nsew')
    switch_view_button.grid(row=1, column=7, pady=5, padx=0,sticky='nsew')
    blinking_circle_canvas.grid(row=1, column=8, padx=0,pady=5)

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

    root.attributes('-toolwindow', False)


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
    timestamp_listbox.grid_remove()
    blinking_circle_canvas.grid_remove()

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

    root.attributes('-toolwindow', True)

def copy_text(widget):
    text = widget.get("1.0", tk.END)
    pyperclip.copy(text)

def add_placeholder(event, text_widget, placeholder_text="Text box"):
    if text_widget.get("1.0", "end-1c") == "":
        text_widget.insert("1.0", placeholder_text)
        text_widget.config(fg='grey')

def remove_placeholder(event, text_widget, placeholder_text="Text box"):
    if text_widget.get("1.0", "end-1c") == placeholder_text:
        text_widget.delete("1.0", "end")
        text_widget.config(fg='black')


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

timestamp_listbox = tk.Listbox(root, height=30)
timestamp_listbox.grid(row=0, column=9, columnspan=2, rowspan=3, padx=5, pady=15, sticky='nsew')
timestamp_listbox.bind('<<ListboxSelect>>', show_response)
timestamp_listbox.insert(tk.END, "Temporary Note History")
timestamp_listbox.config(fg='grey')

window.update_aiscribe_texts(None)
# Bind Alt+P to send_and_receive function
root.bind('<Alt-p>', lambda event: pause_button.invoke())

# Bind Alt+R to toggle_recording function
root.bind('<Alt-r>', lambda event: mic_button.invoke())

#set min size
root.minsize(900, 400)



#Wait for the UI root to be intialized then load the model. If using local llm.
if app_settings.editable_settings["Use Local LLM"]:
    root.after(100, lambda:(ModelManager.setup_model(app_settings=app_settings, root=root)))  

root.mainloop()

p.terminate()

def on_exit():
    # Create a pop up that says yes or no with tkinter messagebox to option to close the docker containers

    global window

    main_window = window.logic

    if main_window.container_manager is not None and app_settings.editable_settings["Auto Shutdown Containers on Exit"] is True:
        main_window.container_manager.stop_container(app_settings.editable_settings["LLM Container Name"])
        main_window.container_manager.stop_container(app_settings.editable_settings["LLM Caddy Container Name"])
        main_window.container_manager.stop_container(app_settings.editable_settings["Whisper Container Name"])
        main_window.container_manager.stop_container(app_settings.editable_settings["Whisper Caddy Container Name"])

atexit.register(on_exit)