# DeVitalik

An AI agent for blockchain and development insights, built on top of ZerePy.

## Features

- Advanced social media monitoring and analysis
- Market context integration
- Sentiment analysis for crypto and tech discussions
- Automated content generation
- Influencer tracking
- Multi-platform support (Twitter, Farcaster)

## Installation

```bash
# Install with pip
pip install git+https://github.com/Experimenting-w-building/DeVitalik.git

# Or install with Poetry
poetry add git+https://github.com/Experimenting-w-building/DeVitalik.git
```

## Configuration

Create a `.env` file with your API keys:

```env
TWITTER_API_KEY=your_twitter_api_key
```

## Usage

### As a Library

```python
from devitalik import DeVitalikAgent

# Initialize the agent
agent = DeVitalikAgent()

# Analyze context
context = {
    "id": "analysis_1",
    "type": "market_analysis",
    "tokens": ["$SOL", "$ETH"]
}
results = await agent.analyze_context(context)

# Get interaction history
history = await agent.get_interaction_history("analysis_1")
```

### Command Line

```bash
# Show version
devitalik --version

# Analyze context from JSON file
devitalik analyze context.json

# Analyze context from string
devitalik analyze '{"id": "test", "type": "market_analysis"}'

# Get interaction history
devitalik history analysis_1

# Enable verbose logging
devitalik -v analyze context.json

# Use custom config file
devitalik -c config.json analyze context.json
```

## Development

```bash
# Clone the repository
git clone https://github.com/Experimenting-w-building/DeVitalik.git
cd DeVitalik

# Install dependencies
poetry install

# Run tests
poetry run pytest

# Format code
poetry run black .
poetry run isort .

# Type checking
poetry run mypy .
```

## Project Structure

```
devitalik/
├── devitalik/
│   ├── __init__.py
│   ├── agent.py
│   ├── cli.py
│   └── version.py
├── social_enhancement/
│   ├── __init__.py
│   ├── social_manager.py
│   ├── analyzers/
│   ├── connections/
│   ├── processors/
│   └── config/
├── tests/
├── pyproject.toml
└── README.md
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Social Enhancements Quick Start

Using the social enhancement features is straightforward with the standard installation. If you run into any issues:

1. Make sure you have your Twitter API key in `.env`:
```
TWITTER_API_KEY=your_key_here
```
Note: DexScreener API doesn't require an API key (rate limited to 300 requests/minute)

2. For sentiment analysis, you might need to download NLTK data:
```python
import nltk
nltk.download('vader_lexicon')
```

That's it! Everything else is handled by the Poetry installation.
