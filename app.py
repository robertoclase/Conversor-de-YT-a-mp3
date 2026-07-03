import os
import re
import uuid
import zipfile
import tempfile
from urllib.parse import quote

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
        body {
            transition: background 0.3s, color 0.3s;
            background:
                radial-gradient(circle at top left, rgba(239, 68, 68, 0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(168, 85, 247, 0.16), transparent 24%),
                linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
        }
        .dark body {
            background:
                radial-gradient(circle at top left, rgba(239, 68, 68, 0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(168, 85, 247, 0.14), transparent 24%),
                linear-gradient(180deg, #020617 0%, #0f172a 100%);
            color: #e2e8f0;
        }
        .dark .card {
            background: rgba(15, 23, 42, 0.82);
            border-color: rgba(148, 163, 184, 0.16);
        }
        .card {
            transition: transform 0.2s, box-shadow 0.2s;
            backdrop-filter: blur(14px);
            border: 1px solid rgba(148, 163, 184, 0.18);
        }
        .card:hover {
            transform: translateY(-4px);
            box-shadow: 0 24px 60px rgba(15, 23, 42, 0.12);
        }
        #progress-bar { transition: width 0.3s ease; }
        .glass {
            background: rgba(255, 255, 255, 0.72);
            backdrop-filter: blur(14px);
        }
    </style>
</head>
<body class="bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
    <div class="container mx-auto px-4 py-12 max-w-3xl">
        <div class="flex justify-between items-center mb-8">
            <div>
                <div class="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold tracking-wide uppercase bg-white/75 dark:bg-slate-800/80 border border-slate-200/70 dark:border-slate-700/70 shadow-sm mb-4">
                    <span class="h-2 w-2 rounded-full bg-red-500"></span>
                    Conversor local
                </div>
                <h1 class="text-4xl sm:text-5xl font-black bg-gradient-to-r from-red-500 via-orange-500 to-purple-600 bg-clip-text text-transparent">
                    <i class="fab fa-youtube text-red-600 mr-2"></i> YouTube → MP3
                </h1>
                <p class="mt-3 text-sm sm:text-base text-slate-600 dark:text-slate-300 max-w-xl">
                    Pega una canción o una playlist completa. La app descargará el audio, lo convertirá a MP3 y te devolverá un ZIP si es una lista.
                </p>
            </div>
            <button id="theme-toggle" class="p-2.5 rounded-full bg-white/80 dark:bg-gray-700/90 border border-slate-200 dark:border-slate-700 shadow-sm">
                <i id="theme-icon" class="fas fa-moon"></i>
            </button>
        </div>

        <div class="card glass dark:bg-gray-800/80 rounded-3xl shadow-2xl p-6 sm:p-8 mb-8">
            <div class="flex flex-wrap gap-2 mb-4 text-xs font-semibold text-slate-600 dark:text-slate-300">
                <span class="px-3 py-1 rounded-full bg-red-50 text-red-700 dark:bg-red-950/70 dark:text-red-200">Vídeo suelto</span>
                <span class="px-3 py-1 rounded-full bg-purple-50 text-purple-700 dark:bg-purple-950/70 dark:text-purple-200">Playlist completa</span>
                <span class="px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-950/70 dark:text-emerald-200">MP3 + ZIP</span>
            </div>
            <label class="block text-sm font-semibold mb-2">URL del vídeo o playlist de YouTube</label>
            <div class="flex flex-col sm:flex-row gap-3">
                <input type="text" id="url" placeholder="Pega una URL de YouTube o una playlist completa"
                       class="flex-1 p-4 border border-slate-200 dark:border-slate-700 rounded-xl bg-white/90 dark:bg-gray-700 focus:ring-2 focus:ring-red-500 focus:border-transparent outline-none shadow-sm">
                <button id="download-btn" class="bg-gradient-to-r from-red-600 to-orange-500 hover:from-red-500 hover:to-orange-400 text-white font-bold py-3 px-6 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-red-500/20 transition-transform active:scale-[0.99]">
                    <i class="fas fa-download"></i> Descargar MP3
                </button>
            </div>

            <div class="mt-4 grid gap-3 sm:grid-cols-2">
                <label class="flex items-center gap-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-gray-800/70 px-4 py-3 text-sm">
                    <input type="checkbox" id="use-cookies" class="h-4 w-4 text-red-600 focus:ring-red-500 rounded border-slate-300">
                    <span>Usar cookies del navegador</span>
                </label>
                <label class="flex items-center gap-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-gray-800/70 px-4 py-3 text-sm">
                    <span class="text-slate-600 dark:text-slate-300 whitespace-nowrap">Navegador</span>
                    <select id="cookie-browser" class="flex-1 bg-transparent focus:outline-none">
                        <option value="chrome">Chrome</option>
                        <option value="edge">Edge</option>
                        <option value="brave">Brave</option>
                        <option value="firefox">Firefox</option>
                    </select>
                </label>
                <label class="flex items-center gap-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white/70 dark:bg-gray-800/70 px-4 py-3 text-sm sm:col-span-2">
                    <span class="text-slate-600 dark:text-slate-300 whitespace-nowrap">cookies.txt</span>
                    <input type="file" id="cookie-file" accept=".txt,text/plain" class="flex-1 text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-red-600 file:px-3 file:py-2 file:text-white file:font-semibold hover:file:bg-red-500">
                </label>
                <p class="sm:col-span-2 text-xs text-slate-500 dark:text-slate-400 -mt-1">
                    Si el navegador da error, exporta tus cookies a un archivo <span class="font-semibold">cookies.txt</span> y súbelo aquí.
                </p>
            </div>

            <div id="progress-container" class="hidden mt-5">
                <div class="flex justify-between text-sm mb-1">
                    <span><i class="fas fa-spinner fa-spin"></i> Procesando...</span>
                    <span id="progress-percent">0%</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-600 overflow-hidden">
                    <div id="progress-bar" class="bg-red-600 h-2.5 rounded-full" style="width:0%"></div>
                </div>
            </div>

            <div id="message" class="mt-4 text-center text-sm"></div>
        </div>

        <footer class="text-center text-sm text-slate-500 dark:text-slate-400">
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
        const useCookiesInput = document.getElementById('use-cookies');
        const cookieBrowserInput = document.getElementById('cookie-browser');
        const cookieFileInput = document.getElementById('cookie-file');
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
                const formData = new FormData();
                formData.append('url', url);
                formData.append('use_cookies', useCookiesInput.checked ? '1' : '0');
                formData.append('cookie_browser', cookieBrowserInput.value);
                if (cookieFileInput.files && cookieFileInput.files[0]) {
                    formData.append('cookie_file', cookieFileInput.files[0]);
                }

                const response = await fetch('/download', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                clearInterval(interval);
                if (!response.ok) throw new Error(data.error || 'Error desconocido');
                progressBar.style.width = '100%';
                progressPercent.innerText = '100%';
                urlInput.value = '';
                if (data.download_url) {
                    showMessage(data.message || '✅ MP3 listo. Iniciando descarga...', 'success');
                    window.location.href = data.download_url;
                } else {
                    showMessage(data.message || '✅ Conversión completada', 'success');
                }
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


def crear_zip_desde_carpeta(carpeta_origen, archivo_zip):
    with zipfile.ZipFile(archivo_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
        for nombre_archivo in os.listdir(carpeta_origen):
            ruta_archivo = os.path.join(carpeta_origen, nombre_archivo)
            if os.path.isfile(ruta_archivo) and nombre_archivo.lower().endswith('.mp3'):
                zip_file.write(ruta_archivo, arcname=nombre_archivo)


def es_playlist(url):
    return 'list=' in url or '/playlist' in url

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/download', methods=['POST'])
def download_audio():
    data = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
    video_url = data.get('url')
    if not video_url:
        return jsonify({'error': 'URL no proporcionada'}), 400

    playlist_mode = bool(data.get('playlist')) or es_playlist(video_url)
    use_cookies = str(data.get('use_cookies', '')).lower() in ('1', 'true', 'yes', 'on')
    cookie_browser = (data.get('cookie_browser') or 'chrome').strip().lower()
    cookie_file = request.files.get('cookie_file')

    # Opciones para yt-dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': not playlist_mode,
        'retries': 3,
        'fragment_retries': 3,
        'socket_timeout': 15,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Referer': 'https://www.youtube.com/',
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
            }
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title).200s [%(id)s].%(ext)s'),
        'quiet': True,   # Menos ruido en la consola
    }

    if use_cookies:
        if cookie_file and cookie_file.filename:
            cookie_path = os.path.join(tempfile.gettempdir(), f"ytcookies_{uuid.uuid4().hex}.txt")
            cookie_file.save(cookie_path)
            ydl_opts['cookiefile'] = cookie_path
        else:
            ydl_opts['cookiesfrombrowser'] = (cookie_browser,)

    if playlist_mode:
        ydl_opts['ignoreerrors'] = True

    try:
        if playlist_mode:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_preview = ydl.extract_info(video_url, download=False)
                if not info_preview:
                    return jsonify({'error': 'No se pudo leer la playlist. Prueba con otra URL o una playlist más pública.'}), 400
                playlist_title = limpiar_nombre(
                    info_preview.get('title')
                    or info_preview.get('playlist_title')
                    or info_preview.get('id')
                    or 'playlist'
                ) or 'playlist'
                batch_name = f"{playlist_title}_{uuid.uuid4().hex[:8]}"
                batch_folder = os.path.join(DOWNLOAD_FOLDER, batch_name)
                os.makedirs(batch_folder, exist_ok=True)
                ydl_opts['outtmpl'] = os.path.join(batch_folder, '%(playlist_index)03d - %(title).200s [%(id)s].%(ext)s')

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                skipped_items = []
                downloaded_items = 0
                entries = (info_preview.get('entries') or [])

                for entry in entries:
                    if not entry:
                        skipped_items.append('Entrada vacía')
                        continue

                    entry_url = entry.get('webpage_url') or entry.get('url')
                    entry_title = limpiar_nombre(entry.get('title') or entry.get('id') or 'sin_titulo')

                    if not entry_url:
                        skipped_items.append(entry_title)
                        continue

                    try:
                        ydl.extract_info(entry_url, download=True)
                        downloaded_items += 1
                    except Exception:
                        skipped_items.append(entry_title)

                if downloaded_items == 0:
                    return jsonify({
                        'error': 'No se pudo descargar ninguna canción de la playlist. Es probable que YouTube haya bloqueado el contenido o que la lista no tenga temas accesibles.',
                        'details': 'Todas las entradas fallaron o se omitieron.',
                    }), 400

            zip_filename = f"{batch_name}.zip"
            zip_path = os.path.join(DOWNLOAD_FOLDER, zip_filename)
            crear_zip_desde_carpeta(batch_folder, zip_path)

            if not os.path.exists(zip_path):
                return jsonify({'error': 'La playlist terminó, pero no se pudo generar el ZIP'}), 500

            return jsonify({
                'playlist': True,
                'filename': zip_filename,
                'download_url': f"/download-zip/{quote(zip_filename)}",
                'downloaded': downloaded_items,
                'skipped': skipped_items,
                'message': f'Se descargaron {downloaded_items} canciones. Se omitieron {len(skipped_items)}.' if skipped_items else f'Se descargaron {downloaded_items} canciones.',
            })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            ruta_base = os.path.splitext(ydl.prepare_filename(info))[0]
            mp3_path = ruta_base + '.mp3'

            if not os.path.exists(mp3_path):
                return jsonify({'error': 'La conversión terminó, pero no se encontró el MP3 generado'}), 500

            nombre_archivo = os.path.basename(mp3_path)
            return jsonify({
                'filename': nombre_archivo,
                'download_url': f"/download/{quote(nombre_archivo)}",
            })
    except yt_dlp.utils.DownloadError as e:
        if playlist_mode:
            return jsonify({
                'error': 'No se pudo leer la playlist completa. Algunos vídeos pueden estar bloqueados o no disponibles.',
                'details': str(e),
            }), 400
        return jsonify({
            'error': 'Ese vídeo no se puede descargar porque YouTube lo bloquea o no está disponible.',
            'details': str(e),
        }), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def descargar_archivo(filename):
    """Sirve el MP3 para descargar"""
    ruta_completa = os.path.join(DOWNLOAD_FOLDER, filename)
    if not os.path.exists(ruta_completa):
        return "Archivo no encontrado", 404
    return send_file(ruta_completa, as_attachment=True)


@app.route('/download-zip/<filename>')
def descargar_zip(filename):
    """Sirve el ZIP de una playlist para descargar"""
    ruta_completa = os.path.join(DOWNLOAD_FOLDER, filename)
    if not os.path.exists(ruta_completa):
        return "Archivo no encontrado", 404
    return send_file(ruta_completa, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)