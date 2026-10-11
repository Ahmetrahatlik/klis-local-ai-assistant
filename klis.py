import json
import sqlite3
from pathlib import Path
from datetime import datetime
from openai import OpenAI

# =========================
# DOSYA YOLLARI
# =========================

BASE_DIR = Path(__file__).resolve().parent
MEMORY_DIR = BASE_DIR / "memory"

MEMORY_FILE = MEMORY_DIR / "memory.json"
DATABASE_FILE = MEMORY_DIR / "klis_memory.db"

MEMORY_DIR.mkdir(parents=True, exist_ok=True)


# =========================
# LM STUDIO
# =========================

client = OpenAI(
    base_url="http://localhost:1235/v1",
    api_key="lm-studio"
)

MODEL_NAME = "qwen3.6@iq4_nl"


# =========================
# SİSTEM PROMPT
# =========================

SYSTEM_PROMPT = """
Sen Klis'sin.

Kullanıcıyla doğal, samimi ve akıcı Türkçe konuş.

Kurallar:
- Basit sorulara kısa ve doğrudan cevap ver.
- Gereksiz selamlaşma, tekrar ve yapay resmiyetten kaçın.
- Karmaşık görevleri adım adım çöz.
- Kod istenirse eksiksiz ve çalıştırılabilir kod ver.
- Bilmediğin bir şeyi biliyormuş gibi yapma.
- Sana verilen geçmiş konuşma bilgilerini dikkate al.
- Geçmiş konuşmalardan gelen bilgilerin güncel olmayabileceğini unutma.
"""


# =========================
# HAFIZA JSON
# =========================

def load_memory():
    if not MEMORY_FILE.exists():
        return {
            "user": {},
            "assistant": {},
            "facts": [],
            "preferences": [],
            "projects": [],
            "tasks": [],
            "conversation_summary": ""
        }

    try:
        return json.loads(
            MEMORY_FILE.read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, OSError):
        print("Uyarı: memory.json okunamadı.")
        return {}


