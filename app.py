import os
from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
import PyPDF2
import openai

# ← PONÉ TU CLAVE ACÁ
openai.api_key = "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"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    file = request.files['pdf']
    start = int(request.form['start'])
    end = int(request.form['end'])
    step = int(request.form['step'])
    initial_prompt = request.form['prompt']
    initial_prompt = initial_prompt.encode('utf-8', errors='ignore').decode('utf-8')

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    print(f"[INFO] PDF recibido: {filename}")
    print(f"[INFO] Rango de páginas: {start} a {end}")
    print(f"[INFO] Particionando de a {step} páginas")

    page_ranges = [list(range(i, min(i + step, end + 1))) for i in range(start, end + 1, step)]
    full_apunte = ""

    for idx, page_range in enumerate(page_ranges):
        print(f"\n[INFO] Procesando partición {idx + 1} con páginas: {page_range}")
        pages_text = extract_text_from_pdf(filepath, [p - 1 for p in page_range])
        pages_text = pages_text.encode('utf-8', errors='ignore').decode('utf-8')

        if idx == 0:
            messages = [
                {"role": "user", "content": initial_prompt},
                {"role": "user", "content": f"Texto de estudio:\n{pages_text}"}
            ]
        else:
            messages = [
                {"role": "user", "content": f"Continúa el apunte con el siguiente fragmento de texto del PDF:\n{pages_text}"}
            ]

        print(f"[INFO] Enviando partición {idx + 1} a OpenAI...")
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages
        )
        new_content = response['choices'][0]['message']['content']
        print(f"[INFO] Respuesta recibida de OpenAI para partición {idx + 1}")
        full_apunte += f"\n\n---\n\n{new_content}"

    print("\n✅ Apunte completo generado.")
    return jsonify({"apunte": full_apunte.strip()})

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    print("[INFO] Servidor iniciado en http://127.0.0.1:5000")
    app.run(debug=True)
