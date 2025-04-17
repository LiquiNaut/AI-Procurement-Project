# AI Procurement Assistant

This project consists of an Angular frontend and a Python backend using the OpenAI Agents SDK for intelligent procurement assistance.

## Prerequisites

- Node.js and npm (for Angular frontend)
- Python 3.8+ (for backend)
- OpenAI API key

## Setup

1. Clone the repository
2. Set up the backend:

   ```bash
   # Create and activate a virtual environment (optional but recommended)
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt

   # Create a .env file with your OpenAI API key
   echo "OPENAI_API_KEY=your_api_key_here" > .env
   ```

3. Set up the frontend:
   ```bash
   cd ai-procurement
   npm install
   ```

## Running the Application

1. Start the backend server:

   ```bash
   # From the root directory
   python server.py
   ```

   The backend will run on http://localhost:8000

2. Start the frontend development server:
   ```bash
   # From the ai-procurement directory
   ng serve
   ```
   The frontend will run on http://localhost:4200

## Features

- Interactive chat interface for product specification
- AI-powered product recommendations
- JSON specification generation
- Downloadable product specifications
- Material Design UI

## Architecture

- Frontend: Angular with Angular Material
- Backend: FastAPI with OpenAI Agents SDK
- AI: OpenAI's GPT model through the Agents SDK

## API Endpoints

- POST /api/chat - Send a message to the AI assistant
- GET /api/check-api-key - Check if a valid API key is configured

## Development

The project uses:

- Angular Material for UI components
- FastAPI for the backend API
- OpenAI Agents SDK for AI functionality
- TypeScript for type safety
- SCSS for styling
