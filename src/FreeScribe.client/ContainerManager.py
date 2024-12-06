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

from enum import Enum
import docker
import asyncio
import time

class ContainerState(Enum):
    CONTAINER_STOPPED = "ContainerStopped"
    CONTAINER_STARTED = "ContainerStarted"
    
class ContainerManager:
    """
    Manages Docker containers by starting and stopping them.

    This class provides methods to interact with Docker containers,
    including starting, stopping, and checking their status.

    Attributes:
        client (docker.DockerClient): The Docker client used to interact with containers.
    """

    def __init__(self):
        """
        Initialize the ContainerManager with a Docker client.
        """
        self.client = None

        try:
            self.client = docker.from_env()
        except docker.errors.DockerException as e:
            self.client = None

    def start_container(self, container_name):
        """
        Start a Docker container by its name.

        :param container_name: The name of the container to start.
        :type container_name: str
        :raises docker.errors.NotFound: If the specified container is not found.
        :raises docker.errors.APIError: If an error occurs while starting the container.
        """
        try:
            container = self.client.containers.get(container_name)
            container.start()
            return ContainerState.CONTAINER_STARTED
        except docker.errors.NotFound as e:
            raise docker.errors.NotFound(f"Container {container_name} not found.") from e
        except docker.errors.APIError as e:
            raise docker.errors.APIError(f"An error occurred while starting the container: {e}") from e

    def update_container_status_icon(self, dot, container_name):
        """Update the status icon for a Docker container based on its current state.

        This method checks the current status of a specified Docker container and updates
        the visual indicator (dot) to reflect that status using appropriate colors.
        The method only executes if there is an active Docker client connection.

        Parameters
        ----------
        dot : QWidget
            The widget representing the status indicator dot that will be updated
            with the appropriate color based on container status.
        container_name : str
            The name of the Docker container to check the status for.

        Notes
        -----
        This method requires:
            - An active Docker client connection through container_manager
            - A valid container name that exists in Docker
        
        The status colors are managed by the container_manager's set_status_icon_color
        method and typically follow conventions like:
            - Green for running
            - Red for stopped/failed
            - Yellow for transitional states

        Examples
        --------
        >>> status_dot = QWidget()
        >>> self.update_container_status_icon(status_dot, "mysql-container")
        """
        if self.client is not None:
            status = self.check_container_status(container_name)
            self.set_status_icon_color(dot, ContainerState.CONTAINER_STARTED if status else ContainerState.CONTAINER_STOPPED)

    def stop_container(self, container_name):
        """
        Stop a Docker container by its name.

        :param container_name: The name of the container to stop.
        :type container_name: str
        :raises docker.errors.NotFound: If the specified container is not found.
        :raises docker.errors.APIError: If an error occurs while stopping the container.
        """
        try:
            container = self.client.containers.get(container_name)
            container.stop()
            print(f"Container {container_name} stopped successfully.")
            return ContainerState.CONTAINER_STOPPED
        except docker.errors.NotFound as e:
            raise docker.errors.NotFound(f"Container {container_name} not found.") from e
        except docker.errors.APIError as e:
            raise docker.errors.APIError(f"An error occurred while stopping the container: {e}") from e

    def check_container_status(self, container_name):
        """
        Check the status of a Docker container by its name.

        :param container_name: The name of the container to check.
        :type container_name: str
        :return: True if the container is running, False otherwise.
        :rtype: bool
        :raises docker.errors.NotFound: If the specified container is not found.
        :raises docker.errors.APIError: If an error occurs while checking the container status.
        """
        try:
            container = self.client.containers.get(container_name)
            status = container.status

            return status == "running"

        except docker.errors.NotFound:
            print(f"Container {container_name} not found.")
            return False
        except docker.errors.APIError as e:
            print(f"An error occurred while checking the container status: {e}")
            return False
        except Exception as e:
            print(f"An error occurred while checking the container status: {e}")
            return False

    def set_status_icon_color(self, widget, status: ContainerState):
        """
        Set the color of the status icon based on the status of the container.

        :param widget: The widget representing the status icon.
        :type widget: tkinter.Widget
        :param status: The status of the container.
        :type status: ContainerState
        """
        if status not in ContainerState:
            raise ValueError(f"Invalid container state: {status}")
        
        if status == ContainerState.CONTAINER_STARTED:
            widget.config(fg='green')
        elif status == ContainerState.CONTAINER_STOPPED:
            widget.config(fg='red')

    def check_docker_availability(self):
        """
        Check if the Docker client is available.

        :return: True if the Docker client is available, False otherwise.
        :rtype: bool
        """
        try:
            self.client = docker.from_env()
        except docker.errors.DockerException as e:
            self.client = None
            
        return self.client is not None