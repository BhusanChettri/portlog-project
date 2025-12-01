"""Gradio UI for Port Tariff Calculation System."""

import sys
from pathlib import Path
from typing import List, Tuple

import gradio as gr
from dotenv import load_dotenv

# Load environment variables
project_dir = Path(__file__).parent
parent_dir = project_dir.parent
env_file = parent_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)
elif (project_dir / ".env").exists():
    load_dotenv(project_dir / ".env")

# Add src to path
sys.path.insert(0, str(project_dir / "src"))

from src.core.workflow import TariffWorkflow


class TariffChatInterface:
    """Chat interface wrapper for TariffWorkflow.
    
    Provides a simple interface between Gradio's ChatInterface and
    the TariffWorkflow. Handles initialization and error handling.
    """
    
    def __init__(self):
        """Initialize the chat interface."""
        self.workflow = None
        self.initialized = False
    
    def initialize(self):
        """Initialize the workflow."""
        if not self.initialized:
            print("Initializing Port Tariff Workflow...")
            self.workflow = TariffWorkflow()
            self.workflow.initialize()
            self.initialized = True
            print("Workflow initialized successfully!")
    
    def process_message(self, message: str, history: List[Tuple[str, str]]) -> str:
        """Process a message and return a response.
        
        Args:
            message: The user's input message
            history: List of previous (user, assistant) message tuples
            
        Returns:
            str: The assistant's response
        """
        if not self.initialized:
            self.initialize()
        
        try:
            # Process the message through the workflow
            response = self.workflow.process(message)
            return response
        except Exception as e:
            return f"Error processing query: {str(e)}\n\nPlease try rephrasing your question or check that all required data files are available."


def create_demo():
    """Create and return a Gradio demo for the Port Tariff System.
    
    Returns:
        gr.Blocks: Configured Gradio interface
    """
    # Create chat interface (our custom class)
    tariff_chat = TariffChatInterface()
    
    # Initialize it (this will happen in background)
    tariff_chat.initialize()
    
    # Create the respond function that uses our chat implementation
    # Gradio ChatInterface expects a function that takes (message, history)
    # where history is a list of tuples (user_msg, assistant_msg)
    def respond(message: str, history: List[Tuple[str, str]]) -> str:
        """Process the message and return a response.
        
        Args:
            message: The user's input message
            history: List of previous (user, assistant) message tuples
        
        Returns:
            str: The assistant's response
        """
        return tariff_chat.process_message(message, history)
    
    # Custom CSS for centering description and styling input box
    custom_css = """
    /* Style all textareas in the chat interface */
    .gradio-container textarea {
        border: 2px solid #6366f1 !important;
        border-radius: 8px !important;
        padding: 12px !important;
        min-height: 60px !important;
    }
    .gradio-container textarea:focus {
        border-color: #4f46e5 !important;
        outline: none !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
    }
    /* Target input wrapper specifically */
    .gradio-container .input-wrap textarea,
    .gradio-container .input-wrap input[type="text"] {
        border: 2px solid #6366f1 !important;
        border-radius: 8px !important;
        padding: 12px !important;
    }
    .gradio-container .input-wrap textarea:focus,
    .gradio-container .input-wrap input[type="text"]:focus {
        border-color: #4f46e5 !important;
        outline: none !important;
    }
    /* Hide the Chatbot label/button - using valid CSS selectors */
    .gradio-container button[aria-label*="Chatbot"],
    .gradio-container .chatbot-label {
        display: none !important;
        visibility: hidden !important;
    }
    /* Target buttons in footer or chat area */
    .gradio-container footer button,
    .gradio-container .footer button {
        display: none !important;
    }
    /* Hide any button that might contain Chatbot text (will be handled by JS) */
    .gradio-container button {
        /* JavaScript will handle specific Chatbot buttons */
    }
    """
    
    # Create the Gradio interface with custom CSS
    with gr.Blocks(css=custom_css, theme=gr.themes.Soft()) as demo:
        # Title at the top
        gr.Markdown(
            "<h1 style='text-align: center; margin: 20px 0;'>Port Tariff Calculation System v0</h1>"
        )
        # Description text
        gr.Markdown(
            "<div style='text-align: center; margin: 20px 0; font-size: 16px;'>"
            "Ask questions about port charges for different vessel types, or request tariff calculations with specific parameters."
            "</div>"
        )
        chat_interface = gr.ChatInterface(
            fn=respond,
            title=None,  # Remove title from ChatInterface since we're adding it manually
            examples=None,  # Remove examples
        )
        
        # JavaScript to change placeholder text and hide Chatbot button on load
        demo.load(
            fn=None,
            js="""
            function() {
                function updatePlaceholder() {
                    const textareas = document.querySelectorAll('textarea');
                    textareas.forEach(function(textarea) {
                        if (textarea.getAttribute('placeholder') && 
                            textarea.getAttribute('placeholder').includes('Type a message')) {
                            textarea.setAttribute('placeholder', 'Ask any question about port charges!');
                        }
                    });
                }
                
                function hideChatbotButton() {
                    // Find and hide any button or element containing "Chatbot" text
                    const allElements = document.querySelectorAll('*');
                    allElements.forEach(function(element) {
                        const text = element.textContent || element.innerText || '';
                        if (text.trim() === 'Chatbot' || text.trim().includes('Chatbot')) {
                            // Check if it's a button or label
                            if (element.tagName === 'BUTTON' || 
                                element.tagName === 'LABEL' || 
                                element.tagName === 'SPAN' ||
                                element.closest('button')) {
                                element.style.display = 'none';
                                element.style.visibility = 'hidden';
                            }
                        }
                    });
                    
                    // Also hide buttons in footer or chat area
                    const footerButtons = document.querySelectorAll('footer button, .footer button');
                    footerButtons.forEach(function(btn) {
                        if (btn.textContent.includes('Chatbot')) {
                            btn.style.display = 'none';
                            btn.style.visibility = 'hidden';
                        }
                    });
                }
                
                // Update immediately
                updatePlaceholder();
                hideChatbotButton();
                
                // Update after a short delay to catch dynamically loaded elements
                setTimeout(function() {
                    updatePlaceholder();
                    hideChatbotButton();
                }, 500);
                setTimeout(function() {
                    updatePlaceholder();
                    hideChatbotButton();
                }, 1000);
                
                // Also listen for dynamic updates
                const observer = new MutationObserver(function(mutations) {
                    updatePlaceholder();
                    hideChatbotButton();
                });
                
                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });
            }
            """
        )
    
    return demo


def main():
    """Main entry point for the Port Tariff Calculation System."""
    print("=" * 60)
    print("Port Tariff Calculation System v0")
    print("=" * 60)
    print("Starting web interface...")
    print("The UI will open in your browser automatically.")
    print("If it doesn't, navigate to: http://localhost:7860")
    print("Press Ctrl+C to stop the server.")
    print("=" * 60)
    print()
    
    # Create and launch the demo
    demo = create_demo()
    demo.launch(
        server_name="0.0.0.0",  # Allow access from network
        server_port=7860,       # Default Gradio port
        share=False             # Set to True to create a public link
    )


if __name__ == "__main__":
    main()

