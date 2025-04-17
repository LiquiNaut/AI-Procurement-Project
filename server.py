from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ai_agent_service import ProcurementAgent
import uvicorn
import asyncio
import nest_asyncio
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime
import json

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

app = FastAPI()
agent = ProcurementAgent()

# In-memory conversations store (use a database in production)
conversations = {}

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # Angular app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    cached_messages: Optional[List[Dict[str, Any]]] = None

@app.post("/api/chat")
async def chat(message: Message):
    try:
        conversation_id = message.conversation_id
        
        # Debug logging
        print(f"Received message: {message.message}")
        print(f"Conversation ID: {conversation_id}")
        print(f"Cached messages count: {len(message.cached_messages) if message.cached_messages else 0}")
        
        # Always convert cached messages if available
        converted_messages = None
        if message.cached_messages and len(message.cached_messages) > 0:
            # Convert the messages to the format expected by the agent
            converted_messages = []
            for msg in message.cached_messages:
                if msg.get("role") and msg.get("content"):
                    converted_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Ensure system message is present
            if not any(msg["role"] == "system" for msg in converted_messages):
                converted_messages.insert(0, {
                    "role": "system",
                    "content": agent.agent.instructions
                })
            
            print(f"Converted {len(converted_messages)} messages from cache")
        
        # Create new conversation if ID doesn't exist
        if not conversation_id or conversation_id not in conversations:
            conversation_id = str(uuid.uuid4())
            print(f"Creating new conversation with ID: {conversation_id}")
            
            if converted_messages:
                # Use converted messages from above
                conversations[conversation_id] = {
                    'messages': message.cached_messages.copy() if message.cached_messages else [],
                    'chat_history': converted_messages,
                    'created_at': datetime.now().isoformat(),
                    'restored_from_cache': True
                }
                print(f"Initialized from {len(converted_messages)} cached messages")
            else:
                # Start a fresh conversation
                conversations[conversation_id] = {
                    'messages': [],
                    'chat_history': [
                        {
                            "role": "system",
                            "content": agent.agent.instructions
                        }
                    ],
                    'created_at': datetime.now().isoformat()
                }
                print("Initialized fresh conversation")
        # For existing conversations, update the chat_history if we have cached messages
        elif converted_messages:
            print(f"Updating existing conversation {conversation_id} with cached messages")
            conversations[conversation_id]['chat_history'] = converted_messages
        
        print(f"Chat history length before processing: {len(conversations[conversation_id]['chat_history'])}")
        
        # Process the message with chat history
        result = agent.process_message(
            message.message, 
            conversations[conversation_id]['chat_history']
        )
        
        # Update the conversation history
        conversations[conversation_id]['chat_history'] = result['history']
        
        # Add user message to messages
        conversations[conversation_id]['messages'].append({
            'role': 'user',
            'content': message.message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Add assistant response to messages
        conversations[conversation_id]['messages'].append({
            'role': 'assistant',
            'content': result['message'],
            'timestamp': datetime.now().isoformat()
        })
        
        # Debug logging
        print(f"Product extraction from agent: {agent.current_product}")
        print(f"Chat history length after processing: {len(conversations[conversation_id]['chat_history'])}")
        print(f"Response message: {result['message'][:50]}...")
        
        return {
            "conversation_id": conversation_id,
            "response": result["message"],
            "productSpecification": result["specification"],
            "isSpecificationFinalized": bool(result["specification"]),
            "messages": conversations[conversation_id]['messages']
        }
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "conversation_id": conversation_id,
        "messages": conversations[conversation_id]['messages'],
    }

@app.get("/api/check-api-key")
async def check_api_key():
    return {"has_valid_key": agent.has_valid_api_key()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 