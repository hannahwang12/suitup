from flask import Flask, render_template, Response, redirect, url_for
import base64
import cv2
import imageio
import requests
import socketio

app = Flask(__name__)
camera = cv2.VideoCapture(0)

server_url = "http://localhost:5000"
configure_url = server_url + "/configure"
transform_url = server_url + "/transform"


# standard Python
currframe = None
sio = socketio.Client()
@sio.event
def message(data):
    print('msg :' + data)
    # Mutate currframe here

uid = None
NULL_UID = '#'

def crop_img(img):
    w = img.shape[0]
    h = img.shape[1]
    crop_size = min(w,h)
    startx = w//2-(crop_size//2)
    starty = h//2-(crop_size//2)
    cropped = img[starty:starty+crop_size, startx:startx+crop_size]
    return cropped


def gen_frames():  # generate frame by frame from camera
    while True:
        # Capture frame-by-frame
        success, frame = camera.read()  # read the camera frame
        if not success:
            break
        else:
            frame = cv2.flip(crop_img(frame), 1)
            ret, buffer = cv2.imencode('.jpg', frame)
            stream_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + stream_bytes + b'\r\n')


@app.route('/configure', methods = ['POST'])
def configure():
    source_image = imageio.imread('images/jack3.jpg')
    source_image = cv2.cvtColor(source_image, cv2.COLOR_BGR2RGB)
    _, source_buffer = cv2.imencode('.jpg', source_image)

    _, frame = camera.read()
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

    global sio
    if not sio.sid:
      sio.connect('ws://localhost:5000/connect')

    return redirect(url_for('index'))


def gen_transformed_frames():
    while True:
        success, frame = camera.read()  # read the camera frame
        if not success:
            break
        else:
            _, frame_buffer = cv2.imencode('.jpg', frame)
            frame_encoded = base64.b64encode(frame_buffer)
            data = {
              "uid": uid,
              "frame": frame_encoded
            }

            global sio
            sio.emit('data', data)
            print("emitted!")

            global currframe
            yield "tmp"
            """
            yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + currframe + b'\r\n')
            """
    """
    while True:
        # Capture frame-by-frame
        success, frame = camera.read()  # read the camera frame
        if not success:
            break
        else:
            _, frame_buffer = cv2.imencode('.jpg', frame)
            frame_encoded = base64.b64encode(frame_buffer)
            data = {
              "uid": uid,
              "frame": frame_encoded
            }

            r = requests.post(transform_url, data=data)
            yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + r.content + b'\r\n')
    """


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