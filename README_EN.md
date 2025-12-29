# MindVoice

A cross-platform desktop voice assistant powered by AI that supports speech-to-text, voice notes, and translation features.

**Architecture**: Electron frontend + Python API backend (separated architecture for easy frontend framework replacement)

## ✨ Features

- 🎤 **Speech-to-Text** - Real-time voice recognition using third-party ASR services
- 📝 **Voice Notes** - Record and save your voice notes
- 🌐 **Multi-language Translation** - (Coming soon)
- 💾 **History Storage** - SQLite-based history storage
- 📋 **One-click Copy** - Copy recognized text with one click
- 🎯 **System Tray Icon** - Minimize to system tray
- 🔌 **Extensible Plugin Architecture** - Easy to add new ASR providers and storage backends

## 🏗️ Architecture

This project adopts a separated frontend-backend architecture:

- **Backend**: Python API server (FastAPI + WebSocket)
- **Frontend**: Electron + React + TypeScript
- **Communication**: HTTP REST API + WebSocket for real-time updates

For detailed architecture documentation, please refer to [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/ARCHITECTURE_API.md](docs/ARCHITECTURE_API.md)

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- npm or yarn

### Installation

1. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

2. **Install Electron frontend dependencies**:
```bash
cd electron-app
npm install
```

3. **Configure ASR Service** (Optional):

**Method 1: Using setup script (Recommended)**
```bash
python setup_asr.py
```

**Method 2: Manual configuration**
```bash
# Copy example configuration file
cp config.yml.example config.yml

# Edit config.yml and fill in your API credentials
nano config.yml
```

**Important**: The `config.yml` file contains sensitive information and has been added to `.gitignore`. It will not be committed to version control.

For detailed configuration instructions, please refer to [docs/CONFIG.md](docs/CONFIG.md)

4. **Run the application**:

**Method 1: Using Electron (Recommended)**
```bash
# Terminal 1: Start API server
python api_server.py

# Terminal 2: Start Electron frontend
cd electron-app
npm run dev
```

**Method 2: API server only (for development or web frontend)**
```bash
python api_server.py
# API server will run at http://127.0.0.1:8765
```

**Stop the application**:
```bash
# Using stop script (Recommended)
./stop.sh

# Or manually stop
# Press Ctrl+C to stop the process in the current terminal
# If the process is running in background, use:
# kill $(pgrep -f api_server.py)
```

## 📁 Project Structure

```
src/
├── core/              # Core modules (abstract interfaces, config, plugin management)
├── providers/         # Provider implementations (ASR, storage)
├── services/          # Service layer (business logic)
├── api/               # API service layer (FastAPI)
└── utils/             # Utility modules

electron-app/          # Electron frontend (React + TypeScript)
```

## 🔧 Development

### Adding a New ASR Provider

1. Create a new file under `src/providers/asr/`
2. Inherit from `ASRProvider` and implement all required methods
3. Load it in `src/api/server.py`: `plugin_manager.load_plugin_module('src.providers.asr.your_provider')`

### Adding a New Storage Provider

1. Create a new file under `src/providers/storage/`
2. Inherit from `StorageProvider` and implement all required methods
3. Set `storage.provider` in config to your provider name

## 📖 Usage

- After starting the application, click the system tray icon to show/hide the window
- Click "Start" button to begin voice recognition
- Click "Pause" to pause recognition
- Click "Stop" to stop and save
- Recognition results will be displayed automatically and can be copied with one click

## 📊 Development Status

Current version completed:
- ✅ Core architecture design (frontend-backend separation)
- ✅ Plugin system
- ✅ Configuration management
- ✅ Volcano Engine ASR provider integration
- ✅ Audio recorder (based on sounddevice)
- ✅ Electron frontend interface (React + TypeScript)
- ✅ API service layer (FastAPI + WebSocket)
- ✅ SQLite storage provider
- ✅ Recording control (start/pause/stop)
- ✅ Real-time text display and copy functionality
- ✅ History storage

Coming soon:
- ⏳ Translation feature
- ⏳ More ASR providers (Baidu, iFlytek, etc.)
- ⏳ History viewing interface

## 🛠️ Tech Stack

### Backend
- **Python 3.9+**
- **FastAPI**: API server framework
- **sounddevice**: Audio recording
- **aiohttp**: Async HTTP/WebSocket client
- **SQLite**: Data storage

### Frontend
- **Electron**: Cross-platform desktop application framework
- **React**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool

## 🔌 Extensibility

The project adopts a plugin-based architecture, making it easy to add:

1. **New ASR Providers**: Inherit from `ASRProvider` and implement the `recognize` method
2. **New Storage Providers**: Inherit from `StorageProvider` and implement storage interfaces
3. **New Frontend Frameworks**: Use the same API interface (HTTP/WebSocket)

## 📡 API Interface

- HTTP REST API: `http://127.0.0.1:8765/api/`
- WebSocket: `ws://127.0.0.1:8765/ws`

For detailed API documentation, please refer to [docs/ARCHITECTURE_API.md](docs/ARCHITECTURE_API.md)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework
- [Electron](https://www.electronjs.org/) - Build cross-platform desktop apps
- [React](https://react.dev/) - UI library
- [Volcano Engine](https://www.volcengine.com/) - ASR service provider

