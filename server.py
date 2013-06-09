# encoding: utf-8
import base64
import os
import timeit
from flask import Flask, request, jsonify, session
from core import ServerCore

app = Flask(__name__)

app.secret_key = '123456'

app.cores = {}


def gen_db_path(client_id):
    return 'entries.db'


@app.route('/', methods=['POST'])
def hail():
    return jsonify({'status': 'ok',
                    'comment': 'Hi, %s.' % (session['id'] if 'id' in session else 'there')})


@app.route('/login', methods=['POST'])
def login():
    if 'id' not in session:
        session['id'] = request.form['id']
        session.permanent = False
        app.cores[session['id']] = ServerCore(db_path=gen_db_path(session['id']))

        app.logger.info('core %s for %s', id(app.cores[session['id']]), session['id'])

        return jsonify({
            'status': 'ok'
        })
    else:
        return jsonify({
            'status': 'err',
            'comment': 'You are already logged in.'
        })


@app.route('/logout', methods=['POST'])
def logout():
    if 'id' in session:
        del app.cores[session['id']]
        session.pop('id', None)

        return jsonify({
            'status': 'ok'
        })
    else:
        return jsonify({
            'status': 'err',
            'comment': 'You are not even logged in.'
        })


@app.route('/add', methods=['POST'])
def add_to_db():
    if 'id' not in session:
        return jsonify({'status': 'err',
                        'comment': 'Please login.'})

    data = request.form['img']
    status, msg = app.cores[session['id']].add_jpeg_file(data)

    return jsonify({'status': status,
                    'comment': msg})


@app.route('/retrieve', methods=['POST'])
def retrieve():
    if 'id' not in session:
        return jsonify({'status': 'err',
                        'comment': 'Please login.'})

    core = app.cores[session['id']]
    try:
        fn, norm = core.retrieve()
        status = 'ok'
        result = (base64.standard_b64encode(open(os.path.join(core.img_store_path,
                                                              '%s.jpg' % fn),
                                                 'rb').read()),
                  norm)
    except IOError as err:
        status = 'err'
        if 'Errno 2' in err.message:
            result = 'Cannot find proper image file.'
        else:
            result = 'Internal Server Error: %s.' % err.message

    return jsonify({
        'status': status,
        'result': result
    })


@app.route('/send', methods=['POST'])
def retrieve_prepare():
    if 'id' not in session:
        return jsonify({'status': 'err',
                        'comment': 'Please login.'})

    core = app.cores[session['id']]
    data = request.form['img']
    max_count = int(request.form['max_count'])

    status = 'ok'
    start = timeit.default_timer()
    result = core.prepare_results(data, n=max_count)
    end = timeit.default_timer()

    return jsonify({
        'status': status,
        'result': result,
        'time_elapsed': '%2.5f' % (end - start)
    })


if __name__ == '__main__':
    app.run(debug=True)


