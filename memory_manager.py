import json
import sqlite3
from datetime import datetime
from config import MEMORY_FILE, DATABASE_FILE, MEMORY_DIR

def load_memory():
    if not MEMORY_FILE.exists():
        return {
            "user": {}, "assistant": {}, "facts": [],
            "preferences": [], "projects": [], "tasks": [],
            "conversation_summary": ""
        }
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print("Uyarı: memory.json okunamadı.")
        return {}

def save_memory(memory):
    MEMORY_FILE.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")

def init_database():
    connection = sqlite3.connect(DATABASE_FILE)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)
    connection.execute("CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp)")
    connection.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts
        USING fts5(content, content='conversations', content_rowid='id')
    """)
    connection.commit()
    connection.close()

def save_message(role, content):
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.execute(
        "INSERT INTO conversations (timestamp, role, content) VALUES (?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"), role, content)
    )
    message_id = cursor.lastrowid
    connection.execute(
        "INSERT INTO conversations_fts (rowid, content) VALUES (?, ?)",
        (message_id, content)
    )
    connection.commit()
    connection.close()

def search_conversations(query, limit=6):
    words = query.strip().split()
    if not words:
        return []
    
    safe_words = []
    for word in words:
        word = word.replace('"', '').strip()
        if word:
            safe_words.append(f'"{word}"')
            
    if not safe_words:
        return []
        
    search_query = " OR ".join(safe_words)
    connection = sqlite3.connect(DATABASE_FILE)
    try:
        results = connection.execute("""
            SELECT conversations.timestamp, conversations.role, conversations.content
            FROM conversations_fts
            JOIN conversations ON conversations.id = conversations_fts.rowid
            WHERE conversations_fts MATCH ?
            ORDER BY rank LIMIT ?
        """, (search_query, limit)).fetchall()
    except sqlite3.OperationalError:
        results = []
    connection.close()
    return results

def import_old_history():
    old_file = MEMORY_DIR / "conversations.jsonl"
    if not old_file.exists():
        return
        
    connection = sqlite3.connect(DATABASE_FILE)
    existing_count = connection.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    if existing_count > 0:
        connection.close()
        return
        
    print("Eski konuşma geçmişi SQLite'a aktarılıyor...")
    imported = 0
    try:
        with old_file.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line: continue
                try:
                    data = json.loads(line)
                    timestamp = data.get("time", datetime.now().isoformat(timespec="seconds"))
                    role = data.get("role", "")
                    content = data.get("content", "")
                    if not role or not content: continue
                    
                    cursor = connection.execute(
                        "INSERT INTO conversations (timestamp, role, content) VALUES (?, ?, ?)",
                        (timestamp, role, content)
                    )
                    connection.execute(
                        "INSERT INTO conversations_fts (rowid, content) VALUES (?, ?)",
                        (cursor.lastrowid, content)
                    )
                    imported += 1
                except json.JSONDecodeError:
                    continue
        connection.commit()
    finally:
        connection.close()
    print(f"{imported} mesaj SQLite'a aktarıldı.")

def build_memory_context(user_text, memory):
    relevant = search_conversations(user_text, limit=6)
    parts = []
    if memory:
        memory_text = json.dumps(memory, ensure_ascii=False, indent=2)
        parts.append("KALICI HAFIZA:\n" + memory_text)
    if relevant:
        history_lines = [f"[{timestamp}] {role}: {content}" for timestamp, role, content in relevant]
        parts.append("İLGİLİ ESKİ KONUŞMALAR:\n" + "\n".join(history_lines))
    return "\n\n".join(parts)

def auto_extract_memory(user_text, client, model_name, memory):
    system_prompt = """Sen bir bilgi çıkarma asistanısın. Sadece kullanıcının mesajını analiz et.
Eğer kullanıcı memleketi, yaşadığı yer, yaşı, hobileri veya projeleri hakkında kalıcı bir bilgi veriyorsa bunu tek bir cümleyle özetle (Örn: Kullanıcı Konya'da yaşıyor).
Eğer böyle net bir kişisel bilgi yoksa, SADECE "YOK" yaz. Başka hiçbir açıklama yapma."""
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f'Kullanıcı mesajı: "{user_text}"'}
            ],
            temperature=0.0
        )
        result = response.choices[0].message.content.strip()
        
        print(f"\n[GİZLİ LOG - Modelin Hafıza Analizi: {result}]")
        
        if "YOK" not in result.upper() and len(result) > 5:
            memory.setdefault("facts", []).append(result)
            save_memory(memory)
            print(f"[🧠 Otonom Hafıza Güncellendi: {result}]")
            
    except Exception as e:
        print(f"\n[⚠️ HAFIZA SİSTEMİ HATASI: {str(e)}]")