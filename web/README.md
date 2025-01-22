# DeVitalik Web Integration

This directory contains everything needed to integrate DeVitalik's thought stream into your website.

## Quick Start

1. Include the required files:
```html
<link rel="stylesheet" href="css/devitalik-stream.css">
<script src="js/devitalik-stream.js"></script>
```

2. Add the container to your HTML:
```html
<div id="devitalik-thoughts" class="devitalik-stream"></div>
```

3. Initialize the stream:
```javascript
const devitalikStream = new DeVitalikStream('devitalik-thoughts', {
    maxEntries: 50,
    autoScroll: true,
    showTimestamp: true
});
```

## Configuration Options

```javascript
{
    maxEntries: 50,      // Maximum number of entries to show
    autoScroll: true,    // Automatically scroll to new entries
    showTimestamp: true, // Show timestamp on entries
    theme: 'light'       // 'light' or 'dark'
}
```

## Data Structure

Each thought entry follows this structure:
```javascript
{
    "timestamp": "2024-03-15T14:30:00Z",
    "type": "analyzing",  // thinking, analyzing, deciding, action, success, error
    "emoji": "🔍",
    "content": "Analyzing tweet from @VitalikButerin about L2 scaling",
    "data": {
        "tweet_id": "12345678901234",
        "sentiment_score": 0.85,
        "technical_depth": 0.9,
        "engagement_potential": 0.75,
        "metrics": {
            "likes": 150,
            "retweets": 45,
            "replies": 23
        }
    }
}
```

## Connection Details

- WebSocket: `ws://your-server:8765/devitalik/stream`
- SSE Endpoint: `/devitalik/events`

## Examples

Check the `examples` directory for complete implementation examples. 