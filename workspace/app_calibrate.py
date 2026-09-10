from flask import Flask, render_template, request, jsonify, Response, send_from_directory, send_file
import cv2
import numpy as np
import os
import glob
import json
import time
import base64

app = Flask(__name__)

# Directory setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'calibration_images')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global settings & active camera handle
VIDEO_DEVICE = os.getenv('VIDEO_DEVICE', '/dev/video1')
active_device = VIDEO_DEVICE
camera_handle = None
last_calibration_result = None

def get_camera_index(dev_path):
    """Utility to convert device path like /dev/video1 to integer index 1 if needed."""
    if isinstance(dev_path, int):
        return dev_path
    if str(dev_path).isdigit():
        return int(dev_path)
    if str(dev_path).startswith('/dev/video'):
        try:
            return int(str(dev_path).replace('/dev/video', ''))
        except ValueError:
            pass
    return dev_path

def get_camera():
    global camera_handle, active_device
    if camera_handle is not None and camera_handle.isOpened():
        return camera_handle
    
    dev_id = get_camera_index(active_device)
    camera_handle = cv2.VideoCapture(dev_id, cv2.CAP_V4L2)
    if not camera_handle.isOpened():
        # Fallback without V4L2 flag
        camera_handle = cv2.VideoCapture(dev_id)
    return camera_handle

def release_camera():
    global camera_handle
    if camera_handle is not None:
        camera_handle.release()
        camera_handle = None

def generate_frames(overlay=True, pattern_size=(9, 6)):
    """Generator for MJPEG stream with optional live corner detection overlay."""
    while True:
        cap = get_camera()
        if not cap or not cap.isOpened():
            # Generate black frame with error text if camera unavailable
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "Kamera Tidak Terhubung (" + str(active_device) + ")", 
                        (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.5)
            continue

        success, frame = cap.read()
        if not success:
            time.sleep(0.05)
            continue

        if overlay:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            found, corners = cv2.findChessboardCorners(gray, pattern_size, cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FAST_CHECK + cv2.CALIB_CB_NORMALIZE_IMAGE)
            if found:
                cv2.drawChessboardCorners(frame, pattern_size, corners, found)
                cv2.putText(frame, f"CHESSBOARD DETECTED ({pattern_size[0]}x{pattern_size[1]})", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "Arahkan Kamera ke Papan Catur...", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.03)

@app.route('/')
def index():
    return render_template('calibrate.html')

