import os
import ssl
import PyPDF2
import openai
import requests
from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

# === Desactiva SSL si estás en red con certificado autofirmado ===
class UnsafeAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

# Configuración de sesión para certificados autofirmados
session = requests.Session()
session.mount("https://", UnsafeAdapter())
openai.requestssession = session

# Clave de API de OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Inicializar Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Función para extraer texto de páginas específicas del PDF
def extract_text_from_pdf(pdf_path, page_indices):
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for i in page_indices:
            if 0 <= i < len(reader.pages):
                print(f"[INFO] Extrayendo texto de la página {i + 1}")
                page = reader.pages[i]
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    return text

# Ruta principal
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para procesar el PDF
@app.route('/process', methods=['POST'])
def process():
    file = request.files['pdf']
    start = int(request.form['start'])
    end = int(request.form['end'])
    step = int(request.form['step'])
    initial_prompt = request.form['prompt'].strip()

    # Asegurar que el directorio de uploads existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Guardar archivo subido de forma segura
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    print(f"[INFO] PDF recibido: {filename}")
    print(f"[INFO] Rango de páginas: {start} a {end}")
    print(f"[INFO] Particionando de a {step} páginas")

    page_ranges = [list(range(i, min(i + step, end + 1))) for i in range(start, end + 1, step)]
    full_apunte = ""
    messages = [{"role": "user", "content": initial_prompt}]

    for idx, page_range in enumerate(page_ranges):
        print(f"\n[INFO] Procesando partición {idx + 1} con páginas: {page_range}")
        pages_text = extract_text_from_pdf(filepath, [p - 1 for p in page_range])
        pages_text = pages_text.encode('utf-8', errors='ignore').decode('utf-8').strip()

        if idx == 0:
            prompt = f"A continuación se presenta el primer fragmento del texto:\n\n{pages_text}"
        else:
            prompt = f"Continuá el apunte agregando y desarrollando este nuevo fragmento de texto:\n\n{pages_text}"

        messages.append({"role": "user", "content": prompt})
        print(f"[INFO] Enviando partición {idx + 1} a OpenAI...")

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0.7
            )
            new_content = response['choices'][0]['message']['content'].strip()
            print(f"[INFO] Respuesta recibida de OpenAI para partición {idx + 1}")

            full_apunte += f"\n{new_content}\n"
            messages.append({"role": "assistant", "content": new_content})

        except openai.error.OpenAIError as e:
            print(f"[ERROR] OpenAI API: {str(e)}")
            return jsonify({"error": f"Error al procesar con OpenAI: {str(e)}"}), 500

    print("\n✅ Apunte completo generado.")
    return jsonify({"apunte": full_apunte.strip()})

# Ejecutar el servidor
if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    print("[INFO] Servidor iniciado en http://127.0.0.1:5000")
    app.run(debug=True)
