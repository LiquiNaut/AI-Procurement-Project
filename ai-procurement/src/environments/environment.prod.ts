export const environment = {
  production: true,
  openai: {
    apiKey: 'YOUR_OPENAI_API_KEY', // Replace with your actual OpenAI API key for production
    apiUrl: 'https://api.openai.com/v1/chat/completions',
    model: 'gpt-3.5-turbo', // You can change this to 'gpt-4' if you have access
  },
};