@app.route('/video_feed')
def video_feed():
    overlay = request.args.get('overlay', '1') == '1'
    cols = int(request.args.get('cols', 9))
    rows = int(request.args.get('rows', 6))
    return Response(generate_frames(overlay=overlay, pattern_size=(cols, rows)),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/devices')
def list_devices():
    devs = glob.glob('/dev/video*')
    devs.sort()
    return jsonify({
        "devices": devs if devs else ["/dev/video1", "/dev/video0"],
        "current": active_device
    })

@app.route('/set_device', methods=['POST'])
def set_device():
    global active_device
    data = request.get_json() or {}
    new_device = data.get('device', '/dev/video1')
    release_camera()
    active_device = new_device
    return jsonify({"status": "success", "active_device": active_device})

@app.route('/capture', methods=['POST'])
def capture_frame():
    data = request.get_json() or {}
    cols = data.get('cols', 9)
    rows = data.get('rows', 6)

    cap = get_camera()
    if not cap or not cap.isOpened():
        return jsonify({"status": "error", "message": "Gagal membuka kamera"}), 500

    success, frame = cap.read()
    if not success:
        return jsonify({"status": "error", "message": "Gagal membaca frame kamera"}), 500

    timestamp = int(time.time() * 1000)
    filename = f"capture_{timestamp}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    cv2.imwrite(filepath, frame)

    # Check for corners
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners_found, _ = cv2.findChessboardCorners(gray, (cols, rows), None)

    return jsonify({
        "status": "success",
        "filename": filename,
        "url": f"/images/{filename}",
        "corners_found": corners_found
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'images' not in request.files:
        return jsonify({"status": "error", "message": "Tidak ada file yang diunggah"}), 400

    cols = int(request.form.get('cols', 9))
    rows = int(request.form.get('rows', 6))

    files = request.files.getlist('images')
    saved_count = 0

    for file in files:
        if file.filename == '':
            continue
        timestamp = int(time.time() * 1000)
        filename = f"upload_{timestamp}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        saved_count += 1

    return jsonify({
        "status": "success",
        "message": f"Berhasil mengunggah {saved_count} foto papan catur."
    })

@app.route('/images')
def list_images():
    cols = int(request.args.get('cols', 9))
    rows = int(request.args.get('rows', 6))

    image_files = sorted(glob.glob(os.path.join(UPLOAD_FOLDER, '*.[jJ][pP][gG]')) + 
                         glob.glob(os.path.join(UPLOAD_FOLDER, '*.[pP][nN][gG]')))

    results = []
    for path in image_files:
        fname = os.path.basename(path)
        img = cv2.imread(path)
        corners_found = False
        if img is not None:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            ret, _ = cv2.findChessboardCorners(gray, (cols, rows), cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FAST_CHECK)
            corners_found = ret

        results.append({
            "filename": fname,
            "url": f"/images/{fname}",
            "corners_found": corners_found
        })

    return jsonify({"images": results})

@app.route('/images/<filename>', methods=['GET'])
def get_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/images/<filename>', methods=['DELETE'])
def delete_image(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({"status": "success", "message": "File dihapus"})
    return jsonify({"status": "error", "message": "File tidak ditemukan"}), 404

@app.route('/images/clear', methods=['POST'])
def clear_images():
    files = glob.glob(os.path.join(UPLOAD_FOLDER, '*'))
    for f in files:
        try:
            os.remove(f)
        except Exception:
            pass
    return jsonify({"status": "success", "message": "Semua foto dihapus"})

@app.route('/calibrate', methods=['POST'])
def calibrate():
    global last_calibration_result
    data = request.get_json() or {}
    cols = int(data.get('cols', 9))
    rows = int(data.get('rows', 6))
    square_size = float(data.get('square_size', 25.0)) # in mm

    pattern_size = (cols, rows)
    image_paths = sorted(glob.glob(os.path.join(UPLOAD_FOLDER, '*.[jJ][pP][gG]')) + 
                         glob.glob(os.path.join(UPLOAD_FOLDER, '*.[pP][nN][gG]')))

    if len(image_paths) == 0:
        return jsonify({"status": "error", "message": "Tidak ada foto di galeri. Ambil minimal 5-10 foto."}), 400

    # Prepare 3D object points (0,0,0), (1,0,0), (2,0,0) ...
    objp = np.zeros((cols * rows, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2) * square_size

    objpoints = [] # 3d point in real world space
    imgpoints = [] # 2d points in image plane.
    valid_images = []
    img_shape = None

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    for fname in image_paths:
        img = cv2.imread(fname)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_shape = gray.shape[::-1]

        # Find chessboard corners
        ret, corners = cv2.findChessboardCorners(gray, pattern_size, cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE)

        if ret:
            objpoints.append(objp)
            corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            imgpoints.append(corners2)
            valid_images.append(fname)

    if len(objpoints) < 3:
        return jsonify({
            "status": "error", 
            "message": f"Hanya {len(objpoints)} foto dengan pola sudut catur ({cols}x{rows}) yang valid. Dibutuhkan minimal 3-5 foto valid."
        }), 400

    # Perform camera calibration
    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, img_shape, None, None)

    # Compute Reprojection Error (RMSE)
    total_error = 0
    for i in range(len(objpoints)):
        imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
        error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
        total_error += error
    rmse = total_error / len(objpoints)

    # Generate Undistort Preview from first valid image
    sample_orig_b64 = ""
    sample_undist_b64 = ""
    if len(valid_images) > 0:
        sample_img = cv2.imread(valid_images[0])
        h, w = sample_img.shape[:2]
        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (w, h), 1, (w, h))
        dst = cv2.undistort(sample_img, mtx, dist, None, newcameramtx)

        # Crop if roi valid
        x, y, w_roi, h_roi = roi
        if w_roi > 0 and h_roi > 0:
            dst_cropped = dst[y:y+h_roi, x:x+w_roi]
        else:
            dst_cropped = dst

        _, buf1 = cv2.imencode('.jpg', sample_img)
        _, buf2 = cv2.imencode('.jpg', dst_cropped)
        sample_orig_b64 = "data:image/jpeg;base64," + base64.b64encode(buf1).decode('utf-8')
        sample_undist_b64 = "data:image/jpeg;base64," + base64.b64encode(buf2).decode('utf-8')

    result_payload = {
        "status": "success",
        "reproj_error": float(rmse),
        "camera_matrix": mtx.tolist(),
        "dist_coeff": dist.tolist(),
        "image_width": img_shape[0],
        "image_height": img_shape[1],
        "valid_images_count": len(valid_images),
        "total_images_count": len(image_paths),
        "sample_original": sample_orig_b64,
        "sample_undistorted": sample_undist_b64
    }

    last_calibration_result = result_payload

    # Save to JSON
    json_path = os.path.join(BASE_DIR, 'camera_calibration.json')
    with open(json_path, 'w') as f:
        json.dump(result_payload, f, indent=4)

    # Save to ROS YAML format (ost.yaml / camera_info.yaml)
    yaml_path = os.path.join(BASE_DIR, 'camera_calibration.yaml')
    save_ros_yaml(yaml_path, result_payload)

    return jsonify(result_payload)

def save_ros_yaml(filepath, res):
    K = res['camera_matrix']
    D = res['dist_coeff'][0]
    w = res['image_width']
    h = res['image_height']

    yaml_content = f"""image_width: {w}
image_height: {h}
camera_name: drone_camera
camera_matrix:
  rows: 3
  cols: 3
  data: [{K[0][0]:.6f}, {K[0][1]:.6f}, {K[0][2]:.6f}, {K[1][0]:.6f}, {K[1][1]:.6f}, {K[1][2]:.6f}, {K[2][0]:.6f}, {K[2][1]:.6f}, {K[2][2]:.6f}]
distortion_model: plumb_bob
distortion_coefficients:
  rows: 1
  cols: 5
  data: [{D[0]:.6f}, {D[1]:.6f}, {D[2]:.6f}, {D[3]:.6f}, {D[4]:.6f}]
rectification_matrix:
  rows: 3
  cols: 3
  data: [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
projection_matrix:
  rows: 3
  cols: 4
  data: [{K[0][0]:.6f}, 0.0, {K[0][2]:.6f}, 0.0, 0.0, {K[1][1]:.6f}, {K[1][2]:.6f}, 0.0, 0.0, 0.0, 1.0, 0.0]
"""
    with open(filepath, 'w') as f:
        f.write(yaml_content)

@app.route('/download/yaml')
def download_yaml():
    path = os.path.join(BASE_DIR, 'camera_calibration.yaml')
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name='camera_calibration.yaml')
    return jsonify({"status": "error", "message": "Belum ada hasil kalibrasi"}), 404

@app.route('/download/json')
def download_json():
    path = os.path.join(BASE_DIR, 'camera_calibration.json')
    if os.path.exists(path):
        return send_file(path, as_attachment=True, download_name='camera_calibration.json')
    return jsonify({"status": "error", "message": "Belum ada hasil kalibrasi"}), 404

if __name__ == '__main__':
    port = int(os.getenv('CALIBRATE_PORT', 5001))
    print(f"[*] Starting Camera Calibration Web Server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
