
import ctypes
from utils.file_utils import get_file_path
# Define the mutex name and error code
MUTEX_NAME = 'Global\\FreeScribe_Instance'
ERROR_ALREADY_EXISTS = 183

# Global variable to store the mutex handle
mutex = None

# function to check if another instance of the application is already running
def window_has_running_instance() -> bool:
    """
    Check if another instance of the application is already running.
    Returns:
        bool: True if another instance is running, False otherwise
    """
    global mutex

    # Create a named mutex
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    return ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS

def bring_to_front(app_name: str):
    """
    Bring the window with the given handle to the front.
    Parameters:
        app_name (str): The name of the application window to bring to the front
    """

    # TODO - Check platform and handle for different platform
    U32DLL = ctypes.WinDLL('user32')
    SW_SHOW = 5
    hwnd = U32DLL.FindWindowW(None, app_name)
    U32DLL.ShowWindow(hwnd, SW_SHOW)
    U32DLL.SetForegroundWindow(hwnd)

def close_mutex():
    """
    Close the mutex handle to release the resource.
    """
    global mutex
    if mutex:
        ctypes.windll.kernel32.ReleaseMutex(mutex)
        ctypes.windll.kernel32.CloseHandle(mutex)
        mutex = None

def get_application_version():
        version_str = "vx.x.x.alpha"
        try:
            with open(get_file_path('__version__'), 'r') as file:
                version_str = file.read().strip()
        except Exception as e:
            print(f"Error loading version file ({type(e).__name__}). {e}")
        finally:
            return version_str