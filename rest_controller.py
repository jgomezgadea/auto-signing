#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from flask import Flask, jsonify, request
import telegram
from auto_signing import *
from flask_cors import CORS

app = Flask(__name__)
port = int(os.environ.get('PORT', 5000))
CORS(app)

sign = AutoSigning()
bot = telegram.Bot(sign.telegram_token)

@app.route('/{}'.format(sign.telegram_token), methods=['POST'])
def receive_telegram():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    #chat_id = update.message.chat.id
    #msg_id = update.message.message_id
    text = update.message.text.encode('utf-8').decode()
    sign.receive_telegram(text)
    return 'ok'

@app.route('/test')
def test():
    return jsonify(sign.print_test())

@app.route('/fichar_hoy')
def fichar_hoy():
    return jsonify(sign.signing_today())

@app.route('/fichar_ayer')
def fichar_ayer():
    return jsonify(sign.signing_yesterday())

@app.route('/fichar/<fecha>')
def fichar_fecha(fecha):
    return jsonify(sign.signing_date(fecha))

@app.route('/activar')
def activar():
    return jsonify(sign.set_active(True))

@app.route('/desactivar')
def desactivar():
    return jsonify(sign.set_active(False))

@app.route('/session_id/<session_id>')
def establecer_id(session_id):
    return jsonify(sign.set_session_id(session_id))

@app.errorhandler(404)
def not_found(status:int):
    message = {
        'status': status,
        'message':'Record not found: ' + request.url,
    }
    response = jsonify(message)
    response.status_code = 404
    return response

if __name__ == '__main__':
    # Set telegram webhook
    bot.setWebhook('{URL}{HOOK}'.format(URL=sign.heroku_url, HOOK=sign.telegram_token))
    # Start flask server
    app.run(debug=False, host='0.0.0.0', port=port)