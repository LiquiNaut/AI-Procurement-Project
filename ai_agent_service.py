from custom_agents import Agent, Runner
from typing import List, Dict, Any
import json
import os
from dotenv import load_dotenv
import openai
import asyncio
import nest_asyncio
import re

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

load_dotenv()

class ProcurementAgent:
    def __init__(self):
        # Initialize OpenAI client
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        self.agent = Agent(
            name="Procurement Assistant",
            instructions="""You are a helpful AI procurement assistant. Your goal is to help users specify products they want to purchase. 
            CRITICALLY IMPORTANT: You MUST remember the specific product name and all details the user provides across the entire conversation.
            
            Follow these guidelines:
            1. ALWAYS refer to the exact product name in every response (e.g., "Pyrus calleryana" not just "plant")
            2. Maintain a mental list of all specifications mentioned so far and reference them in your responses
            3. If a user asks if you remember what they specified, summarize ALL the details they've provided so far
            4. When enough details have been provided and the user indicates they're done (e.g., "that's all", "no, thank you", etc.), 
               you MUST output a finalized product specification
            5. Always output the finalized specification in JSON format EXACTLY like this:
               ```json
               {
                 "name": "Product Name",
                 "description": "Detailed description of the product",
                 "features": ["Feature 1", "Feature 2", "Feature 3"],
                 "estimatedPrice": "Price range or exact price",
                 "category": "Product category"
               }
               ```
            6. The JSON must be enclosed in triple backticks with "json" exactly as shown above
            7. Before the JSON, summarize the specification in natural language
            
            Example conversation flow:
            User: "I want to buy an iPhone 15 Pro, 256GB, black"
            Assistant: "I understand you're looking for an iPhone 15 Pro with 256GB storage in black color. Would you like to specify any additional features or accessories for this iPhone 15 Pro?"
            User: "No, that's all"
            Assistant: "Perfect! Here's the specification for your iPhone 15 Pro with 256GB storage in black color.
            
            ```json
            {
              "name": "iPhone 15 Pro",
              "description": "Apple iPhone 15 Pro with 256GB storage in black color",
              "features": ["256GB storage", "Black color", "Unlocked"],
              "estimatedPrice": "$999-$1099",
              "category": "Smartphones"
            }
            ```"
            
            Example plant conversation:
            User: "I want to buy Pyrus calleryana"
            Assistant: "I understand you're looking for a Pyrus calleryana (Callery Pear tree). Could you specify the size, container type, or any other preferences for this Pyrus calleryana?"
            User: "height 90-120cm, container grown"
            Assistant: "Thank you for specifying. You're looking for a Pyrus calleryana that is container grown and 90-120cm in height. Is there anything else you'd like to specify about this Pyrus calleryana?"
            
            When a user asks "give me the specs" or similar, always provide a full specification, including the formatted JSON.
            """
        )
        # Initialize chat history with system message
        self.chat_history = [
            {
                "role": "system",
                "content": self.agent.instructions
            }
        ]
        self.current_product = {
            "name": None,
            "specifications": {}
        }

    def process_message(self, user_message: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        try:
            # Debug logging
            print(f"Processing message: {user_message}")
            print(f"History length: {len(history) if history else 0}")
            
            # Important: If external history is provided, use it to initialize our chat_history
            # This ensures we maintain continuity across different sessions
            if history and len(history) > 0:
                # Ensure system message is always first
                system_message = next((msg for msg in history if msg["role"] == "system"), None)
                if not system_message:
                    history = [{"role": "system", "content": self.agent.instructions}] + history
                
                # Use the provided history to replace our chat_history
                self.chat_history = history.copy()
                print(f"Updated chat_history with provided history ({len(history)} messages)")
                
                # Try to extract product details from history
                self._extract_product_from_history(self.chat_history)
                print(f"Extracted product details: {self.current_product}")
            else:
                # Ensure we have a system message at the beginning
                if not self.chat_history or len(self.chat_history) == 0:
                    self.chat_history = [{"role": "system", "content": self.agent.instructions}]
                elif self.chat_history[0]["role"] != "system":
                    self.chat_history = [{"role": "system", "content": self.agent.instructions}] + self.chat_history

            # Always append the new user message to the chat history
            self.chat_history.append({
                "role": "user",
                "content": user_message
            })
            print(f"Added user message to chat_history. New length: {len(self.chat_history)}")

            # Special trigger for finalizing specification 
            finalize_triggers = ["that's all", "no, thank you", "nothing else", "that is all", "that should be it", "no thank", "thats all"]
            should_finalize = any(trigger in user_message.lower() for trigger in finalize_triggers)
            
            # Memory triggers for remembering product
            memory_triggers = ["remember", "what did i", "what was the", "specified earlier", "what product", "give me the spec", "specs again"]
            should_remember = any(trigger in user_message.lower() for trigger in memory_triggers)
            
            # Create a new event loop for this thread if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Prepare context with additional instructions and FULL chat history
            context = {"chat_history": self.chat_history}
            print(f"Sending chat_history with {len(self.chat_history)} messages to agent")
            
            # If we have product info, include it in instructions
            product_summary = self._get_product_summary()
            context["instructions"] = f"Remember, the user has previously mentioned: {product_summary}"
            
            if should_finalize or "give me the specification" in user_message.lower():
                finalize_instruction = f"The user has indicated they're done specifying the product or wants a specification. You must output a finalized JSON specification using the exact format specified in your instructions. Based on the conversation, they want: {product_summary}"
                context["instructions"] = finalize_instruction
            
            if should_remember:
                remember_instruction = f"The user is asking you to recall what they specified previously. Make sure to mention ALL details they've provided so far AND provide a JSON specification. Based on the conversation history, they have mentioned: {product_summary}"
                context["instructions"] = remember_instruction
                
            # Run the agent with FULL chat history context
            result = loop.run_until_complete(Runner.run(
                self.agent, 
                user_message,
                context=context
            ))
            
            # Always append assistant's response to chat history
            self.chat_history.append({
                "role": "assistant",
                "content": result.final_output
            })
            print(f"Added assistant response to chat_history. Final length: {len(self.chat_history)}")

            # Check if the response contains a JSON specification
            if "```json" in result.final_output:
                try:
                    # Extract JSON part
                    json_str = result.final_output.split("```json")[1].split("```")[0].strip()
                    specification = json.loads(json_str)
                    return {
                        "success": True,
                        "message": result.final_output.split("```json")[0].strip(),
                        "specification": specification,
                        "history": self.chat_history  # Return the COMPLETE updated history
                    }
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON: {e}")
                    return {
                        "success": True,
                        "message": result.final_output,
                        "specification": None,
                        "history": self.chat_history  # Return the COMPLETE updated history
                    }
            
            # Always return the complete chat history
            return {
                "success": True,
                "message": result.final_output,
                "specification": None,
                "history": self.chat_history  # Return the COMPLETE updated history
            }
        except Exception as e:
            print(f"Error in process_message: {e}")
            return {
                "success": False,
                "message": f"An error occurred: {str(e)}",
                "specification": None,
                "history": self.chat_history  # Return the COMPLETE updated history even on error
            }
    
    def _extract_product_from_history(self, history: List[Dict[str, str]]) -> None:
        """Extract product details from conversation history"""
        user_messages = [msg["content"] for msg in history if msg["role"] == "user"]
        assistant_messages = [msg["content"] for msg in history if msg["role"] == "assistant"]
        
        # First pass: look for explicit product mentions
        self._extract_explicit_products(user_messages)
        
        # If no products found, try more sophisticated methods
        if not self.current_product["name"]:
            self._extract_from_patterns(user_messages)
        
        # If still no product, look in assistant messages for confirmations
        if not self.current_product["name"]:
            self._extract_from_assistant_messages(assistant_messages)
        
        # Extract specifications regardless of product name
        self._extract_specifications(user_messages)
        
        print(f"Extracted product: {self.current_product}")
    
    def _extract_explicit_products(self, messages: List[str]) -> None:
        """Extract explicitly mentioned products"""
        product_keywords = ["buy", "purchase", "looking for", "interested in", "want to get", "but a"]
        
        for msg in messages:
            # Check for explicit mentions with keywords
            for keyword in product_keywords:
                if keyword in msg.lower():
                    parts = msg.lower().split(keyword, 1)
                    if len(parts) > 1 and parts[1].strip():
                        # Extract the text after the keyword
                        text_after = parts[1].strip().strip(',.!?:;')
                        
                        # Look for capitalized words which might be product names
                        potential_products = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', msg)
                        if potential_products:
                            for product in potential_products:
                                if len(product) > 2 and product.lower() in text_after.lower():
                                    self.current_product["name"] = product
                                    return
                        
                        # Check for ":" which often indicates a product specification
                        if ":" in text_after:
                            product_part = text_after.split(":", 1)[1].strip()
                            if product_part:
                                self.current_product["name"] = product_part
                                return
                        
                        # Otherwise use the text after the keyword
                        if len(text_after) > 2:
                            # Look for the first substantive word or phrase
                            words = text_after.split()
                            if words and len(words[0]) > 2:
                                self.current_product["name"] = words[0]
                                if len(words) > 1 and words[1].lower() not in ["a", "an", "the", "of", "for", "with"]:
                                    self.current_product["name"] += " " + words[1]
                            else:
                                self.current_product["name"] = text_after[:30]  # Limit length
    
    def _extract_from_patterns(self, messages: List[str]) -> None:
        """Extract product from common patterns in messages"""
        for msg in messages:
            # Look for common phrases
            plant_match = re.search(r'([A-Z][a-z]+ [a-z]+)', msg)
            if plant_match:
                self.current_product["name"] = plant_match.group(1)
                return
            
            # Look for quoted product names
            quote_match = re.search(r'"([^"]+)"', msg)
            if quote_match:
                self.current_product["name"] = quote_match.group(1)
                return
            
            # Look for detailed specifications which might indicate a product
            spec_matches = re.findall(r'(\d+[cm|mm|inches|"]\s*(?:height|width|tall|long))', msg, re.IGNORECASE)
            if spec_matches and len(msg.split()) < 20:  # If it's a short message with specifications
                potential_product = re.sub(r'\d+[cm|mm|inches|"]\s*(?:height|width|tall|long)', '', msg, flags=re.IGNORECASE)
                potential_product = potential_product.strip().strip(',.!?:;')
                if potential_product and len(potential_product) > 2:
                    self.current_product["name"] = potential_product
                    return
    
    def _extract_from_assistant_messages(self, messages: List[str]) -> None:
        """Extract product mentions from assistant messages"""
        # Look in assistant confirmations
        for msg in messages:
            # Look for confirmation patterns
            confirmation_patterns = [
                r"you're looking for (?:a|an) ([^.,!?]+)",
                r"you want to buy (?:a|an) ([^.,!?]+)",
                r"interested in (?:a|an) ([^.,!?]+)",
                r"you're interested in (?:the|a|an) ([^.,!?]+)",
                r"you'd like to purchase (?:a|an) ([^.,!?]+)"
            ]
            
            for pattern in confirmation_patterns:
                match = re.search(pattern, msg, re.IGNORECASE)
                if match:
                    self.current_product["name"] = match.group(1).strip()
                    return
            
            # Look for product mentions in parentheses (common for scientific names)
            paren_match = re.search(r'\(([^)]+)\)', msg)
            if paren_match:
                self.current_product["name"] = paren_match.group(1).strip()
                return

    def _extract_specifications(self, messages: List[str]) -> None:
        """Extract specifications from user messages"""
        # Common specification types
        spec_patterns = {
            "size": r'(\d+\s*-?\s*\d+\s*(?:cm|mm|m|inches|feet|"|ft))',
            "color": r'(?:color|colour):\s*([a-zA-Z]+)',
            "container": r'(container\s*(?:grown|raised|planted))',
            "quantity": r'(\d+\s*(?:units|pieces|pcs|count))',
            "delivery": r'(delivery|shipping):\s*([^.,!?]+)'
        }
        
        for msg in messages:
            for spec_type, pattern in spec_patterns.items():
                matches = re.findall(pattern, msg, re.IGNORECASE)
                if matches:
                    if spec_type not in self.current_product["specifications"]:
                        self.current_product["specifications"][spec_type] = []
                    
                    for match in matches:
                        if isinstance(match, tuple):  # Some regex patterns return tuples
                            match = " ".join(match).strip()
                        
                        if match and match not in self.current_product["specifications"][spec_type]:
                            self.current_product["specifications"][spec_type].append(match)
            
            # Look for key-value pairs (e.g., "height: 90-120cm")
            kv_matches = re.findall(r'([a-zA-Z]+):\s*([^.,!?]+)', msg)
            for key, value in kv_matches:
                key = key.lower().strip()
                value = value.strip()
                
                if key not in self.current_product["specifications"]:
                    self.current_product["specifications"][key] = []
                
                if value and value not in self.current_product["specifications"][key]:
                    self.current_product["specifications"][key].append(value)
    
    def _get_product_summary(self) -> str:
        """Get a summary of the current product and its specifications"""
        if not self.current_product["name"]:
            return "No product specified yet."
        
        summary = f"Product: {self.current_product['name']}"
        
        if self.current_product["specifications"]:
            summary += ". Specifications: "
            specs = []
            
            for spec_type, values in self.current_product["specifications"].items():
                if values:
                    spec_str = f"{spec_type}: {', '.join(values)}"
                    specs.append(spec_str)
            
            summary += "; ".join(specs)
        
        return summary
    
    def _try_extract_from_conversation(self) -> str:
        """Try to extract product information from the conversation as a fallback"""
        important_words = []
        for msg in self.chat_history:
            if msg["role"] == "user":
                # Extract capitalized words which might be product names
                words = msg["content"].split()
                for word in words:
                    if word and word[0].isupper() and len(word) > 2:
                        important_words.append(word.strip(',.!?:;'))
        
        if important_words:
            return "Potentially mentioned product names or details: " + ", ".join(important_words)
        return "No specific product details detected."

    def has_valid_api_key(self) -> bool:
        try:
            return bool(os.getenv("OPENAI_API_KEY"))
        except Exception:
            return False 