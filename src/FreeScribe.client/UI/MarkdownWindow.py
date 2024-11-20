from tkinter import Toplevel, messagebox
import markdown as md
import tkinter as tk
from tkhtmlview import HTMLLabel
from utils.file_utils import get_file_path

"""
A class to create a window displaying rendered Markdown content.
Attributes:
-----------
window : Toplevel
  The top-level window for displaying the Markdown content.
Methods:
--------
__init__(parent, title, file_path, callback=None):
  Initializes the MarkdownWindow with the given parent, title, file path, and optional callback.
_on_close(var, callback):
  Handles the window close event, invoking the callback with the state of the checkbox.
"""
class MarkdownWindow:
    """
    Initializes the MarkdownWindow.
    Parameters:
    -----------
    parent : widget
      The parent widget.
    title : str
      The title of the window.
    file_path : str
      The path to the Markdown file to be rendered.
    callback : function, optional
      A callback function to be called when the window is closed, with the state of the checkbox.
    """
    def __init__(self, parent, title, file_path, callback=None):
        self.window = Toplevel(parent)
        self.window.title(title)
        self.window.transient(parent)
        self.window.grab_set()
        self.window.iconbitmap(get_file_path('assets','logo.ico'))

        try:
          with open(file_path, "r") as file:
              content = md.markdown(file.read(), extensions=["extra", "smarty"])
              
        except FileNotFoundError:
          print(f"File not found: {file_path}")
          self.window.destroy()
          messagebox.showerror("Error", "File not found")
          return

        # Create a frame to hold the HTMLLabel and scrollbar
        frame = tk.Frame(self.window)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Create the HTMLLabel widget
        html_label = HTMLLabel(frame, html=content)
        html_label.pack(side="left", fill="both", expand=True)

        # Create the scrollbar
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=html_label.yview)
        scrollbar.pack(side="right", fill="y")

        # Configure the HTMLLabel to use the scrollbar
        html_label.config(yscrollcommand=scrollbar.set)

        if callback:
            var = tk.BooleanVar()
            tk.Checkbutton(self.window, text="Don't show this message again", 
                          variable=var).pack(side=tk.BOTTOM, pady=10)
            self.window.protocol("WM_DELETE_WINDOW", 
                               lambda: self._on_close(var, callback))

            # Add a close button at the bottom center
            close_button = tk.Button(self.window, text="Close", command=lambda: self._on_close(var, callback))
            close_button.pack(side=tk.BOTTOM)  # Extra padding for separation from the checkbox
        else:
          # Add a close button at the bottom center
          close_button = tk.Button(self.window, text="Close", command= self.window.destroy)
          close_button.pack(side=tk.BOTTOM , pady=5)  # Extra padding for separation from the checkbox

        self.window.geometry("900x900")
        self.window.lift()


    """
    Handles the window close event.
    Parameters:
    -----------
    var : BooleanVar
      The Tkinter BooleanVar associated with the checkbox.
    callback : function
      The callback function to be called with the state of the checkbox.
    """
    def _on_close(self, var, callback):
        callback(var.get())
        self.window.destroy()