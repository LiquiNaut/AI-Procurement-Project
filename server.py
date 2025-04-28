from fastapi import FastAPI, HTTPException, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# Import both agents
from custom_agents import Agent as ProcurementAgentImpl, Runner  # Renamed to avoid conflict
from ai_agent_service import ProcurementAgent # This wraps the implementation
from shopping_agent import ShoppingAgent
import uvicorn
import asyncio
import nest_asyncio
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime
import httpx
import os
import json
import hmac
import hashlib
import base64

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

app = FastAPI()
# Instantiate both agents
procurement_agent_service = ProcurementAgent() # Keep using the service wrapper
shopping_agent = ShoppingAgent()

# In-memory conversations store (use a database in production)
conversations = {}

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "https://ai-procurement.netlify.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WhatsApp configuration
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_API_VERSION = "v19.0"
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

# WhatsApp Models
class WhatsAppChangeValue(BaseModel):
    messaging_product: str
    metadata: dict
    contacts: Optional[List[dict]] = None
    messages: Optional[List[dict]] = None
    statuses: Optional[List[dict]] = None

class WhatsAppChange(BaseModel):
    value: WhatsAppChangeValue
    field: str

class WhatsAppEntry(BaseModel):
    id: str
    changes: List[WhatsAppChange]

class WhatsAppWebhookPayload(BaseModel):
    object: str
    entry: List[WhatsAppEntry]

