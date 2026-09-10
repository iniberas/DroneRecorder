from flask import Flask, render_template_string, jsonify
import subprocess
import os

app = Flask(__name__)

FCU_URL = os.getenv('FCU_URL', '/dev/ttyACM0:921600')
VIDEO_DEVICE = os.getenv('VIDEO_DEVICE', '/dev/video1')
BAG_FOLDER = os.getenv('BAG_FOLDER', './')

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SBC Control Panel</title>
    <style>
        body { display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #2c3e50; font-family: Arial, sans-serif; color: white; }
        .config-box { background-color: #34495e; padding: 20px; border-radius: 8px; margin-bottom: 30px; text-align: left; }
        .config-box h3 { margin-top: 0; color: #f39c12; }
        .btn-group { display: flex; gap: 20px; }
        .btn { color: white; border: none; padding: 15px 30px; font-size: 18px; border-radius: 8px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: 0.2s; font-weight: bold; }
        .btn-start { background-color: #2980b9; }
        .btn-record { background-color: #27ae60; }
        .btn-stop { background-color: #c0392b; }
        .btn:hover { filter: brightness(1.1); transform: scale(1.05); }
        .btn:active { transform: scale(0.95); }
        #output { margin-top: 20px; color: #ecf0f1; font-size: 14px; background: #1a252f; padding: 15px; border-radius: 5px; width: 80%; max-width: 600px; white-space: pre-wrap; display: none; min-height: 50px; }
    </style>
</head>
<body>
    <div class="config-box">
        <h3>Konfigurasi Aktif (.env)</h3>
        <div><strong>FCU_URL:</strong> {{ fcu_url }}</div>
        <div><strong>VIDEO_DEVICE:</strong> {{ video_device }}</div>
        <div><strong>BAG_FOLDER:</strong> {{ bag_folder }}</div>
    </div>

    <div class="btn-group">
        <button class="btn btn-start" onclick="runCommand('/start')">Start Topic</button>
        <button class="btn btn-record" onclick="runCommand('/record')">Start Record</button>
        <button class="btn btn-stop" onclick="runCommand('/stop')">Stop All</button>
        <a id="calibBtn" class="btn" style="background-color: #8e44ad; text-decoration: none;" href="http://{{ request.host.split(':')[0] }}:5001" target="_blank">Kalibrasi Kamera (5001)</a>
    </div>
    
    <div id="output">Output akan muncul di sini...</div>

    <script>
        function runCommand(endpoint) {
            const outputDiv = document.getElementById('output');
            outputDiv.style.display = 'block';
            outputDiv.innerText = 'Mengeksekusi perintah...';

            fetch(endpoint, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    outputDiv.innerText = data.output;
                })
                .catch(error => {
                    outputDiv.innerText = 'Error Network: ' + error;
                });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    # Mengirimkan nilai variabel ke HTML agar tampil di layar
    return render_template_string(HTML_PAGE, fcu_url=FCU_URL, video_device=VIDEO_DEVICE, bag_folder=BAG_FOLDER)

@app.route('/start', methods=['POST'])
def start_topic():
    try:
        result = subprocess.run(['bash', 'start-topic.sh', FCU_URL, VIDEO_DEVICE], capture_output=True, text=True, check=True)
        return jsonify({"status": "success", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "output": f"Error:\n{e.stderr}\n{e.stdout}"})

@app.route('/record', methods=['POST'])
def record_bag():
    try:
        result = subprocess.run(['bash', 'record.sh', BAG_FOLDER], capture_output=True, text=True, check=True)
        return jsonify({"status": "success", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "output": f"Error:\n{e.stderr}\n{e.stdout}"})

@app.route('/stop', methods=['POST'])
def stop_all():
    try:
        result = subprocess.run(['bash', 'stop.sh'], capture_output=True, text=True, check=True)
        return jsonify({"status": "success", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "output": f"Error:\n{e.stderr}\n{e.stdout}"})

@app.route('/start-calibrate', methods=['POST'])
def start_calibrate():
    try:
        result = subprocess.run(['bash', 'start-calibrate.sh', '5001'], capture_output=True, text=True, check=True)
        return jsonify({"status": "success", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "output": f"Error:\n{e.stderr}\n{e.stdout}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)