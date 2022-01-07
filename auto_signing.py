#!/usr/bin/env python
# -*- coding: utf-8 -*-

from random import randrange
from datetime import datetime, timedelta
import requests
import json
from pytz import timezone
import pandas as pd
import pymongo
import os

from telegram import ParseMode
from telegram.ext import Updater

class AutoSigning():

    def __init__(self):
        self.odoo_url = os.environ['ODOO_URL']
        self.telegram_token = os.environ['TELEGRAM_TOKEN']
        self.telegram_chat_id = os.environ['TELEGRAM_CHAT_ID']
        self.heroku_url = os.environ['HEROKU_URL']
        self.mongodb_client_url = os.environ['MONGODB_CLIENT_URL']

        self.mongodb_client = pymongo.MongoClient(self.mongodb_client_url)
        self.mongodb_database = self.mongodb_client["autoSigning"]
        self.mongodb_collection = self.mongodb_database["autoSigningParams"]

        self.session_id = self.get_mongodb_session_id()
        self.active = self.get_mongodb_active()

        self.headers = {
                    'Cookie': 'session_id='+self.session_id,
                    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:94.0) Gecko/20100101 Firefox/94.0',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
        }

        self.data = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "args": [
                    {
                        "employee_id": 94,
                        "check_in": "2021-11-13 18:36:20",
                        "check_out": "2021-11-13 18:36:21"
                    }
                ],
                "model": "hr.attendance",
                "method": "create",
                "kwargs": {
                    "context": {
                        "lang": "es_ES",
                        "tz": "Europe/Brussels",
                        "uid": 60,
                        "search_default_today": 1
                    }
                }
            },
            "id": 983940971
        }

        self.utc = timezone('UTC')
        self.bru = timezone('Europe/Brussels')

        self.updater = Updater(token=self.telegram_token, use_context=True)

    def twodigits(self, num: int) -> str:
        if(num < 10):
            return "0" + str(num)
        else:
            return str(num)

    def tz_diff(self, date, tz1, tz2):
        '''
        Returns the difference in hours between timezone1 and timezone2
        for a given date.
        '''
        date = pd.to_datetime(date)
        return int((tz1.localize(date) - tz2.localize(date).astimezone(tz1)).seconds/3600)

    def print_test(self) -> str:
        return "Esto es un test..."

    def set_session_id(self, session_id) -> str:
        self.set_mongodb_session_id(session_id)
        self.session_id = session_id
        self.headers['Cookie'] = 'session_id='+self.session_id
        self.send_telegram("Establecida nueva session_id="+self.session_id)
        return "Establecida nueva session_id="+self.session_id

    def set_active(self, active: bool) -> str:
        self.active = active
        self.set_mongodb_active(active)
        self.send_telegram("Establecido estado activo="+str(active)+" en mongodb.")
        return "Establecido estado activo="+str(active)+" en mongodb."

    def signing_today(self) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.signing_date(today)

    def signing_yesterday(self) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = today - timedelta(days=1)
        return self.signing_date(yesterday)

    def signing_date(self, date: str) -> str:
        ret = ""

        if (self.active):
            error = False
            gmt_offset = -self.tz_diff(date, self.utc, self.bru) # -1 winter, -2 summer

            # Sign morning

            self.data["params"]["args"][0]["check_in"] = date + " " + self.twodigits(7 + gmt_offset) + ":" + self.twodigits(randrange(11)) + ":" + self.twodigits(randrange(60))
            self.data["params"]["args"][0]["check_out"] = date + " " + self.twodigits(10 + gmt_offset) + ":" + self.twodigits(randrange(25, 35)) + ":" + self.twodigits(randrange(60))

            response = requests.request("POST", self.odoo_url, headers=self.headers, data=json.dumps(self.data), verify=False)
            if(response.status_code == 200 and not "error" in json.loads(response.text).keys()):
                print("Set morning time successful.")
                ret += "Se ha fichado la mañana correctamente.\n"
            else:
                print("ERROR: Set morning time unsuccessful.")
                ret += "ERROR: No se ha podido fichar la mañana.\n"
                self.send_telegram(date + " ERROR: No se ha podido fichar la mañana.")
                error = True
            print(response.text)
            print("------------")
            ret += response.text + "\n"
            ret += "--------------\n"

            # Sign afternoon

            self.data["params"]["args"][0]["check_in"] = date + " " + self.twodigits(10 + gmt_offset) + ":" + self.twodigits(randrange(50, 60)) + ":" + self.twodigits(randrange(60))
            self.data["params"]["args"][0]["check_out"] = date + " " + self.twodigits(15 + gmt_offset) + ":" + self.twodigits(randrange(25, 35)) + ":" + self.twodigits(randrange(60))

            response = requests.request("POST", self.odoo_url, headers=self.headers, data=json.dumps(self.data), verify=False)
            if(response.status_code == 200 and not "error" in json.loads(response.text).keys()):
                print("Set midday time successful.")
                ret += "Se ha fichado el mediodía correctamente.\n"
            else:
                print("ERROR: Set midday time unsuccessful.")
                ret += "ERROR: No se ha podido fichar el mediodía.\n"
                self.send_telegram(date + " ERROR: No se ha podido fichar el mediodía.")
                error = True
            print(response.text)
            print("------------")
            ret += response.text + "\n"
            ret += "--------------\n"

            if (error == False):
                self.send_telegram(date + ": Se te ha fichado correctamente.")

        else:
            ret += "ERROR: No se ha podido fichar. El bot está desactivado. Usa /activar para activarlo."

        return ret

    def get_mongodb_session_id(self) -> str:
        try:
            return self.mongodb_collection.find_one({'collection': 'params'})["session_id"]
        except:
            self.send_telegram("ERROR: No se ha podido obtener la session_id de mongodb.")
            return ""

    def set_mongodb_session_id(self, session_id: str) -> None:
        try:
            self.mongodb_collection.find_and_modify(
                query={'collection': 'params'},
                update={'$set': {'session_id': session_id}},
                new=True)
        except Exception as e:
            self.send_telegram("ERROR: No se ha podido establecer la session_id de mongodb.")
            self.send_telegram(str(e))

    def get_mongodb_active(self) -> bool:
        try:
            return self.mongodb_collection.find_one({'collection': 'active'})["active"]
        except:
            self.send_telegram("ERROR: No se ha podido obtener el parámetro 'active' de mongodb.")
            return None

    def set_mongodb_active(self, active: bool) -> None:
        try:
            self.mongodb_collection.find_and_modify(
                query={'collection': 'active'},
                update={'$set': {'active': active}},
                new=True)
        except Exception as e:
            self.send_telegram("ERROR: No se ha podido establecer el estado activo="+str(active)+" en mongodb.")
            self.send_telegram(str(e))

    def receive_telegram(self, msg: str) -> None:
        """Command bot using telegram."""
        msg_array = msg.split(" ")
        if (msg == "Activar"):
            self.set_active(True)
        elif (msg == "Desactivar"):
            self.set_active(False)
        elif (msg == "Fichar hoy"):
            if (self.active) == True:
                self.signing_today()
            else:
                self.send_telegram("ERROR: El bot está desactivado. Escribe <b>Activar</b> para activarlo.")
        elif (len(msg_array) == 2 and msg_array[0] == "Fichar" and len(msg_array[1].split("-")) == 3):
            if (self.active) == True:
                self.signing_date(msg_array[1])
            else:
                self.send_telegram("ERROR: El bot está desactivado. Escribe <b>Activar</b> para activarlo.")
        else:
            self.send_telegram("No entiendo lo que quieres decir. Los comandos reconocidos son:\n\n" +
                                        "<b>Activar</b>: activa el autofichaje.\n" +
                                        "<b>Desactivar</b>: desactiva el autofichaje.\n" +
                                        "<b>Fichar hoy</b>: ficha el día actual.\n" +
                                        "<b>Fichar año-mes-dia</b>: ficha el día indicado.\n")

    def send_telegram(self, text: str) -> None:
        try:
            self.updater.bot.send_message(chat_id=self.telegram_chat_id, text=text, parse_mode=ParseMode.HTML)
        except:
            pass
