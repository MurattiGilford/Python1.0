# Quantum AI Lab - Nuclear Spaceship Edition v5.1

A comprehensive AI-powered backend application with multi-provider support, file generation, chat history management, and media generation capabilities.

## Features

### Core Capabilities
- **Multi-Provider AI Chat**: Support for GLM-4.5-Flash, GLM-4.6, Kimi K2, and more
- **Media Generation**: Image generation (CogView-4) and video generation (CogVideoX-3)
- **File Processing**: Upload and process DOCX, PDF, XLSX, PPTX, TXT, CSV, images, and videos
- **File Export**: Generate DOCX, PDF, XLSX, PPTX files from chat content
- **Session-based Chat History**: Organized conversations with sidebar display
- **Research Tools**: arXiv search, PubMed search, Semantic Scholar
- **Dynamic Data**: News headlines, weather, crypto prices, exchange rates
- **Code Execution**: Safe Python code execution in sandboxed environment
- **Fact Checking**: Built-in fact guard with pre-validated responses
- **Cost Tracking**: Accurate API usage cost monitoring

### Bug Fixes in v5.1
✅ **Fixed missing `io` import** - File generation now works properly
✅ **Fixed file generation for all formats** - DOCX, XLSX, PPTX, PDF fully functional
✅ **Fixed file upload preview** - Files no longer auto-preview in reader panel
✅ **Fixed chat history** - Session-based management for sidebar display
✅ **Fixed chat deletion** - Proper session deletion functionality
✅ **Improved error handling** - Better graceful degradation when libraries are missing

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Python1.0
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API keys**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env and add your API keys
   ```

4. **Run the application**
   ```bash
   cd backend
   python app.py
   ```

5. **Access the API**
   - Server: http://127.0.0.1:7861
   - Health check: http://127.0.0.1:7861/health
   - API docs: http://127.0.0.1:7861/docs

## API Endpoints

### Chat & AI

#### POST /chat
Main chat endpoint with conversation context
```json
{
  "task": "Your question or request",
  "temperature": 0.4,
  "max_tokens": 4096,
  "provider": "zai-glm-4.5-flash",
  "session_id": "session_123"
}
```

#### GET /providers
Get list of available AI providers

#### GET /cost
Get total API usage cost

### File Management

#### POST /files/upload
Upload files (DOCX, PDF, XLSX, PPTX, images, videos, etc.)
- Returns minimal info to prevent auto-preview
- Files stored in `data/uploads/`

#### POST /generate/file
Generate various file types
```json
{
  "content": "Your content here",
  "type": "docx",  // docx, xlsx, pptx, pdf, txt, csv
  "filename": "generated_document.docx"
}
```

#### POST /files/export/pdf
Export text as PDF

#### POST /files/export/docx
Export text as DOCX

#### POST /files/export/xlsx
Export data as Excel

#### GET /files/download/{filename}
Download generated files

### Media Generation

#### POST /generate/image
Generate images with CogView-4
```json
{
  "prompt": "A beautiful sunset over mountains",
  "size": "1024x1024"
}
```

#### POST /generate/video
Generate videos with CogVideoX-3
```json
{
  "prompt": "A cat playing with a ball",
  "duration": 5
}
```

### Chat History (Session-based)

#### GET /chats/sessions
Get list of chat sessions for sidebar
```json
{
  "ok": true,
  "sessions": [
    {
      "session_id": "session_123",
      "last_message_ts": 1234567890.0,
      "message_count": 10,
      "preview": "What is the speed of light?..."
    }
  ]
}
```

#### GET /chats/history?session_id=session_123
Get chat history for specific session

#### DELETE /chats/delete/{session_id}
Delete a specific chat session

#### DELETE /chats/clear
Clear all chat history

### Research & Tools

#### POST /research/literature
Search arXiv for academic papers
```json
{
  "query": "machine learning",
  "max_results": 10
}
```

#### POST /run/python
Execute Python code safely
```json
{
  "code": "print('Hello World')",
  "timeout_sec": 8
}
```

## Providers

| Provider | Model | Type | Cost/1K tokens |
|----------|-------|------|----------------|
| zai-glm-4.5-flash | glm-4.5-flash | Chat | FREE |
| zai-glm-4.6 | glm-4.6 | Chat | $0.01 |
| zai-glm-4.5v | glm-4.5v | Vision | $0.001 |
| kimi-k2-0905-preview | kimi-k2-0905-preview | Chat | $0.002 |
| kimi-k2-turbo-preview | kimi-k2-turbo-preview | Chat | $0.0013 |
| zai-cogview-4 | cogview-4-250304 | Image | Per image |
| zai-cogvideox-3 | CogVideoX-3 | Video | Per video |

## Project Structure

```
Python1.0/
├── backend/
│   ├── app.py                      # Main FastAPI application (FIXED)
│   ├── chat_storage.py             # Session-based chat history (NEW)
│   ├── document_handler.py         # File operations (IMPROVED)
│   ├── fact_guard.py               # Fact checking system
│   ├── research_apis.py            # Academic paper search
│   ├── dynamic_fact_fetcher.py     # Real-time data fetching
│   ├── .env.example                # Environment variables template
│   └── .env                        # Your API keys (create this)
├── data/
│   ├── uploads/                    # Uploaded files
│   ├── outputs/                    # Generated files
│   └── chats/                      # Chat history database
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Usage Examples

