# Strain Search - Cannabis Research Assistant

A modern web application for cannabis strain research powered by Perplexity AI. Built with HTML/CSS frontend and Python backend, deployed on Vercel.

## Features

🌿 **Intelligent Strain Search** - AI-powered research using Perplexity's real-time web search
💬 **Conversational Interface** - Natural chat experience with context awareness  
📱 **Responsive Design** - Works perfectly on desktop and mobile devices
🔍 **Comprehensive Information** - Genetics, effects, medical uses, growing info
⚡ **Fast & Reliable** - Serverless deployment with instant responses
🎨 **Modern UI** - Clean, dark design inspired by the provided Figma mockup

## Quick Start

### 1. Clone and Setup
```bash
git clone <your-repo>
cd Strain_researcher
```

### 2. Environment Variables
You'll need a Perplexity API key. Add it to your Vercel project:

```bash
# In Vercel dashboard or CLI
vercel env add PERPLEXITY_API_KEY
```

### 3. Deploy to Vercel
```bash
vercel --prod
```

## Local Development

### Run locally with Python:
```bash
# Install dependencies
pip install -r requirements.txt

# Start a simple HTTP server for frontend
python -m http.server 8000

# For API testing, you can run the Python backend separately
python api/search.py
```

## Project Structure

```
Strain_researcher/
├── index.html          # Main frontend page
├── style.css           # Styles and responsive design
├── script.js           # Frontend JavaScript logic
├── api/
│   └── search.py       # Python backend API
├── vercel.json         # Vercel deployment configuration
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## API Usage

### POST `/api/search`
Search for strain information with conversation context.

**Request:**
```json
{
  "query": "Tell me about Blue Dream",
  "conversation_history": [
    {"role": "user", "content": "What is Blue Dream?"},
    {"role": "assistant", "content": "Blue Dream is a popular..."}
  ]
}
```

**Response:**
```json
{
  "response": "Blue Dream is a sativa-dominant hybrid...",
  "status": "success"
}
```

## Configuration

### Perplexity AI Integration
The backend uses Perplexity AI's `llama-3.1-sonar-small-128k-online` model with:
- Real-time web search from cannabis databases
- Filtered domains: Leafly, Weedmaps, AllBud, BudGenius
- Temperature: 0.2 for factual responses
- Max tokens: 1000 for comprehensive answers

### Search Optimization
- **Domain filtering** for reliable cannabis sources
- **Recent results** prioritized (last month)
- **Citation tracking** for source verification
- **Conversation context** maintained for follow-up questions

## Features in Detail

### 🎯 Smart Search
- Recognizes strain names, effects, medical conditions
- Provides comprehensive information including genetics, cannabinoids, effects
- Suggests similar strains and alternatives

### 💬 Conversational AI  
- Maintains conversation context for follow-up questions
- Natural language understanding for various query types
- Educational focus with medical disclaimers

### 🎨 Modern Interface
- Dark theme with gradient accents
- Responsive design for all devices
- Smooth animations and transitions
- Typing indicators and loading states

### 🔒 Safety & Compliance
- Educational purpose disclaimers
- Healthcare consultation recommendations
- Reliable source citations
- No promotion of illegal activities

## Deployment

### Vercel Deployment (Recommended)
1. Connect your GitHub repository to Vercel
2. Add `PERPLEXITY_API_KEY` environment variable
3. Deploy automatically on push to main branch

### Environment Variables
- `PERPLEXITY_API_KEY` - Your Perplexity AI API key (required)

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Legal Notice

This application is for educational and research purposes only. The information provided should not be used as medical advice. Always consult with healthcare professionals before using cannabis for medical purposes. Comply with local laws and regulations regarding cannabis use.

## License

MIT License - see LICENSE file for details.