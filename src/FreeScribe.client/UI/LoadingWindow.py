import tkinter as tk
from tkinter import ttk
from utils.file_utils import get_file_path

class LoadingWindow:
    """
    A class to create and manage an animated processing popup window.
    
    This class creates a popup window with an animated progress bar to indicate
    ongoing processing and a cancel button to abort the operation.
    
    :param parent: The parent window for this popup
    :type parent: tk.Tk or tk.Toplevel or None
    :param title: The title of the popup window
    :type title: str
    :param initial_text: The initial text to display in the popup
    :type initial_text: str
    :param on_cancel: Callback function to execute when cancel is pressed
    :type on_cancel: callable or None
    
    :ivar popup: The main popup window
    :type popup: tk.Toplevel
    :ivar popup_label: The label widget containing the text
    :type popup_label: tk.Label
    :ivar cancelled: Flag indicating if the operation was cancelled
    :type cancelled: bool
    
    Example
    -------
    >>> root = tk.Tk()
    >>> def cancel_callback():
    ...     print("Operation cancelled")
    >>> processing = LoadingWindow(root, on_cancel=cancel_callback)
    >>> # Do some work here
    >>> if not processing.cancelled:
    ...     # Complete the operation
    >>> processing.destroy()
    """

    def __init__(self, parent=None, title="Processing", initial_text="Loading", on_cancel=None):
        """
        Initialize the processing popup window.
        
        :param parent: Parent window for this popup
        :type parent: tk.Tk or tk.Toplevel or None
        :param title: Title of the popup window
        :type title: str
        :param initial_text: Initial text to display
        :type initial_text: str
        :param on_cancel: Callback function to execute when cancel is pressed
        :type on_cancel: callable or None
        """
        try:
            self.title = title
            self.initial_text = initial_text
            self.parent = parent
            self.on_cancel = on_cancel
            self.cancelled = False
            
            self.popup = tk.Toplevel(parent)
            self.popup.title(title)
            # increased width for whisper model type
            self.popup.geometry("280x105")  # Increased height for cancel button
            self.popup.iconbitmap(get_file_path('assets','logo.ico'))

            if parent:
                # Center the popup window on the parent window
                parent.update_idletasks()
                x = parent.winfo_x() + (parent.winfo_width() - self.popup.winfo_reqwidth()) // 2
                y = parent.winfo_y() + (parent.winfo_height() - self.popup.winfo_reqheight()) // 2
                self.popup.geometry(f"+{x}+{y}")
                self.popup.transient(parent)
                
                # Disable the parent window
                parent.wm_attributes('-disabled', True)

            # Use label and progress bar
            self.label = tk.Label(self.popup, text=initial_text)
            self.label.pack(pady=(10,5))
            self.progress = ttk.Progressbar(self.popup, mode='indeterminate')
            self.progress.pack(padx=20, pady=(0,10), fill='x')
            self.progress.start()

            # Add cancel button
            self.cancel_button = ttk.Button(self.popup, text="Cancel", command=self._handle_cancel)
            self.cancel_button.pack(pady=(4,0))

            # Not Resizable
            self.popup.resizable(False, False)
            
            # Disable closing of the popup manually
            self.popup.protocol("WM_DELETE_WINDOW", lambda: None)
        except Exception:
            # Enable the window on exception
            if parent:
                parent.wm_attributes('-disabled', False)
            raise

    def _handle_cancel(self):
        """
        Internal method to handle cancel button press.
        Sets the cancelled flag and calls the user-provided callback if any.
        """
        self.cancelled = True
        if callable(self.on_cancel):
            try:
                self.on_cancel()
            except Exception:
                self.destroy()

        self.destroy()
    
    def destroy(self):
        """
        Clean up and destroy the popup window.
        
        This method performs the following cleanup operations:
        1. Stops the progress bar animation
        2. Re-enables the parent window
        3. Destroys the popup window
        
        Note
        ----
        This method should be called when you want to close the popup window,
        rather than destroying the window directly.
        
        Example
        -------
        >>> popup = LoadingWindow()
        >>> # Do some processing
        >>> popup.destroy()  # Properly clean up and close the window
        """
        if self.popup:
            # Enable the parent window
            if self.parent:
                self.parent.wm_attributes('-disabled', False)
            
            if self.progress.winfo_exists():
                self.progress.stop()

            if self.popup.winfo_exists():
                self.popup.destroy()