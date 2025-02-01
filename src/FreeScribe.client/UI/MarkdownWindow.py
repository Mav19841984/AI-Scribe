from tkinter import Toplevel, messagebox
import markdown as md
import tkinter as tk
from tkhtmlview import HTMLLabel
from utils.file_utils import get_file_path
from utils.utils import get_application_version

class MarkdownWindow:
    """
    A class to display a Markdown file in a pop-up window with optional callback functionality.

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
        try:
            with open(file_path, "r") as file:
                content = md.markdown(file.read(), extensions=["extra", "smarty"])
        except FileNotFoundError:
            print(f"File not found: {file_path}")
            messagebox.showerror("Error", "File not found")
            return

        self.parent = parent
        self.window = Toplevel(parent)
        self.window.title(title)
        self.window.transient(parent)
        self.window.grab_set()
        self.window.iconbitmap(get_file_path('assets', 'logo.ico'))

        # Footer frame to hold checkbox and close button
        footer_frame = tk.Frame(self.window,bg="lightgray")
        footer_frame.pack(side=tk.BOTTOM, fill="x", padx=10, pady=10)

        # Add a version label to the footer
        version = get_application_version()
        version_label = tk.Label(footer_frame, text=f"FreeScribe Client {version}",bg="lightgray",fg="black").pack(side="left", expand=True, padx=2, pady=5)


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

        # Optional checkbox and callback handling
        if callback:
            var = tk.BooleanVar()
            tk.Checkbutton(
                footer_frame, text="Don't show this message again", variable=var
            ).pack(side=tk.BOTTOM, padx=5)

            close_button = tk.Button(
                footer_frame, text="Close", command=lambda: self._on_close(var, callback),font=("Arial", 12),width=6,height=1
            )
        else:
            close_button = tk.Button(footer_frame, text="Close", command=self.window.destroy,font=("Arial", 12),width=6,height=1)

        # Add the close button
        close_button.pack(side=tk.BOTTOM, padx=5, pady=5)

        # Adjust window size based on content with constraints
        self._adjust_window_size(html_label, scrollbar)
        self._display_to_center()
        self.window.lift()
    
    def _display_to_center(self):
        # Get parent window dimensions and position
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()

        width = self.window.winfo_width()
        height = self.window.winfo_height()

        center_x = parent_x + (parent_width - width) // 2
        center_y = parent_y + (parent_height - height) // 2

        # Apply the calculated position to the settings window
        self.window.geometry(f"{width}x{height}+{center_x}+{center_y}")

    def _adjust_window_size(self, html_label, scrollbar):
        """
        Dynamically adjusts the window size based on the content, with constraints.

        Parameters:
        -----------
        html_label : HTMLLabel
            The label containing the rendered Markdown content.
        scrollbar : Scrollbar
            The scrollbar associated with the HTMLLabel.
        """
        self.window.update_idletasks()  # Ensure all widgets are rendered

        content_width = html_label.winfo_reqwidth() + scrollbar.winfo_reqwidth() + 20
        content_height = html_label.winfo_reqheight() + 20  # Exclude footer height from adjustment

        width = min(content_width, 900)  # Maximum width of 900
        height = min(content_height, 750)
        self.window.geometry(f"{width}x{height}")

    def _on_close(self, var, callback):
        """
        Handles the window close event.

        Parameters:
        -----------
        var : BooleanVar
            The Tkinter BooleanVar associated with the checkbox.
        callback : function
            The callback function to be called with the state of the checkbox.
        """
        callback(var.get())
        self.window.destroy()
