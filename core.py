import base64
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/send', methods=['POST'])
def image_retrieve():
    data = request.form['img']
    max_count = int(request.form['max_count'])
    img = base64.standard_b64decode(data)
    with open('c:/test.jpg', 'wb') as f:
        print >>f, img

    return jsonify({'status': 'ok', 'results': [data for _ in range(max_count)]})


if __name__ == '__main__':
    app.run(debug=True)
