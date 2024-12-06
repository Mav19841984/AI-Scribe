"""

MainWindow.py

Main window module for the FreeScribe client application.

This module contains the MainWindow class which is responsible for managing the main window of the application.
It includes methods to start and stop Docker containers for LLM and Whisper services.

This software is released under the AGPL-3.0 license
Copyright (c) 2023-2024 Braedon Hendy

Further updates and packaging added in 2024 through the ClinicianFOCUS initiative, 
a collaboration with Dr. Braedon Hendy and Conestoga College Institute of Applied 
Learning and Technology as part of the CNERG+ applied research project, 
Unburdening Primary Healthcare: An Open-Source AI Clinician Partner Platform". 
Prof. Michael Yingbull (PI), Dr. Braedon Hendy (Partner), 
and Research Students - Software Developer Alex Simko, Pemba Sherpa (F24), and Naitik Patel.

"""

from ContainerManager import ContainerManager, ContainerState
import tkinter as tk

class MainWindow:
    """
    Main window class for the FreeScribe client application.

    This class initializes the main window and provides methods to manage Docker containers for LLM and Whisper services.
    """

    def __init__(self, settings):
        """
        Initialize the main window of the application.
        """
        self.container_manager = ContainerManager()
        self.settings = settings

    def start_LLM_container(self, widget_name, app_settings):
        """
        Start the LLM container.

        :param widget_name: The name of the widget to update with the container status.
        :type widget_name: str
        :param app_settings: The application settings containing container names.
        :type app_settings: ApplicationSettings
        """
        try:
            self.container_manager.set_status_icon_color(widget_name, self.container_manager.start_container(app_settings.editable_settings["LLM Container Name"]))
            self.container_manager.set_status_icon_color(widget_name, self.container_manager.start_container(app_settings.editable_settings["LLM Caddy Container Name"]))
            self.container_manager.set_status_icon_color(widget_name, self.container_manager.start_container(app_settings.editable_settings["LLM Authentication Container Name"]))
        except Exception as e:
            tk.messagebox.showerror("Error", f"An error occurred while starting the LLM container: {e}")

    def stop_LLM_container(self, widget_name, app_settings):
        """
        Stop the LLM container.

        :param widget_name: The name of the widget to update with the container status.
        :type widget_name: str
        :param app_settings: The application settings containing container names.
        :type app_settings: ApplicationSettings
        """
        try:
            self.container_manager.set_status_icon_color(widget_name, self.container_manager.stop_container(app_settings.editable_settings["LLM Container Name"]))
            self.container_manager.set_status_icon_color(widget_name, self.container_manager.stop_container(app_settings.editable_settings["LLM Caddy Container Name"]))
            self.container_manager.set_status_icon_color(widget_name, self.container_manager.stop_container(app_settings.editable_settings["LLM Authentication Container Name"]))
        except Exception as e:
            tk.messagebox.showerror("Error", f"An error occurred while stopping the LLM container: {e}")

    def start_whisper_container(self, widget_name, app_settings):
        """
        Start the Whisper container.

        :param widget_name: The name of the widget to update with the container status.
        :type widget_name: str
        :param app_settings: The application settings containing container names.
        :type app_settings: ApplicationSettings
        """
        try:
            self.container_manager.set_status_icon_color(widget_name, self.container_manager.start_container(app_settings.editable_settings["Whisper Container Name"]))
            self.container_manager.set_status_icon_color(widget_name, self.container_manager.start_container(app_settings.editable_settings["Whisper Caddy Container Name"]))
        except Exception as e:
            tk.messagebox.showerror("Error", f"An error occurred while starting the Whisper container: {e}")

    def stop_whisper_container(self, widget_name, app_settings):
        """
        Stop the Whisper container.

        :param widget_name: The name of the widget to update with the container status.
        :type widget_name: str
        :param app_settings: The application settings containing container names.
        :type app_settings: ApplicationSettings
        """
        try:
            self.container_manager.set_status_icon_color(widget_name, self.container_manager.stop_container(app_settings.editable_settings["Whisper Container Name"]))
            self.container_manager.set_status_icon_color(widget_name, self.container_manager.stop_container(app_settings.editable_settings["Whisper Caddy Container Name"]))
        except Exception as e:
            tk.messagebox.showerror("Error", f"An error occurred while stopping the Whisper container: {e}")

    def check_llm_containers(self):
        """
        Check the status of the LLM containers.
        """
        status_check = all([
            self.container_manager.check_container_status(self.settings.editable_settings["LLM Container Name"]),
            self.container_manager.check_container_status(self.settings.editable_settings["LLM Caddy Container Name"]),
            self.container_manager.check_container_status(self.settings.editable_settings["LLM Authentication Container Name"])
        ])
        return ContainerState.CONTAINER_STARTED if status_check else ContainerState.CONTAINER_STOPPED

    def check_whisper_containers(self):
        """
        Check the status of the Whisper containers.
        """
        status_check = all([
            self.container_manager.check_container_status(self.settings.editable_settings["Whisper Container Name"]),
            self.container_manager.check_container_status(self.settings.editable_settings["Whisper Caddy Container Name"])
        ])

        return ContainerState.CONTAINER_STARTED if status_check else ContainerState.CONTAINER_STOPPED 