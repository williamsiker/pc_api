import httpx
from bs4 import BeautifulSoup


# response = requests.get('https://kenkoooo.com/atcoder/atcoder-api/v3')
# response = requests.get("https://atcoder.jp")
# print(response.status_code)
# print(response.text)

# Usando beautuifulSoup para analizar el HTML
url = "https://atcoder.jp"
res = httpx.get(url)
soup = BeautifulSoup(res.text, 'html.parser')

# Encontrar todos los elementos por etiqueta, clase, id de html y extraer el texto
quotes = soup.find_all(name='h3', class_="panel-title")
for q in quotes:
    print(q.text)
