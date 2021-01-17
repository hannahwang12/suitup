from lib.utils.image_transforms import scale_crop
import requests
import imageio
import cv2
import base64
from flask import Flask, render_template, Response, redirect, url_for
import sys
sys.path.append('../')


app = Flask(__name__)
camera = cv2.VideoCapture(0)

server_url = 'http://127.0.0.1:5000'
# server_url = 'http://9aaa3ade2048.ngrok.io'
# server_url = "http://34.221.75.41:5000"
configure_url = server_url + "/configure"
transform_url = server_url + "/transform"

uid = None
NULL_UID = '#'


def gen_frames():  # generate frame by frame from camera
    while True:
        # Capture frame-by-frame
        success, frame = camera.read()  # read the camera frame
        if not success:
            break
        else:
            frame = cv2.flip(scale_crop(frame), 1)
            _, buffer = cv2.imencode('.jpg', frame)
            stream_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + stream_bytes + b'\r\n')


@app.route('/configure', methods=['POST'])
def configure():
    source_image = imageio.imread('images/ryan.png')
    source_image = cv2.cvtColor(source_image, cv2.COLOR_BGR2RGB)

    source_image = cv2.flip(scale_crop(source_image), 1)
    _, source_buffer = cv2.imencode('.jpg', source_image)

    _, frame = camera.read()
    frame = cv2.flip(scale_crop(frame), 1)
    _, frame_buffer = cv2.imencode('.jpg', frame)

    source_encoded = base64.b64encode(source_buffer)
    frame_encoded = base64.b64encode(frame_buffer)

    data = {
        "source": source_encoded,
        "frame": frame_encoded,
    }

    r = requests.post(configure_url, data=data)

    if r.status_code != 200:
        print("error")
        return ('', 204)

    global uid
    uid = r.text

    return redirect(url_for('index'))


def gen_transformed_frames():
    while True:
        # Capture frame-by-frame
        success, frame = camera.read()  # read the camera frame
        if not success:
            break
        else:
            frame = cv2.flip(scale_crop(frame), 1)
            _, frame_buffer = cv2.imencode('.jpg', frame)
            frame_encoded = base64.b64encode(frame_buffer)
            data = {
                "uid": uid,
                "frame": frame_encoded
            }

            r = requests.post(transform_url, data=data)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + r.content + b'\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/transform')
def transform():
    if uid and uid is not NULL_UID:
        return Response(gen_transformed_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')


if __name__ == '__main__':
    app.run(port=3000)
