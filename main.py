import requests

from googletrans import Translator

# https://www.themealdb.com/api.php
# https://pypi.org/search/?q=translator
# pip install googletrans==4.0.0-rc1
url = "http://www.themealdb.com/api/json/v1/1/search.php?s=tofu"
url1 = "http://www.themealdb.com/api/json/v1/1/random.php"
url2 = "http://www.themealdb.com/api/json/v1/1/search.php?f=a"

response = requests.request("GET", url)
r1 = requests.request("GET", url1)
r2 = requests.request("GET", url2)
# Преобразуем ответ в json-объект
json_response = response.json()
json1_response = r1.json()
j2 = r2.json()
# Получаем первый топоним из ответа геокодера.
# Согласно описанию ответа, он находится по следующему пути:
toponym = json_response['meals'][0]['strInstructions']
x = json1_response

# print(toponym)

translator = Translator()
a= translator.translate(toponym, dest='ru').text
print(a)
# print(j2)
