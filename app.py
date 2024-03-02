# app.py

from flask import Flask, render_template, request
import os
import requests
import json
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from openai import OpenAI
from dotenv import load_dotenv

app = Flask(__name__, template_folder='.')
load_dotenv()
client_mistalai = MistralClient(api_key=os.environ["MISTRALAI_API_KEY"])
client_openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
messages = [ChatMessage(role="user", content="What is the best French cheese?")]
model="open-mistral-7b"

# Home route
@app.route('/')
def home():
    return render_template('index.html')

# Route for handling form submission
@app.route('/', methods=['POST'])
def define_word():
    word = request.form['word'].lower()
    definition=generate_definition(word)
    return render_template('index.html', definition=definition, image=generate_image(word, definition))

# Function to generate definition for the word
def generate_definition(word):
    chat_response = client_mistalai.chat(
        model=model,
        messages=[ChatMessage(role="user", content=prompt_definition(word))],
    )
    return chat_response.choices[0].message.content

def prompt_definition(word):
    return '''Tu es un académicien français qui donne des définitions à des mots français en français. 
    Fais comme si le mot "+word+" existait. Maintenant, définis ce mot en utilisant la syntaxe suivante : 
    <MOT> : (<TYPE>) (<ORIGINE>) <DEFINITION>. <MOT> est '''+word+''', <TYPE> est soit un nom, 
    verbe, ajectif, adverbe, ou pronom, <ORIGINE> est une courte phrase qui donne l'origine du mot, par exemple "provient du latin", 
    mais peut aussi être breton, basque, occitan par exemple, et <DEFINITION> est la définition que tu donnes à ce mot.
    La syntaxe est donc <MOT> : (<TYPE>) (<ORIGINE>) <DEFINITION>. A noter que <TYPE>, <ORIGINE> et <DEFINITION> 
    doivent être cohérents entre eux.'''

def generate_image(word, definition):
    response = client_openai.images.generate(
        model="dall-e-3",
        prompt=prompt_image(word, definition),
        size="1024x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url
    print(image_url)
    return image_url

def prompt_image(word, definition):
    return "Génère une image pour ce mot : "+word+" qui a la définition suivante : "+definition

if __name__ == '__main__':
    app.run(debug=True)