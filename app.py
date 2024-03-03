
from flask import Flask, render_template, request
import os
import requests
import json

# Mistal AI & Open AI
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from openai import OpenAI

# AWS Dynamodb
import boto3

from dotenv import load_dotenv
print(load_dotenv())

language='fr'
text_completion_choice = 'openai'

app = Flask(__name__, template_folder='.')

client_mistalai = MistralClient(api_key=os.environ["MISTRALAI_API_KEY"])
client_openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

region_aws='eu-west-3'
table_name = 'definitions'
client_dynamodb = boto3.client('dynamodb',aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"], 
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"], region_name=region_aws)

# Home route
@app.route('/')
def home():
    return render_template('index.html')

# Submission route
@app.route('/', methods=['POST'])
def define_word():
    word = request.form['word'].lower()
    if len(word)<2:
        return render_template('index.html')

    if not word_exists(word, language):
        definition = generate_definition(word)
        prompt_image = generate_prompt_image_generation(word, definition)
        image_url = generate_image(prompt_image)
        caption = generate_image_caption(prompt_image, word, definition)
        add_item_to_db(word, definition, language, image_url, caption)

    else:
        item = get_word(word, language)['Items'][0]
        definition = item['definition']['S']
        image_url = item['image_url']['S']
        caption = item['caption']['S']

    return render_template('index.html', validite="Le mot "+word+" est valide au scrabble.", 
        definition=definition, image=image_url, image_caption=caption)

### GenAi functions

def text_completion(prompt):
    if text_completion_choice=='openai':
        return client_openai.chat.completions.create(
            model="gpt-4", 
            messages=[{"role": "user", "content": prompt}]
        )
    elif text_completion_choice=='mistralai':
        return client_mistalai.chat(
            model="open-mistral-7b",
            messages=[ChatMessage(role="user", content=prompt)],
        )

def generate_definition(word):
    chat_response = text_completion(prompt_definition(word))
    return chat_response.choices[0].message.content

def prompt_definition(word):
    return '''Tu es un académicien français qui donne des définitions à des mots français en français. 
    Fais comme si le mot '''+word+''' existait. Maintenant, définis ce mot en utilisant la syntaxe suivante : 
    <MOT> : (<TYPE>) (<ORIGINE>) <DEFINITION>. <MOT> est '''+word+''', <TYPE> est soit un nom, 
    verbe, ajectif, adverbe, ou pronom, <ORIGINE> est une courte phrase qui donne l'origine du mot, par exemple "provient du latin", 
    mais peut aussi être breton, basque, occitan par exemple, et <DEFINITION> est la définition que tu donnes à ce mot.
    La syntaxe est donc <MOT> : (<TYPE>) (<ORIGINE>) <DEFINITION>. A noter que <TYPE>, <ORIGINE> et <DEFINITION> 
    doivent être cohérents entre eux. Retire toutes les balises < et > de la définition.'''

def generate_image(prompt_image):
    response = client_openai.images.generate(
        model="dall-e-3",
        prompt=prompt_image,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url
    return image_url

def generate_prompt_image_generation(word, definition):
    chat_response = text_completion('''Emploie le terme : '''+word+''' qui a la définition 
            suivante : '''+definition+''' dans une phrase. La phrase doit être plausible, comme sortie 
            d'un ouvrage ou d'un journal, en respectant au mieux la définition du mot.''')
    return chat_response.choices[0].message.content

def generate_image_caption(prompt_image, word, definition):
    chat_response = text_completion('''Tu es un académicien français. Tourne cette phrase
            en français : '''+prompt_image+''' en faisant en sorte que la phrase soit comme le sous-titre
            en langue française d'une image qui représente cette phrase. La phrase en français doit absolument 
            employer le mot '''+word+''' qui a la définition suivante : '''+definition+'''. ''')
    return chat_response.choices[0].message.content[:chat_response.choices[0].message.content.find('.')]

# def prompt_image(word, definition):
#     return "Génère une image pour ce mot : "+word+" qui a la définition suivante : "+definition

### database functions
def word_exists(word, language):
    response = client_dynamodb.query(
        TableName=table_name,
        KeyConditionExpression='word = :word AND #dynobase_language = :language',
        ExpressionAttributeValues={
            ':word': {'S': word},
            ':language': {'S': language},
        },
        ExpressionAttributeNames={
            '#dynobase_language': 'language'
        }
    )
    return len(get_word(word, language)['Items'])>0

def get_word(word, language):
    return client_dynamodb.query(
        TableName=table_name,
        KeyConditionExpression='word = :word AND #dynobase_language = :language',
        ExpressionAttributeValues={
            ':word': {'S': word},
            ':language': {'S': language},
        },
        ExpressionAttributeNames={
            '#dynobase_language': 'language'
        }
    )

def add_item_to_db(word, definition, language, image_url, caption):
    item = {
        'word':{'S':word},
        'definition':{'S':definition},
        'language':{'S': language},
        'image_url':{'S': image_url},
        'caption':{'S': caption},
    }
    response = client_dynamodb.put_item(
        TableName='definitions', 
        Item=item
    )


# dynamodb = boto3.resource('dynamodb',aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"], 
#     aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"], region_name=region_aws)
# table = dynamodb.Table('definitions')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')