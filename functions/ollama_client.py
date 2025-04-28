import asyncio, json, os
import os
import asyncio
from ollama import AsyncClient
from dotenv import load_dotenv

load_dotenv("./settings/.env")
terminal_path = os.getenv("TERMINAL_PATH")


class OllamaClient:
    """
    A class to handle interactions with the Ollama API.
    This provides a clean interface for querying the LLM and processing responses.
    """

    def __init__(self, host=None, model=None):
        """Initialize the Ollama client with configuration"""
        self.settings = json.load(open(terminal_path + "settings/settings.json"))
        self.ollama_settings = self.settings.get("ollama_settings", {})
        self.host = self.ollama_settings.get("ollama_url", "http://localhost:11434")
        self.model = self.ollama_settings.get("ollama_model", "llama3.2:3b-instruct-q4_K_M")
        self.client = AsyncClient(host=self.host)
        self.system_prompt = self.settings["system_prompt"]

    async def query(self, prompt, system_context=None, temperature=0.1):
        """
        Send a query to the Ollama model and get a response.

        Args:
            prompt (str): The user's query
            system_context (str, optional): System instructions for the model
            temperature (float, optional): Creativity parameter (0.0-1.0)

        Returns:
            str: The model's response
        """
        try:
            # Prepare the message structure
            messages = [{"role": "system", "content": self.system_prompt}]

            # Add system message if provided
            if system_context:
                messages.append({"role": "system", "content": f"{system_context}"})

            # Add user message
            messages.append({"role": "user", "content": prompt})

            # Get response from model
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                stream=False,
                options={"temperature": temperature}
            )

            # Extract the assistant's message
            if response and "message" in response and "content" in response["message"]:
                return response["message"]["content"]
            else:
                return "Keine verwertbare Antwort erhalten."

        except Exception as e:
            return f"Fehler bei der Kommunikation mit Ollama: {str(e)}"

    def extract_command(self, response):
        """
        Extract the most likely command from an LLM response.

        Args:
            response (str): The LLM's response text

        Returns:
            str or None: The extracted command or None if no command found
        """
        # Split response into lines and clean them
        command_lines = [line.strip() for line in response.split("\n")
                         if line.strip() and not line.strip().startswith(("1.", "2.", "3."))]

        # Look for lines that look like commands (start with $ or don't have punctuation)
        potential_commands = [line.lstrip("$ ") for line in command_lines
                              if line.startswith("$") or not any(c in line for c in [":", ".", "?"])]

        # Return the first potential command if any were found
        return potential_commands[0] if potential_commands else None

    def format_context(self, context_results):
        """
        Format ChromaDB results into a text context for the LLM.

        Args:
            context_results (dict): Results from ChromaDB query

        Returns:
            str: Formatted context text
        """
        context_text = ""
        if context_results and "documents" in context_results and context_results["documents"]:
            # Format paths and contents for the LLM
            for i, (doc, path_id) in enumerate(zip(context_results["documents"], context_results["ids"])):
                context_text += f"Path: {path_id}\nContents: {doc}\n\n"

        return context_text if context_text else "Keine relevanten Systeminformationen gefunden."