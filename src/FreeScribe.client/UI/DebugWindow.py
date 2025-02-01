"""
Input/output utilities for debugging and logging with tkinter GUI support.

This module provides classes for dual output handling (console and buffer) 
and a debug window interface built with tkinter.
"""

import tkinter as tk
import io
import sys
from datetime import datetime
from collections import deque
from utils.utils import bring_to_front

class DualOutput:
    buffer = None
    MAX_BUFFER_SIZE = 2500  # Maximum number of lines in the buffer

    def __init__(self):
        """
        Initialize the dual output handler.
        
        Creates a deque buffer with a max length and stores references to original stdout/stderr streams.
        """
        DualOutput.buffer = deque(maxlen=DualOutput.MAX_BUFFER_SIZE)  # Buffer with a fixed size
        self.original_stdout = sys.stdout  # Save the original stdout
        self.original_stderr = sys.stderr  # Save the original stderr

    def write(self, message):
        """
        Write a message to both the buffer and original stdout.
        
        :param message: The message to be written
        :type message: str
        """
        if message.strip():
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if "\n" in message:  # Handle multi-line messages
                for line in message.splitlines():
                    if line.strip():
                        formatted_message = f"{timestamp} - {line}\n"
                        DualOutput.buffer.append(formatted_message)
            else:
                formatted_message = f"{timestamp} - {message}"
                DualOutput.buffer.append(formatted_message)
        else:
            DualOutput.buffer.append("\n")
        if self.original_stdout is not None:
            self.original_stdout.write(message)

    def flush(self):
        """
        Flush the original stdout to ensure output is written immediately.
        """
        if self.original_stdout is not None:
            self.original_stdout.flush()

    @staticmethod
    def get_buffer_content():
        """
        Retrieve all content stored in the buffer.
        
        :return: The complete buffer contents as a single string.
        :rtype: str
        """
        return ''.join(DualOutput.buffer)

class DebugPrintWindow:
    """
    Creates and manages a tkinter window for displaying debug output.
    
    Provides a GUI interface for viewing buffered output with scroll functionality
    and manual refresh capability.
    """

    def __init__(self, parent):
        """
        Initialize the debug window interface.
        
        :param parent: Parent tkinter window
        :type parent: tk.Tk or tk.Toplevel
        """
        self.parent = parent
        if self.parent.debug_window_open:
            bring_to_front("Debug Output")
            return
        self.parent.debug_window_open = True
        self.window = tk.Toplevel(parent.root)
        self.window.title("Debug Output")
        self.window.geometry("650x450")

        # Create a Text widget for displaying captured output
        self.text_widget = tk.Text(self.window, wrap="none", width=80, height=20)
        self.text_widget.pack(padx=10, pady=(10, 0), fill=tk.BOTH, expand=True)

        # Create vertical scrollbar
        scrollbar = tk.Scrollbar(self.text_widget)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Create horizontal scrollbar
        hscrollbar = tk.Scrollbar(self.text_widget, orient=tk.HORIZONTAL)
        hscrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Configure scrollbar-text widget interactions
        scrollbar.config(command=self.text_widget.yview)
        self.text_widget.config(yscrollcommand=scrollbar.set)
        hscrollbar.config(command=self.text_widget.xview)
        self.text_widget.config(xscrollcommand=hscrollbar.set)

        # Add refresh button
        refresh_button = tk.Button(self.window, text="Refresh", command=self.refresh_output)
        refresh_button.pack(side=tk.RIGHT,pady=10, padx=10)

        # Add copy to clipboard button
        copy_button = tk.Button(self.window, text="Copy to Clipboard", command=self._copy_to_clipboard)
        copy_button.pack(side=tk.LEFT, pady=10, padx=10)

        # custom function to close the window
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)

        self.refresh_output()

    def _copy_to_clipboard(self):
        # Copy the content of the Text widget to the clipboard
        content = self.text_widget.get("1.0", tk.END).strip()
        self.window.clipboard_clear()
        self.window.clipboard_append(content)
        self.window.update_idletasks()


    def refresh_output(self):
        """
        Update the debug window with latest buffer contents.
        
        Preserves scroll position when updating content and only updates
        if there are changes in the buffer.
        """
        content = DualOutput.get_buffer_content()
        current_content = self.text_widget.get("1.0", tk.END).strip()

        if content != current_content:
            top_line_index = self.text_widget.index("@0,0")
            self.text_widget.delete("1.0", tk.END)
            self.text_widget.insert(tk.END, content)
            self.text_widget.see(top_line_index)

    def close_window(self):
        self.parent.debug_window_open = False
        self.window.destroy()