import asyncio
from ai_agent_service import ProcurementAgent
import json

async def main():
    print("Starting context test...")
    agent = ProcurementAgent()
    
    # First message
    print("\n--- SENDING FIRST MESSAGE ---")
    first_message = "Hi, my name is Boris and I'm looking for a Pyrus calleryana."
    result1 = agent.process_message(first_message)
    
    print(f"\nResponse: {result1['message'][:100]}...")
    print(f"History length: {len(result1['history'])}")
    
    # Second message to test context
    print("\n--- SENDING SECOND MESSAGE TO TEST CONTEXT ---")
    second_message = "Can you tell me what my name is and what product I'm looking for?"
    
    # Use history from previous response
    result2 = agent.process_message(second_message, result1['history'])
    
    print(f"\nResponse: {result2['message'][:100]}...")
    print(f"History length: {len(result2['history'])}")
    
    # Show the full conversation
    print("\n--- FULL CONVERSATION HISTORY ---")
    for i, msg in enumerate(result2['history']):
        if msg['role'] != 'system':  # Skip the long system message
            print(f"{i}. {msg['role']}: {msg['content'][:100]}...")
    
    print("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(main()) 