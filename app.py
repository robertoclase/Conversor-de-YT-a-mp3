import os
import re
import yt_dlp
from flask import Flask, render_template_string, request, send_file, jsonify

app = Flask(__name__)

# Carpeta donde se guardarán los MP3
DOWNLOAD_FOLDER = "descargas"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ---------------- HTML + CSS + JavaScript de la página ----------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>YouTube a MP3</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        body { transition: background 0.3s; }
        .dark body { background-color: #0f172a; color: #e2e8f0; }
        .dark .card { background-color: #1e293b; }
        .card { transition: transform 0.2s; }
        .card:hover { transform: translateY(-5px); }
        #progress-bar { transition: width 0.3s ease; }
    </style>
</head>
<body class="bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
    <div class="container mx-auto px-4 py-12 max-w-2xl">
        <div class="flex justify-between items-center mb-8">
            <h1 class="text-4xl font-bold bg-gradient-to-r from-red-500 to-purple-600 bg-clip-text text-transparent">
                <i class="fab fa-youtube text-red-600 mr-2"></i> YouTube → MP3
            </h1>
            <button id="theme-toggle" class="p-2 rounded-full bg-gray-200 dark:bg-gray-700">
                <i id="theme-icon" class="fas fa-moon"></i>
            </button>
        </div>

        <div class="card bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6 mb-8">
            <label class="block text-sm font-medium mb-2">URL del vídeo de YouTube</label>
            <div class="flex flex-col sm:flex-row gap-3">
                <input type="text" id="url" placeholder="https://youtu.be/... o https://www.youtube.com/watch?v=..." 
                       class="flex-1 p-3 border rounded-lg dark:bg-gray-700 dark:border-gray-600 focus:ring-2 focus:ring-red-500">
                <button id="download-btn" class="bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-6 rounded-lg flex items-center justify-center gap-2">
                    <i class="fas fa-download"></i> Descargar MP3
                </button>
            </div>

            <div id="progress-container" class="hidden mt-4">
                <div class="flex justify-between text-sm mb-1">
                    <span><i class="fas fa-spinner fa-spin"></i> Procesando...</span>
                    <span id="progress-percent">0%</span>
                </div>
                <div class="w-full bg-gray-300 rounded-full h-2.5 dark:bg-gray-600">
                    <div id="progress-bar" class="bg-red-600 h-2.5 rounded-full" style="width:0%"></div>
                </div>
            </div>

            <div id="message" class="mt-4 text-center text-sm"></div>
        </div>

        <footer class="text-center text-sm text-gray-500">
            <i class="fas fa-headphones"></i> Tu propio conversor local
        </footer>
    </div>

    <script>
        // Tema oscuro/claro
        const html = document.documentElement;
        const toggle = document.getElementById('theme-toggle');
        const icon = document.getElementById('theme-icon');
        const isDark = localStorage.getItem('theme') === 'dark' || (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
        if (isDark) html.classList.add('dark');
        else html.classList.remove('dark');
        function updateIcon() { icon.className = html.classList.contains('dark') ? 'fas fa-sun' : 'fas fa-moon'; }
        updateIcon();
        toggle.onclick = () => {
            html.classList.toggle('dark');
            localStorage.setItem('theme', html.classList.contains('dark') ? 'dark' : 'light');
            updateIcon();
        };

        // Lógica de descarga
        const downloadBtn = document.getElementById('download-btn');
        const urlInput = document.getElementById('url');
        const progressContainer = document.getElementById('progress-container');
        const progressBar = document.getElementById('progress-bar');
        const progressPercent = document.getElementById('progress-percent');
        const messageDiv = document.getElementById('message');

        downloadBtn.addEventListener('click', async () => {
            const url = urlInput.value.trim();
            if (!url) {
                showMessage('❌ Introduce una URL de YouTube válida', 'error');
                return;
            }

            downloadBtn.disabled = true;
            downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
            progressContainer.classList.remove('hidden');
            progressBar.style.width = '0%';
            progressPercent.innerText = '0%';
            messageDiv.innerHTML = '';

            // Simulación de progreso visual
            let fakeProgress = 0;
            const interval = setInterval(() => {
                if (fakeProgress < 90) {
                    fakeProgress += 10;
                    progressBar.style.width = fakeProgress + '%';
                    progressPercent.innerText = fakeProgress + '%';
                }
            }, 300);

            try {
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });
                const data = await response.json();
                clearInterval(interval);
                if (!response.ok) throw new Error(data.error || 'Error desconocido');
                progressBar.style.width = '100%';
                progressPercent.innerText = '100%';
                urlInput.value = '';
            } catch (err) {
                clearInterval(interval);
                progressContainer.classList.add('hidden');
                showMessage(`❌ Error: ${err.message}. ¿Revisaste la URL?`, 'error');
            } finally {
                downloadBtn.disabled = false;
                downloadBtn.innerHTML = '<i class="fas fa-download"></i> Descargar MP3';
                setTimeout(() => progressContainer.classList.add('hidden'), 3000);
            }
        });

        function showMessage(msg, type) {
            messageDiv.innerHTML = msg;
            const classes = type === 'error' 
                ? 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 p-3 rounded-lg' 
                : 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-200 p-3 rounded-lg';
            messageDiv.className = `mt-4 text-center text-sm ${classes}`;
            setTimeout(() => { if (messageDiv.innerHTML === msg) messageDiv.innerHTML = ''; }, 8000);
        }
    </script>
</body>
</html>
"""
# -------------------------------------------------------------------------

def limpiar_nombre(nombre):
    """Elimina caracteres no permitidos en nombres de archivo Windows/Linux"""
    return re.sub(r'[\\/*?:"<>|]', "", nombre).strip()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/download', methods=['POST'])
def download_audio():
    data = request.get_json()
    video_url = data.get('url')
    if not video_url:
        return jsonify({'error': 'URL no proporcionada'}), 400

    # Opciones para yt-dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        'quiet': True,   # Menos ruido en la consola
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title', 'audio')
            nombre_limpio = limpiar_nombre(title) + ".mp3"
            return jsonify({'filename': nombre_limpio})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def descargar_archivo(filename):
    """Sirve el MP3 para descargar"""
    ruta_completa = os.path.join(DOWNLOAD_FOLDER, filename)
    if not os.path.exists(ruta_completa):
        return "Archivo no encontrado", 404
    return send_file(ruta_completa, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)