def save_memory(memory):
    MEMORY_FILE.write_text(
        json.dumps(
            memory,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


# =========================
# SQLITE
# =========================

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

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_timestamp
        ON conversations(timestamp)
    """)

    connection.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts
        USING fts5(
            content,
            content='conversations',
            content_rowid='id'
        )
    """)

    connection.commit()
    connection.close()


def save_message(role, content):
    connection = sqlite3.connect(DATABASE_FILE)

    cursor = connection.execute(
        """
        INSERT INTO conversations
        (timestamp, role, content)
        VALUES (?, ?, ?)
        """,
        (
            datetime.now().isoformat(timespec="seconds"),
            role,
            content
        )
    )

    message_id = cursor.lastrowid

    connection.execute(
        """
        INSERT INTO conversations_fts
        (rowid, content)
        VALUES (?, ?)
        """,
        (
            message_id,
            content
        )
    )

    connection.commit()
    connection.close()


def search_conversations(query, limit=6):
    """
    Eski konuşmalarda ilgili kelimeleri arar.
    """

    words = query.strip().split()

    if not words:
        return []

    # SQLite FTS5 için güvenli arama
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
        results = connection.execute(
            """
            SELECT
                conversations.timestamp,
                conversations.role,
                conversations.content
            FROM conversations_fts
            JOIN conversations
                ON conversations.id = conversations_fts.rowid
            WHERE conversations_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (
                search_query,
                limit
            )
        ).fetchall()

    except sqlite3.OperationalError:
        results = []

    connection.close()

    return results


# =========================
# ESKİ JSONL'Yİ AKTAR
# =========================

def import_old_history():
    old_file = MEMORY_DIR / "conversations.jsonl"

    if not old_file.exists():
        return

    connection = sqlite3.connect(DATABASE_FILE)

    existing_count = connection.execute(
        "SELECT COUNT(*) FROM conversations"
    ).fetchone()[0]

    if existing_count > 0:
        connection.close()
        return

    print("Eski konuşma geçmişi SQLite'a aktarılıyor...")

    imported = 0

    try:
        with old_file.open(
            "r",
            encoding="utf-8"
        ) as file:

            for line in file:
                line = line.strip()

                if not line:
                    continue

                try:
                    data = json.loads(line)

                    timestamp = data.get(
                        "time",
                        datetime.now().isoformat(
                            timespec="seconds"
                        )
                    )

                    role = data.get("role", "")
                    content = data.get("content", "")

                    if not role or not content:
                        continue

                    cursor = connection.execute(
                        """
                        INSERT INTO conversations
                        (timestamp, role, content)
                        VALUES (?, ?, ?)
                        """,
                        (
                            timestamp,
                            role,
                            content
                        )
                    )

                    message_id = cursor.lastrowid

                    connection.execute(
                        """
                        INSERT INTO conversations_fts
                        (rowid, content)
                        VALUES (?, ?)
                        """,
                        (
                            message_id,
                            content
                        )
                    )

                    imported += 1

                except json.JSONDecodeError:
                    continue

        connection.commit()

    finally:
        connection.close()

    print(f"{imported} mesaj SQLite'a aktarıldı.")


# =========================
# GEÇMİŞİ MODELE HAZIRLA
# =========================

def build_memory_context(user_text, memory):
    relevant = search_conversations(
        user_text,
        limit=6
    )

    parts = []

    # Kalıcı bilgiler
    if memory:
        memory_text = json.dumps(
            memory,
            ensure_ascii=False,
            indent=2
        )

        parts.append(
            "KALICI HAFIZA:\n" +
            memory_text
        )

    # Eski konuşmalar
    if relevant:
        history_lines = []

        for timestamp, role, content in relevant:
            history_lines.append(
                f"[{timestamp}] {role}: {content}"
            )

        parts.append(
            "İLGİLİ ESKİ KONUŞMALAR:\n" +
            "\n".join(history_lines)
        )

    return "\n\n".join(parts)


# =========================
# ANA PROGRAM
# =========================

def main():

    init_database()

    import_old_history()

    memory = load_memory()

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    print("\nKlis hazır!")
    print("Çıkmak için: /çık")
    print("Hafızayı görmek için: /hafıza")
    print("Bilgi kaydetmek için: /hatırla bilgi")
    print("Geçmişte arama yapmak için: /ara kelime\n")

    while True:

        try:
            user_text = input("Sen: ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\nKlis kapatıldı.")
            break

        if not user_text:
            continue


        # =========================
        # ÇIKIŞ
        # =========================

        if user_text.lower() in (
            "/çık",
            "/exit",
            "/quit"
        ):
            print("Klis kapatıldı.")
            break


        # =========================
        # MANUEL HAFIZA
        # =========================

        if user_text.startswith("/hatırla "):

            fact = user_text[
                len("/hatırla "):
            ].strip()

            if fact:

                memory.setdefault(
                    "facts",
                    []
                ).append(fact)

                save_memory(memory)

                print(
                    "Klis: Hafızaya kaydettim."
                )

            continue


        # =========================
        # HAFIZAYI GÖR
        # =========================

        if user_text == "/hafıza":

            print(
                json.dumps(
                    memory,
                    ensure_ascii=False,
                    indent=2
                )
            )

            continue


        # =========================
        # MANUEL SİLME
        # =========================

        if user_text.startswith("/unut "):

            fact = user_text[
                len("/unut "):
            ].strip()

            facts = memory.get(
                "facts",
                []
            )

            if fact in facts:

                facts.remove(fact)

                save_memory(memory)

                print(
                    "Klis: Hafızadan sildim."
                )

            else:

                print(
                    "Klis: Bu bilgi hafızada bulunamadı."
                )

            continue


        # =========================
        # GEÇMİŞTE ARAMA
        # =========================

        if user_text.startswith("/ara "):

            query = user_text[
                len("/ara "):
            ].strip()

            results = search_conversations(
                query,
                limit=10
            )

            if not results:

                print(
                    "Klis: Bu konuyla ilgili "
                    "geçmiş konuşma bulamadım."
                )

            else:

                print(
                    f"\n{len(results)} sonuç bulundu:\n"
                )

                for timestamp, role, content in results:

                    print(
                        f"[{timestamp}] {role}:"
                    )

                    print(content)
                    print("-" * 60)

            continue


        # =========================
        # İLGİLİ GEÇMİŞİ BUL
        # =========================

        memory_context = build_memory_context(
            user_text,
            memory
        )

        current_messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]

        if memory_context:

            current_messages.append(
                {
                    "role": "system",
                    "content": memory_context
                }
            )


        # Mevcut oturum bağlamı
        current_messages.extend(
            messages[1:]
        )

        current_messages.append(
            {
                "role": "user",
                "content": user_text
            }
        )


        # =========================
        # KULLANICI MESAJINI KAYDET
        # =========================

        save_message(
            "user",
            user_text
        )


        # =========================
        # MODELE GÖNDER
        # =========================

        try:

            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=current_messages,
                temperature=0.7
            )

            answer = (
                response.choices[0]
                .message
                .content
                or ""
            )

            print(
                f"\nKlis: {answer}\n"
            )


            # =========================
            # CEVABI KAYDET
            # =========================

            save_message(
                "assistant",
                answer
            )


            # Oturum hafızasına ekle
            messages.append(
                {
                    "role": "user",
                    "content": user_text
                }
            )

            messages.append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )


            # Çok büyümesini engelle
            if len(messages) > 24:

                messages = (
                    [messages[0]]
                    + messages[-23:]
                )


        except Exception as error:

            print(
                "\nBağlantı hatası:",
                error
            )

            print(
                "LM Studio REST Server'ın "
                "çalıştığını kontrol et.\n"
            )


if __name__ == "__main__":
    main()