class Message(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    cached_messages: Optional[List[Dict[str, Any]]] = None

# WhatsApp Webhook Verification
@app.get("/webhook/whatsapp")
async def verify_webhook(request: Request):
    """Verifies webhook for WhatsApp API."""
    print("Received verification request")
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        print(f"Webhook verified successfully! Challenge: {challenge}")
        return Response(content=challenge, status_code=200)
    else:
        print(f"Webhook verification failed. Mode: {mode}, Token: {token}")
        raise HTTPException(status_code=403, detail="Verification token mismatch")

# WhatsApp Webhook Handler
@app.post("/webhook/whatsapp")
async def handle_whatsapp_message(payload: WhatsAppWebhookPayload, background_tasks: BackgroundTasks):
    """Handles incoming messages from WhatsApp."""
    print("Received WhatsApp notification")
    
    try:
        # Verify webhook signature (security)
        # This is a placeholder - implement proper signature verification in production
        # signature = request.headers.get("x-hub-signature-256")
        # if not verify_signature(signature, await request.body()):
        #     raise HTTPException(status_code=403, detail="Invalid signature")

        for entry in payload.entry:
            for change in entry.changes:
                if change.field == "messages" and change.value.messages:
                    for message_data in change.value.messages:
                        if message_data.get("type") == "text" and not message_data.get("from_me"):
                            sender_wa_id = message_data["from"]
                            user_message = message_data["text"]["body"]
                            print(f"Received message: '{user_message}' from {sender_wa_id}")

                            background_tasks.add_task(
                                process_incoming_whatsapp_message, 
                                sender_wa_id, 
                                user_message
                            )

    except Exception as e:
        print(f"Error processing webhook payload: {e}")

    return Response(content="EVENT_RECEIVED", status_code=200)

# WhatsApp Message Sender
async def send_whatsapp_message(recipient_wa_id: str, message_text: str):
    """Sends a text message to a user via WhatsApp Cloud API."""
    if not WHATSAPP_ACCESS_TOKEN or not PHONE_NUMBER_ID:
        print("ERROR: WhatsApp credentials not configured.")
        return

    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_wa_id,
        "type": "text",
        "text": {"body": message_text},
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            print(f"Successfully sent message to {recipient_wa_id}: {response.json()}")
    except httpx.RequestError as e:
        print(f"Error sending WhatsApp message (network): {e}")
    except httpx.HTTPStatusError as e:
        print(f"Error sending WhatsApp message (HTTP status): {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"Unexpected error sending WhatsApp message: {e}")

# WhatsApp Message Processor
async def process_incoming_whatsapp_message(sender_wa_id: str, user_message: str):
    """Processes incoming WhatsApp message through AI agents and sends response."""
    print(f"Processing message for {sender_wa_id}: '{user_message}'")

    conversation_id = sender_wa_id

    if conversation_id not in conversations:
        conversations[conversation_id] = {
            'messages': [],
            'chat_history': [{'role': 'system', 'content': procurement_agent_service.agent.instructions}],
            'created_at': datetime.now().isoformat()
        }
    current_chat_history = conversations[conversation_id]['chat_history']

    try:
        # Process with Procurement Agent
        procurement_result = procurement_agent_service.process_message(
            user_message,
            current_chat_history
        )
        ai_response_text = procurement_result["message"]
        final_specification = procurement_result["specification"]
        conversations[conversation_id]['chat_history'] = procurement_result['history']

        # If specification is finalized, call Shopping Agent
        shopping_options_text = ""
        if final_specification:
            print(f"Specification finalized for {sender_wa_id}, calling Shopping Agent...")
            shopping_options = await shopping_agent.find_options(final_specification)
            if shopping_options:
                shopping_options_text = "\n\nHere are some shopping options I found:"
                for option in shopping_options[:3]:
                    shopping_options_text += f"\n- {option['title']}: {option['link']}"

        # Combine responses
        full_response = ai_response_text + shopping_options_text

        # Send response back via WhatsApp
        await send_whatsapp_message(sender_wa_id, full_response)

    except Exception as e:
        print(f"Error processing AI response for {sender_wa_id}: {e}")
        await send_whatsapp_message(sender_wa_id, "Sorry, I encountered an error processing your request.")

@app.post("/api/chat")
async def chat(message: Message):
    try:
        conversation_id = message.conversation_id
        
        # Debug logging
        print(f"Received message: {message.message}")
        print(f"Conversation ID: {conversation_id}")
        print(f"Cached messages count: {len(message.cached_messages) if message.cached_messages else 0}")
        
        # Convert cached messages if available
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
                    "content": procurement_agent_service.agent.instructions # Use instructions from the service's agent
                })
            
            print(f"Converted {len(converted_messages)} messages from cache")
        
        # Create new conversation if ID doesn't exist
        if not conversation_id or conversation_id not in conversations:
            conversation_id = str(uuid.uuid4())
            print(f"Creating new conversation with ID: {conversation_id}")
            
            initial_chat_history = converted_messages if converted_messages else [
                {
                    "role": "system",
                    "content": procurement_agent_service.agent.instructions
                }
            ]
            
            conversations[conversation_id] = {
                'messages': message.cached_messages.copy() if message.cached_messages else [],
                'chat_history': initial_chat_history,
                'created_at': datetime.now().isoformat(),
                'restored_from_cache': bool(converted_messages)
            }
            print(f"Initialized conversation ({'cached' if converted_messages else 'fresh'}) with {len(initial_chat_history)} history messages")
            
        # For existing conversations, update the chat_history if we have cached messages
        elif converted_messages:
            print(f"Updating existing conversation {conversation_id} with {len(converted_messages)} cached messages")
            conversations[conversation_id]['chat_history'] = converted_messages
        
        current_chat_history = conversations[conversation_id]['chat_history']
        print(f"Chat history length before processing: {len(current_chat_history)}")
        
        # === Step 1: Process message with Procurement Agent ===
        procurement_result = procurement_agent_service.process_message(
            message.message,
            current_chat_history
        )
        
        # Update the conversation history with the procurement agent's result
        conversations[conversation_id]['chat_history'] = procurement_result['history']
        
        # Add user message and procurement agent response to messages list for frontend
        conversations[conversation_id]['messages'].append({
            'role': 'user',
            'content': message.message,
            'timestamp': datetime.now().isoformat()
        })
        conversations[conversation_id]['messages'].append({
            'role': 'assistant',
            'content': procurement_result['message'],
            'timestamp': datetime.now().isoformat()
        })
        
        # === Step 2: If specification finalized, call Shopping Agent ===
        shopping_options = None
        final_specification = procurement_result["specification"]
        
        if final_specification:
            print(f"Procurement agent finalized specification. Calling Shopping Agent.")
            try:
                # Call the shopping agent asynchronously
                shopping_options = await shopping_agent.find_options(final_specification)
                print(f"Shopping agent returned {len(shopping_options) if shopping_options else 0} options.")
            except Exception as shop_e:
                print(f"Error calling Shopping Agent: {shop_e}")
                # Optionally add an error message for the user
                # procurement_result["message"] += "\n(Could not search for shopping options due to an error.)"

        # === Step 3: Prepare response for frontend ===
        print(f"Product extraction from agent: {procurement_agent_service.current_product}")
        print(f"Chat history length after processing: {len(conversations[conversation_id]['chat_history'])}")
        print(f"Response message: {procurement_result['message'][:50]}...")
        
        response_payload = {
            "conversation_id": conversation_id,
            "response": procurement_result["message"],
            "productSpecification": final_specification,
            "isSpecificationFinalized": bool(final_specification),
            "messages": conversations[conversation_id]['messages'],
            # Add shopping options if they exist
            "shoppingOptions": shopping_options 
        }
        
        return response_payload
        
    except Exception as e:
        import traceback
        print(f"Error in chat endpoint: {str(e)}")
        traceback.print_exc() # Print full traceback for debugging
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "conversation_id": conversation_id,
        "messages": conversations[conversation_id]['messages'],
    }

# Removed check-api-key endpoint as it was not fully implemented

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 