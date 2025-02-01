# Settings Documentation
## General Settings
### Show Welcome Message
**Description**: Display welcome message on application startup  
**Default**: `true`  
**Type**: boolean  

### Show Scrub PHI
**Description**: Enable/Disable Scrub PHI (Only for local llm and private network RFC 18/19). Scrub PHI is used to remove potentially sensitive data before feeding it to a Large Language Model. Please note it is still your responsibility to ensure all data is being sent contains no sensitive data.  
**Default**: `false`  
**Type**: boolean  

## Whisper Settings
### Whisper Endpoint
**Description**: API endpoint for Whisper service. This sends a wav file from the client to the endpoint. Default is set to the Local Whisper container provided by ClinicianFOCUS.
**Default**: `https://localhost:2224/whisperaudio`  
**Type**: string  

### Whisper Server API Key
**Description**: API key for Whisper service authentication.
**Default**: `None`  
**Type**: string  

### Whisper Model
**Description**: Whisper model to use for speech recognition. Only applies to the local model. 

Size of the model to use (tiny, tiny.en, base, base.en,
small, small.en, distil-small.en, medium, medium.en, distil-medium.en, large-v1,
large-v2, large-v3, large, distil-large-v2, distil-large-v3, large-v3-turbo, or turbo),
a path to a converted model directory, or a CTranslate2-converted Whisper model ID from
the HF Hub. When a size or a model ID is configured, the converted model is downloaded
from the Hugging Face Hub.

**Default**: `small.en`  
**Type**: string  

### Local Whisper
**Description**: Use local Whisper instance instead of a remote whisper service.
**Default**: `true`  
**Type**: boolean  

### Real Time
**Description**: Enable real-time processing. This will send audio chunks to the whisper when silence is detected and 5 seconds of audio has been recorded. This setting is recommended as you will get real time transcription of your conversation. It is also the most efficient. 
**Default**: `true`  
**Type**: boolean  

## LLM Settings
### Model Endpoint
**Description**: API endpoint URL for the Large Language Model. It must be to a OpenAI api style.   
**Default**: `https://localhost:3334/v1/`  
**Type**: string  

### Use Local LLM
**Description**: Toggle to use a locally built in language model instead of the remote service.  
**Default**: `true`  
**Type**: boolean  

## Advanced Settings
<!-- ### use_story
**Description**: Enable story context for generation  
**Default**: `false`  
**Type**: boolean  

### use_memory
**Description**: Enable memory context for generation  
**Default**: `false`  
**Type**: boolean  

### use_authors_note
**Description**: Enable author's notes in generation  
**Default**: `false`  
**Type**: boolean  

### use_world_info
**Description**: Enable world information in context  
**Default**: `false`  
**Type**: boolean   -->

<!-- ### Enable Scribe Template
**Description**: Enable Scribe template functionality  
**Default**: `false`  
**Type**: boolean   -->

<!-- ### max_context_length
**Description**: Maximum number of tokens in the context window  
**Default**: `5000`  
**Type**: integer  

### max_length
**Description**: Maximum length of generated text  
**Default**: `400`  
**Type**: integer  

### rep_pen
**Description**: Repetition penalty factor  
**Default**: `1.1`  
**Type**: float  

### rep_pen_range
**Description**: Token range for repetition penalty  
**Default**: `5000`  
**Type**: integer  

### rep_pen_slope
**Description**: Slope of repetition penalty curve  
**Default**: `0.7`  
**Type**: float   -->

### temperature 
**Description**: Controls randomness in generation (higher = more random). Gives the LLM more freedom and creativity. More [here](https://platform.openai.com/docs/api-reference/chat/create#chat-create-temperature)
**Default**: `0.1`  
**Type**: float  

<!-- ### tfs
**Description**: Tail free sampling parameter  
**Default**: `0.97`  
**Type**: float   -->

<!-- ### top_a
**Description**: Top-A sampling parameter  
**Default**: `0.8`  
**Type**: float   -->

<!-- ### top_k
**Description**: Top-K sampling parameter  
**Default**: `30`  
**Type**: integer   -->

### top_p
**Description**: Top-P (nucleus) sampling parameter. More info [here](https://platform.openai.com/docs/api-reference/chat/create#chat-create-top_p).
**Default**: `0.4`  
**Type**: float  

<!-- ### typical
**Description**: Typical sampling parameter  
**Default**: `0.19`  
**Type**: float  

### sampler_order
**Description**: Order of sampling methods to apply  
**Default**: `[6, 0, 1, 3, 4, 2, 5]`  
**Type**: string (JSON array)  

### singleline
**Description**: Output single line responses only  
**Default**: `false`  
**Type**: boolean  

### frmttriminc
**Description**: Trim incomplete sentences from output  
**Default**: `false`  
**Type**: boolean   -->

<!-- ### frmtrmblln
**Description**: Remove blank lines from output  
**Default**: `false`  
**Type**: boolean   -->

### Use best_of
**Description**: Enable best-of sampling  
**Default**: `false`  
**Type**: boolean  

### best_of
**Description**: Number of completions to generate and select from. More [here](https://platform.openai.com/docs/api-reference/completions/create#completions-create-best_of).
**Default**: `2`  
**Type**: integer  

### Real Time Audio Length
**Description**: Length of audio segments for real-time processing (seconds)  
**Default**: `5`  
**Type**: integer  

### Use Pre-Processing
**Description**: Enable text pre-processing  
**Default**: `true`  
**Type**: boolean  

### Use Post-Processing
**Description**: Enable text post-processing  
**Default**: `false`  
**Type**: boolean  

<!-- ## Docker Settings
### LLM Container Name
**Description**: Docker container name for LLM service  
**Default**: `ollama`  
**Type**: string  

### LLM Caddy Container Name
**Description**: Docker container name for Caddy reverse proxy  
**Default**: `caddy-ollama`  
**Type**: string  

### LLM Authentication Container Name
**Description**: Docker container name for authentication service  
**Default**: `authentication-ollama`  
**Type**: string  

### Whisper Container Name
**Description**: Docker container name for Whisper service  
**Default**: `speech-container`  
**Type**: string  

### Whisper Caddy Container Name
**Description**: Docker container name for Whisper Caddy service  
**Default**: `caddy`  
**Type**: string  

### Auto Shutdown Containers on Exit
**Description**: Automatically stop Docker containers on application exit  
**Default**: `true`  
**Type**: boolean  

### Use Docker Status Bar
**Description**: Show Docker container status in UI  
**Default**: `false`  
**Type**: boolean   -->
