from os import system
from bot import Bot
from disnake.errors import HTTPException

from flask import Flask, render_template
from threading import Thread


import requests
import json

app = Flask("Wizardi", static_folder='./static')

@app.route('/')
@app.route('/Home.html')
def Home():
    return render_template('Home.html')

@app.route('/Terms.html')
async def Terms():
    return render_template('Terms.html')

@app.route('/Commands.html')
async def Commands():
    return render_template('Commands.html')

@app.route('/char_info/<name>')
def char_info(name):
    req = requests.get(f"https://superheroapi.com/api/2527790687387610/search/{name}")
    return json.loads(req.text)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404-Not-Found.html'), 404

def run():
    app.run(host='0.0.0.0', port=0)

def keep_alive():
    server = Thread(target=run)
    server.start()

system("clear")

bot = Bot()
config = bot.config

bot.remove_command("help")
bot.load_cogs("cogs")

try:
    bot.run(config.token)
except HTTPException as e:
    print("Bot has been temporarily banned by Discord")
    system("kill 1")
    print("Trying fix...")
    try:
        bot.run(config.token)
    except HTTPException as e:
        print("Failed, temporarily banned!")