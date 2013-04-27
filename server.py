import base64
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
    status = app.core.add_jpeg_file(data)

    return jsonify({'status': 'ok' if status else 'fail'})


@app.route('/send', methods=['POST'])
def retrieve():
    data = request.form['img']
    max_count = int(request.form['max_count'])

    results = app.core.retrieve(data, n=max_count)

    return jsonify({
        'status': 'ok',
        'results': map(
            lambda uuid: base64.standard_b64encode(open('images/%s.jpg' % uuid,
                                                      'rb').read()),
            results
        )
    })


if __name__ == '__main__':
    app.run(debug=True)

