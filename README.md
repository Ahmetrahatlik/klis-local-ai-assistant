# Klis - Local AI Assistant

Klis is a privacy-first local AI assistant built with Python and a local LLM served through an OpenAI-compatible API.

The project focuses on persistent memory, contextual conversations, modular architecture, and local tool execution without relying on cloud-based AI services for its core functionality.

## Features

* Persistent conversation memory
* SQLite FTS5 full-text search
* Context-aware conversations
* Local LLM integration
* OpenAI-compatible API support
* Modular tool-calling architecture
* Python script generation and execution
* Automatic and manual memory management
* Configurable application and model settings
* Local-first architecture

## Tech Stack

* Python
* LM Studio
* OpenAI-compatible API
* SQLite
* SQLite FTS5
* JSON
* Git / GitHub

## Architecture

Klis uses a modular architecture where different responsibilities are separated into dedicated components.

```text
Klis/
├── main.py
├── klis.py
├── config.py
├── prompts.py
├── memory_manager.py
├── tools.py
├── memory/
├── models/
├── requirements.txt
└── README.md
```

### Core Components

* `main.py` - Application entry point
* `klis.py` - Core assistant logic
* `memory_manager.py` - Persistent memory and conversation retrieval
* `tools.py` - Local tool execution and tool-calling functionality
* `prompts.py` - System and assistant prompts
* `config.py` - Application and model configuration

## Memory System

Klis uses SQLite to store conversation history and persistent memory.

SQLite FTS5 is used for full-text search, allowing relevant previous conversations and stored information to be retrieved when needed.

The memory system supports both automatic and manual memory management.

## Tool Calling

Klis uses a modular tool architecture that allows the local LLM to interact with local functionality.

One of the available capabilities is generating and executing Python scripts inside an isolated virtual environment.

## Local-First Design

Klis is designed to run primarily on the user's local machine.

The LLM is served locally through an OpenAI-compatible API, keeping the core conversation and memory workflow independent from cloud-based AI services.

## Project Status

Klis is an actively developed personal AI assistant project focused on local LLM integration, persistent memory, modular architecture, and practical automation.

## Author

Ahmet Zülkarneyn Rahatlık

GitHub: https://github.com/Ahmetrahatlik
