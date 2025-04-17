import os
import openai
import json
from typing import List, Dict, Any, Optional

class Agent:
    def __init__(self, name: str, instructions: str):
        self.name = name
        self.instructions = instructions
        # Initialize the OpenAI client
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    async def process_message(self, user_message: str, chat_history: List[Dict[str, str]] = None) -> str:
        """
        Process a message using the OpenAI API, ensuring the chat history is used for context.
        
        Args:
            user_message: The message from the user
            chat_history: Previous messages in the conversation
            
        Returns:
            The AI's response
        """
        if not chat_history:
            # Start with system message if no history provided
            messages = [{"role": "system", "content": self.instructions}]
        else:
            # Use provided history, ensuring system message exists
            if not any(msg.get("role") == "system" for msg in chat_history):
                messages = [{"role": "system", "content": self.instructions}] + chat_history
            else:
                messages = chat_history.copy()
        
        # Add the current user message
        messages.append({"role": "user", "content": user_message})
        
        # Debug log to see what's being sent
        print(f"Sending {len(messages)} messages to OpenAI API")
        print(f"Last few messages: {json.dumps(messages[-3:], indent=2)}")
        
        try:
            # Use the current OpenAI API format
            response = self.client.chat.completions.create(
                model="gpt-4",  # Or your preferred model
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            assistant_response = response.choices[0].message.content
            return assistant_response
            
        except Exception as e:
            print(f"Error in OpenAI API call: {e}")
            return f"I encountered an error: {str(e)}"

class Result:
    """Simple class to match the expected interface"""
    def __init__(self, final_output):
        self.final_output = final_output

class Runner:
    """
    Runner class to handle processing messages through an agent.
    """
    
    @staticmethod
    async def run(agent: Agent, user_message: str, context: Dict[str, Any] = None) -> Result:
        """
        Run a message through an agent with context.
        
        Args:
            agent: The agent to process the message
            user_message: The message from the user
            context: Additional context, including chat_history
            
        Returns:
            Result object with final_output attribute
        """
        chat_history = None
        additional_instructions = None
        
        if context:
            # Extract chat history from context if available
            chat_history = context.get("chat_history")
            
            # Extract additional instructions if available
            additional_instructions = context.get("instructions")
            
            # If there are additional instructions, add or update the system message
            if additional_instructions and chat_history:
                # Find system message
                system_idx = next((i for i, msg in enumerate(chat_history) 
                                if msg.get("role") == "system"), None)
                
                if system_idx is not None:
                    # Update existing system message with additional instructions
                    chat_history[system_idx]["content"] = (
                        f"{agent.instructions}\n\n{additional_instructions}"
                    )
                else:
                    # Add system message with combined instructions
                    chat_history.insert(0, {
                        "role": "system", 
                        "content": f"{agent.instructions}\n\n{additional_instructions}"
                    })
        
        # Process the message with the agent
        response = await agent.process_message(user_message, chat_history)
        
        # Return a Result object to match the expected interface
        return Result(final_output=response) 