import json
import re
import tools
from openai import OpenAI

from config import API_BASE_URL, API_KEY, MODEL_NAME, TEMPERATURE
from prompts import SYSTEM_PROMPT
import memory_manager

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=API_KEY
)

def main():
    memory_manager.init_database()
    memory_manager.import_old_history()
    memory = memory_manager.load_memory()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("\nKlis hazır! (Modüler Versiyon)")
    print("Çıkmak için: /çık | Hafıza: /hafıza | Hatırla: /hatırla bilgi | Ara: /ara kelime\n")

    while True:
        try:
            user_text = input("Sen: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nKlis kapatıldı.")
            break

        if not user_text:
            continue

        if user_text.lower() in ("/çık", "/exit", "/quit"):
            print("Klis kapatıldı.")
            break

        if user_text.startswith("/hatırla "):
            fact = user_text[len("/hatırla "):].strip()
            if fact:
                memory.setdefault("facts", []).append(fact)
                memory_manager.save_memory(memory)
                print("Klis: Hafızaya kaydettim.")
            continue

        if user_text == "/hafıza":
            print(json.dumps(memory, ensure_ascii=False, indent=2))
            continue

        if user_text.startswith("/unut "):
            fact = user_text[len("/unut "):].strip()
            facts = memory.get("facts", [])
            if fact in facts:
                facts.remove(fact)
                memory_manager.save_memory(memory)
                print("Klis: Hafızadan sildim.")
            else:
                print("Klis: Bu bilgi hafızada bulunamadı.")
            continue

        if user_text.startswith("/ara "):
            query = user_text[len("/ara "):].strip()
            results = memory_manager.search_conversations(query, limit=10)
            if not results:
                print("Klis: Bu konuyla ilgili geçmiş konuşma bulamadım.")
            else:
                print(f"\n{len(results)} sonuç bulundu:\n")
                for timestamp, role, content in results:
                    print(f"[{timestamp}] {role}:\n{content}\n" + "-" * 60)
            continue

        # =========================
        # NORMAL MESAJ İŞLEME
        # =========================
        
        # 1. Otonom Hafıza Analizi
        memory_manager.auto_extract_memory(user_text, client, MODEL_NAME, memory)

        # 2. Kullanıcının mesajını kaydet
        memory_manager.save_message("user", user_text)
        
        # 3. İlgili hafızayı getir
        memory_context = memory_manager.build_memory_context(user_text, memory)

        # 4. Sistem mesajını birleştir
        final_system_content = SYSTEM_PROMPT
        if memory_context:
            final_system_content += "\n\n" + memory_context

        current_messages = [{"role": "system", "content": final_system_content}]
        current_messages.extend(messages[1:])
        current_messages.append({"role": "user", "content": user_text})

        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=current_messages,
                temperature=TEMPERATURE
            )
            answer = response.choices[0].message.content or ""
            print(f"\nKlis: {answer}\n")

            memory_manager.save_message("assistant", answer)
            messages.append({"role": "assistant", "content": answer})

            # =========================
            # ARAÇ KULLANIMI (TOOL CALLING)
            # =========================
            if "<run_python>" in answer and "</run_python>" in answer:
                match = re.search(r"<run_python>(.*?)</run_python>", answer, re.DOTALL)
                
                if match:
                    code_to_run = match.group(1).strip()
                    
                    result = tools.execute_python_code(code_to_run)
                    print(f"\n[Sistem] Klis'e iletilen çıktı:\n{result}\n")
                    
                    tool_feedback = f"Çalıştırılan kodun sistem çıktısı:\n{result}\nBu bilgiye göre bana nihai cevabı ver."
                    
                    messages.append({"role": "user", "content": tool_feedback})
                    memory_manager.save_message("user", tool_feedback)
                    
                    response2 = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=messages,
                        temperature=TEMPERATURE
                    )
                    
                    final_answer = response2.choices[0].message.content or ""
                    print(f"Klis: {final_answer}\n")
                    
                    memory_manager.save_message("assistant", final_answer)
                    messages.append({"role": "assistant", "content": final_answer})

            # Çok büyümesini engelle
            if len(messages) > 24:
                messages = [messages[0]] + messages[-23:]

        except Exception as error:
            print("\nBağlantı hatası:", error)
            print("LM Studio REST Server'ın çalıştığını kontrol et.\n")

if __name__ == "__main__":
    main()