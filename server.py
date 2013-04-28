import base64
import os
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
    msg = app.core.add_jpeg_file(data)

    return jsonify({'status': msg})


@app.route('/send', methods=['POST'])
def retrieve():
    data = request.form['img']
    max_count = int(request.form['max_count'])

    results = app.core.retrieve(data, n=max_count)

    try:
        status = 'ok'
        results = map(
            lambda (uuid, dist): (
                base64.standard_b64encode(open(os.path.join(app.core.img_store_path,
                                                            '%s.jpg' % uuid), 'rb').read()),
                dist
            ), results)
    except IOError as err:
        status = 'retrieve failed because of unknown error'
        if 'Errno 2' in err.message:
            status = 'cannot find proper image file.'
        status = 'Internal Server Error: %s' % status

    return jsonify({
        'status': status,
        'results': results
    })


if __name__ == '__main__':
    app.run(debug=True)

