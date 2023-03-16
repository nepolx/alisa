import requests
from translator import translator

# https://www.themealdb.com/api.php
# https://pypi.org/search/?q=translator
url = "http://www.themealdb.com/api/json/v1/1/search.php?s=Arrabiata"
url1 = "http://www.themealdb.com/api/json/v1/1/random.php"

response = requests.request("GET", url)
r1 = requests.request("GET", url1)
# Преобразуем ответ в json-объект
json_response = response.json()
json1_response = r1.json()
# Получаем первый топоним из ответа геокодера.
# Согласно описанию ответа, он находится по следующему пути:
toponym = json_response['meals'][0]['strInstructions']
x = json1_response
print(x)
print(toponym)
a = translator.Translator('en', 'fr', 'mother')

