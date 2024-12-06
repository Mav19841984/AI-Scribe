from llama_cpp import Llama
import os
from typing import Optional, Dict, Any
import threading
from UI.LoadingWindow import LoadingWindow
import tkinter.messagebox as messagebox

class Model:
    """
    Model class for handling GPU-accelerated text generation using the Llama library.

    This class provides an interface to initialize a language model with specific configurations
    for GPU acceleration, generate responses based on a text prompt, and retrieve GPU settings.
    The class is configured to support multi-GPU setups and custom configurations for batch size,
    context window, and sampling settings. 

    Attributes:
        model: Instance of the Llama model configured with specified GPU and context parameters.
        config: Dictionary containing the GPU and model configuration.

    Methods:
        generate_response: Generates a text response based on an input prompt using
                        the specified sampling parameters.
        get_gpu_info: Returns the current GPU configuration and batch size details.
    """
    def __init__(
        self,
        model_path: str,
        chat_template: str = None,
        context_size: int = 4096,
        gpu_layers: int = -1,  # -1 means load all layers to GPU
        main_gpu: int = 0,     # Primary GPU device index
        tensor_split: Optional[list] = None,  # For multi-GPU setup
        n_batch: int = 512,    # Batch size for inference
        n_threads: Optional[int] = None,  # CPU threads when needed
        seed: int = 1337
    ):
        """
        Initializes the GGUF model with GPU acceleration.
        
        Args:
            model_path: Path to the model file
            context_size: Size of the context window
            gpu_layers: Number of layers to offload to GPU (-1 for all)
            main_gpu: Main GPU device index
            tensor_split: List of GPU memory splits for multi-GPU setup
            n_batch: Batch size for inference
            n_threads: Number of CPU threads
            seed: Random seed for reproducibility
        """
        try:
            # Set environment variables for GPU
            os.environ["CUDA_VISIBLE_DEVICES"] = str(main_gpu)
            
            # Initialize model with GPU settings
            self.model = Llama(
                model_path=model_path,
                n_ctx=context_size,
                n_gpu_layers=gpu_layers,
                n_batch=n_batch,
                n_threads=n_threads or os.cpu_count(),
                seed=seed,
                tensor_split=tensor_split,
                chat_format=chat_template,
            )
        
            # Store configuration
            self.config = {
                "gpu_layers": gpu_layers,
                "main_gpu": main_gpu,
                "context_size": context_size,
                "n_batch": n_batch
            }
        except Exception as e:
            self.model = None
            raise e
        
    def generate_response(
        self,
        prompt: str,
        max_tokens: int = 50,
        temperature: float = 0.1,
        top_p: float = 0.95,
        repeat_penalty: float = 1.1
    ) -> str:
        """
        Generates a response using GPU-accelerated inference.
        
        Args:
            prompt: Input text prompt
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (higher = more random)
            top_p: Top-p sampling threshold
            repeat_penalty: Penalty for repeating tokens
            
        Returns:
            Generated text response
        """
        try:
            # Generate response using the model

            # Message template for chat completion
            messages = [
                {"role": "user", 
                "content": prompt}
            ]

            response = self.model.create_chat_completion(
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                repeat_penalty=repeat_penalty,
            )

            # reset the model tokens
            self.model.reset()
            return response["choices"][0]["message"]["content"]
            
        except Exception as e:
            print(f"GPU inference error ({e.__class__.__name__}): {str(e)}")
            return f"({e.__class__.__name__}): {str(e)}"

    
    def get_gpu_info(self) -> Dict[str, Any]:
        """
        Returns information about the current GPU configuration.
        """
        return {
            "gpu_layers": self.config["gpu_layers"],
            "main_gpu": self.config["main_gpu"],
            "batch_size": self.config["n_batch"],
            "context_size": self.config["context_size"]
        }

    def close(self):
        """
        Unloads the model from GPU memory.
        """
        self.model.close()
        self.model = None
    
    def __del__(self):
        """Cleanup GPU memory on deletion"""
        if self.model is not None:
            self.model.close()
        self.model = None

class ModelManager:
    """
    Manages the lifecycle of a local LLM model including setup and unloading operations.

    This class provides static methods to handle model initialization, loading, and cleanup
    using the llama.cpp Python bindings. It supports different model architectures and
    quantization levels.

    Attributes:
        local_model (Llama): Static reference to the loaded model instance. None if no model is loaded.
    """
    local_model = None

    @staticmethod
    def setup_model(app_settings, root):
        """
        Initialize and load the LLM model based on application settings.

        Creates a loading window and starts model loading in a separate thread to prevent
        UI freezing. Automatically checks thread status and closes the loading window
        when complete.

        Args:
            app_settings: Application settings object containing model preferences
            root: Tkinter root window for creating the loading dialog

        Raises:
            ValueError: If the specified model file cannot be loaded
        
        Note:
            The method uses threading to avoid blocking the UI while loading the model.
            GPU layers are set to -1 for CUDA architecture and 0 for CPU.
        """
        loading_window = LoadingWindow(root, "Loading Model", "Loading Model. Please wait")

        # unload before loading new model
        if ModelManager.local_model is not None:
            ModelManager.unload_model()

        def load_model():
            """
            Internal function to handle the actual model loading process.
            
            Determines the model file based on settings and initializes the Llama instance
            with appropriate parameters.
            """
            gpu_layers = 0

            if app_settings.editable_settings["Architecture"] == "CUDA (Nvidia GPU)":
                gpu_layers = -1

            model_to_use = "gemma-2-2b-it-Q8_0.gguf"
                
            model_path = f"./models/{model_to_use}"
            try:
                ModelManager.local_model = Model(model_path,
                    context_size=4096,
                    gpu_layers=gpu_layers,
                    main_gpu=0,
                    n_batch=512,
                    n_threads=None,
                    seed=1337)
            except Exception as e:
                # model doesnt exist
                #TODO: Logo to system log
                messagebox.showerror("Model Error", f"Model failed to load. Please ensure you have a valid model selected in the settings. Currently trying to load: {os.path.abspath(model_path)}. Error received ({e.__class__.__name__}): {str(e)}")
                ModelManager.local_model = None

        thread = threading.Thread(target=load_model)
        thread.start()

        def check_thread_status(thread, loading_window, root):
            """
            Recursive function to check the status of the model loading thread.

            Args:
                thread: The thread to monitor
                loading_window: LoadingWindow instance to close when complete
                root: Tkinter root window for scheduling checks
            """
            if thread.is_alive():
                root.after(500, lambda: check_thread_status(thread, loading_window, root))
            else:
                loading_window.destroy()

        root.after(500, lambda: check_thread_status(thread, loading_window, root))


    @staticmethod
    def start_model_threaded(settings, root_window):
        """
        Start the model in a separate thread.

        :param settings: Configuration settings for the model
        :type settings: dict
        :param root_window: The main application window reference
        :type root_window: tkinter.Tk
        :return: The created thread instance
        :rtype: threading.Thread
        
        This method creates and starts a new thread that runs the model's start 
        function with the provided settings and root window reference. The model
        is accessed through ModelManager's local_model attribute.
        """
        thread = threading.Thread(target=ModelManager.setup_model, args=(settings, root_window))
        thread.start()
        return thread

    @staticmethod
    def unload_model():
        """
        Safely unload and cleanup the currently loaded model.

        Closes the model if it exists and sets the local_model reference to None.
        This method should be called before loading a new model or shutting down
        the application.
        """
        if ModelManager.local_model is not None:
            ModelManager.local_model.model.close()
            del ModelManager.local_model
            ModelManager.local_model = None
            