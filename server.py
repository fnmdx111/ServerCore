import base64
import uuid
import cv2
from flask import Flask, request, jsonify
from core import ServerCore

app = Flask(__name__)
app.core = ServerCore()


@app.route('/')
def hail():
    return jsonify({'status': 'ok',
                    'content': 'hi, there'})


@app.route('/add', methods=['POST'])
def add_to_db():
    data = request.form['img']
    img = app.core.from_raw_to_grayscale(base64.standard_b64decode(data))

    app.core.add_jpeg_file(img)

    return jsonify({'status': 'ok'})


@app.route('/send', methods=['POST'])
def retrieve():
    data = request.form['img']
    max_count = int(request.form['max_count'])
    img = app.core.from_raw_to_grayscale(base64.standard_b64decode(data))

    results = app.core.retrieve(img, n=max_count)

    return jsonify({
        'status': 'ok',
        'results': map(
            lambda fn: base64.standard_b64encode(open('images/%s' % fn,
                                                      'rb').read()),
            results
        )
    })


if __name__ == '__main__':
    app.run(debug=True)

