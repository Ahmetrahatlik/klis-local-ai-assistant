# Klis – Local AI Assistant

Klis, Python ve LM Studio kullanılarak geliştirilen yerel bir yapay zeka asistanıdır.

Klis; yerel LLM entegrasyonu, kalıcı hafıza, SQLite tabanlı konuşma geçmişi ve modüler araç yapısını bir araya getiren kişisel bir AI assistant projesidir.

## Features

- Local LLM integration
- OpenAI-compatible API
- Persistent memory
- SQLite conversation history
- SQLite FTS5 full-text search
- Context-aware conversations
- Manual and automatic memory management
- Modular tool architecture
- Configurable model and application settings
- Local-first architecture

## Tech Stack

- Python
- LM Studio
- OpenAI-compatible API
- SQLite
- SQLite FTS5
- JSON
- Git / GitHub

## Architecture

Klis, internet tabanlı bir yapay zeka servisine bağlı kalmadan yerel bir LLM ile çalışacak şekilde tasarlanmıştır.

Proje, farklı sorumlulukları ayrı modüllere ayıran modüler bir mimari kullanır:

```text
Klis/
├── main.py
├── klis.py
├── config.py
├── prompts.py
├── memory_manager.py
├── tools.py
├── requirements.txt
├── README.md
├── memory/
└── models/