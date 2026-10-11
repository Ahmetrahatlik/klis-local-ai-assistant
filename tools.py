import io
from contextlib import redirect_stdout

def execute_python_code(code):
    print("\n" + "="*50)
    print("⚠️ KLİS ŞU KODU ÇALIŞTIRMAK İSTİYOR:")
    print("-" * 50)
    print(code)
    print("=" * 50)
    
    onay = input("Bu koda izin veriyor musun? (E/H): ").strip().lower()
    
    if onay != 'e':
        return "SİSTEM MESAJI: Kullanıcı kodun çalıştırılmasını reddetti."

    # Klis'in kodunun ekran çıktısını (print) yakalamak için sanal bir alan oluşturuyoruz
    captured_output = io.StringIO()
    
    try:
        # Kodun çıktısını terminal yerine 'captured_output' değişkenine yönlendir
        with redirect_stdout(captured_output):
            exec(code, {}) # Kodu çalıştır
            
        output = captured_output.getvalue().strip()
        
        if not output:
            output = "SİSTEM MESAJI: Kod başarıyla çalıştı ancak ekrana bir şey (print) yazdırmadı."
            
        return output
        
    except Exception as e:
        return f"SİSTEM MESAJI: Kod çalışırken hata verdi: {str(e)}"