### Generate a DOCX file
```bash
curl -X POST http://127.0.0.1:7861/generate/file \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This is my document content with multiple paragraphs.",
    "type": "docx",
    "filename": "my_document.docx"
  }'
```

### Generate an Excel file
```bash
curl -X POST http://127.0.0.1:7861/generate/file \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Header1,Header2,Header3\nValue1,Value2,Value3\nData1,Data2,Data3",
    "type": "xlsx",
    "filename": "my_spreadsheet.xlsx"
  }'
```

### Chat with AI
```bash
curl -X POST http://127.0.0.1:7861/chat \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Explain quantum computing in simple terms",
    "provider": "zai-glm-4.5-flash",
    "session_id": "session_001"
  }'
```

### Generate an image
```bash
curl -X POST http://127.0.0.1:7861/generate/image \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A futuristic spaceship in deep space",
    "size": "1024x1024"
  }'
```

### Search academic papers
```bash
curl -X POST http://127.0.0.1:7861/research/literature \
  -H "Content-Type: application/json" \
  -d '{
    "query": "neural networks deep learning",
    "max_results": 5
  }'
```

## Configuration

### Required API Keys
- **ZAI_API_KEY**: For GLM models and media generation
- **MOONSHOT_API_KEY**: For Kimi models

### Optional API Keys
- **NEWS_API_KEY**: For real-time news (will use mock data if not set)
- **OPENWEATHER_API_KEY**: For weather data (will use mock data if not set)
- **STOCK_API_KEY**: For stock quotes (will use mock data if not set)

## Chat History Management

The application now features **session-based chat history**:

1. **Automatic Sessions**: Each chat interaction is assigned a session ID
2. **Sidebar Display**: Sessions appear in left sidebar with preview
3. **Individual Deletion**: Delete specific sessions without affecting others
4. **Persistent Storage**: SQLite database preserves history across restarts
5. **Session Info**: View message count, timestamps, and conversation previews

## File Upload Behavior

**FIXED**: Files no longer auto-preview in reader panel!

When you upload a file:
- File is stored in `data/uploads/`
- Returns minimal metadata (filename, size)
- No preview content sent to frontend
- Use separate endpoint to extract/analyze file content if needed

## Error Handling

The application gracefully handles missing optional libraries:
- If `python-docx` is missing, DOCX export falls back to TXT
- If `reportlab` is missing, PDF export falls back to TXT
- If `openpyxl` is missing, XLSX export falls back to CSV
- If `python-pptx` is missing, PPTX export falls back to TXT

All dependencies are listed in `requirements.txt` for full functionality.

## Development

### Running in development mode
```bash
cd backend
python app.py
```

### Running with auto-reload
```bash
cd backend
uvicorn app:app --host 127.0.0.1 --port 7861 --reload
```

### Testing
```bash
# Health check
curl http://127.0.0.1:7861/health

# List providers
curl http://127.0.0.1:7861/providers

# Get chat sessions
curl http://127.0.0.1:7861/chats/sessions
```

## Troubleshooting

### Import errors
Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### API key errors
Check that your `.env` file has the correct API keys:
```bash
cat backend/.env
```

### File generation fails
Ensure all optional libraries are installed:
```bash
pip install python-docx PyPDF2 openpyxl python-pptx reportlab
```

### Chat history not working
The SQLite database is created automatically. Check permissions:
```bash
ls -la data/chats/
```

## License

This project is provided as-is for educational and development purposes.

## Support

For issues, feature requests, or questions:
1. Check the API documentation at http://127.0.0.1:7861/docs
2. Review the error logs in the console
3. Verify your API keys are correctly configured

## Version History

- **v5.1.0**: Bug fixes for file generation, chat history, and upload behavior
- **v5.0.0**: Multi-provider support with manual selection
- **v4.0.0**: Added media generation capabilities
- **v3.0.0**: Research and fact-checking features
- **v2.0.0**: File processing support
- **v1.0.0**: Initial release
