import requests, re, os
import pytesseract as pt
import pdf2image as pdf
from bs4 import BeautifulSoup
from pynput import keyboard
from ordinance import Ordinance, OrdinanceDAO

def on_press(key):
    if key == keyboard.Key.f1:
        os._exit(1)

def start_keyboard_listener():
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

def get_http_response(url):
    return requests.get(url, headers = {'User-Agent': 'Opera/9.80 (Windows NT 6.1; WOW64) Presto/2.12.388 Version/12.18'})

def get_links(response):
    page = BeautifulSoup(response.content, 'html.parser')
    return page.find_all('a', class_='state-published')

def get_next_page(response):
    page = BeautifulSoup(response.content, 'html.parser')
    return page.find('a', class_='proximo')

def get_file_link(response):
    page = BeautifulSoup(response.content, 'html.parser')
    return page.find(href=re.compile('pdf'))

def get_ordinance(link):
    ordinance = Ordinance(link['href'])
    if not OrdinanceDAO.exists(ordinance):
        response = get_http_response(link['href'])
        ordinance.content = extract_text(response.content)
    return ordinance

def extract_text(file):
    start_string = 'MINISTÉRIO DA EDUCAÇÃO'
    end_string = 'Documento assinado eletronicamente por'
    pages = pdf.convert_from_bytes(pdf_file=file)
    content = ''
    for page in pages:
        page_content = pt.image_to_string(page, lang='por', config='--psm 4')
        if start_string in page_content:
            content += page_content[page_content.find(start_string):]
        else:
            content += page_content
        if end_string in content:
            break
    return re.sub(r'\n\s*\n', '\n\n', content)

if __name__ == '__main__':
    print("Press <F1> to finish!\n\n ")
    start_keyboard_listener()
    url = ('http://cdd.iff.edu.br/@@busca?&sort_order=reverse&portal_type:list=portaria&sort_on=Date')
    while True:
        current_page = get_http_response(url)
        links = get_links(current_page)
        for link in links:
            response = get_http_response(link['href'])
            file_link = get_file_link(response)
            print('Downloading', file_link.string, end = '')
            ordinance = get_ordinance(file_link)
            OrdinanceDAO.insert(ordinance)
        next_page = get_next_page(current_page)
        if next_page == None:
            print('Downloads completed!')
            break
        else:
            url = next_page['href']
