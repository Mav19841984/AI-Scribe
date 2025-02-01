# Application lock class to prevent multiple instances of an app from running
import tkinter as tk
from tkinter import messagebox
import psutil  # For process management
import sys
import ctypes
import os

class OneInstance:
    """
    Controls application instances to ensure only one is running.
    
    Args:
        app_name: Window title of the application
        app_task_manager_name: Process name as shown in Task Manager
    """
    def __init__(self, app_name, app_task_manager_name):
        self.app_name = app_name
        self.app_task_manager_name = app_task_manager_name
        self.root = None
        
    def get_running_instance_pid(self):
        """
        Finds PIDs of any running instances of the application, excluding the current process.
        
        Returns:
            list: PIDs of running instances, excluding the current process
        """
        current_pid = os.getpid()
        possible_ids = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] == f"{self.app_task_manager_name}" and proc.info['pid'] != current_pid:
                    possible_ids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return possible_ids
        
    def kill_instance(self, pid):
        """
        Terminates specified process instance(s).
        
        Args:
            pid: Process ID (int) or list of PIDs to terminate
        
        Returns:
            bool: True if termination successful, False otherwise
        """
        try:
            if type(pid) == int:
                process = psutil.Process(pid)
                process.terminate()
                return True
            elif type(pid) == list:
                for pid in pid:
                    process = psutil.Process(pid)
                    process.terminate()
                return True
        except psutil.NoSuchProcess:
            return False
            
    def bring_to_front(self, app_name: str):
        """
        Bring the window with the given handle to the front.
        Parameters:
            app_name (str): The name of the application window to bring to the front
        """

        # TODO - Check platform and handle for different platform
        # For now, only Windows is supported
        if sys.platform == 'win32':
            U32DLL = ctypes.WinDLL('user32')
            SW_SHOW = 5
            hwnd = U32DLL.FindWindowW(None, app_name)
            U32DLL.ShowWindow(hwnd, SW_SHOW)
            U32DLL.SetForegroundWindow(hwnd)
            return True
        
        return False

    def _handle_kill(self, dialog, pid):
        """Handles clicking 'Close Existing Instance' button"""
        if self.kill_instance(pid):
            dialog.destroy()
            dialog.return_status = False
        else:
            messagebox.showerror("Error", "Failed to terminate existing instance")
            dialog.destroy()
            dialog.return_status = True
    
    def _handle_cancel(self, dialog):
        """Handles clicking 'Cancel' button"""
        dialog.destroy()
        self.bring_to_front(self.app_name)
        dialog.return_status = True

    def show_instance_dialog(self):
        """
        Shows dialog when another instance is detected.
        Allows user to close existing instance or cancel.
        
        Returns:
            bool: True if existing instance continues, False if terminated
        """
        pid = self.get_running_instance_pid()

        if not pid:
            return False

        dialog = tk.Tk()
        dialog.title("FreeScribe Instance")
        dialog.geometry("300x150")
        dialog.attributes("-topmost", True)
        dialog.lift()
        dialog.focus_force()
        
        dialog.return_status = True

        label = tk.Label(dialog, text="Another instance of FreeScribe is already running.\nWhat would you like to do?")
        label.pack(pady=20)
        
        tk.Button(dialog, text="Close Existing Instance", command=lambda: self._handle_kill(dialog, pid)).pack(padx=5, pady=5)
        tk.Button(dialog, text="Cancel", command=lambda: self._handle_cancel(dialog)).pack(padx=5, pady=2)
        
        dialog.mainloop()
        return dialog.return_status
        
    def run(self):
        """
        Main entry point to check for existing instances.
        
        Returns:
            bool: True if existing instance continues, False if none exists or terminated
        """
        if self.get_running_instance_pid():
            return self.show_instance_dialog()
        else:
            return False
