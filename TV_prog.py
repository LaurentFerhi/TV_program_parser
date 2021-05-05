import requests
import bs4
import pandas as pd
from tqdm import tqdm
from datetime import date

def find_element(element, block, class_type, name):
    try:
        return element.find(block,{class_type: name}).getText().replace('\n','').replace('  ','')
    except AttributeError:
        return ''

def get_content(soup):
    data = {}
    idy = 0

    for element in tqdm(soup.find_all('div',{'class': 'mainBroadcastCard-infos'})):
        info = {}
        # Starting hour
        info['heure'] = find_element(element, 'div', 'class', 'mainBroadcastCard-startingHour')
        # Title
        info['titre'] = find_element(element, 'h3', 'class', 'mainBroadcastCard-title')
        # Subtitle
        info['sous_titre'] = find_element(element, 'div', 'class', 'mainBroadcastCard-subtitle')
        # Type
        info['type'] = find_element(element, 'div', 'class', 'mainBroadcastCard-type')
        # Duration
        info['duree'] = find_element(element, 'span', 'class', 'mainBroadcastCard-durationContent')
        # Duration
        info['new'] = find_element(element, 'div', 'class', 'mainBroadcastCard-new')
        # Duration
        info['live'] = find_element(element, 'div', 'class', 'mainBroadcastCard-live')
        # Duration
        info['rebroadcast'] = find_element(element, 'div', 'class', 'mainBroadcastCard-rebroadcast')

        # Description
        links = element.find('h3',{'class': 'mainBroadcastCard-title'})
        for a in links.find_all('a', href=True): 
            if a.text: 
                desc_url = a['href']
        soup_desc = bs4.BeautifulSoup(requests.get(desc_url).text,'html.parser')
        try:
            info['description'] = soup_desc.find(
                'p',
                {'class','synopsis-twoPart resume'}).getText().replace('\n','').replace('Lire la suite','')
        except AttributeError:
            info['description'] ='Aucune description'

        # insert into data
        data[idy] = info
        idy += 1

    ### Find and clean channels
    chaines = []
    for element in soup.find_all('h2',{'class': 'homeGrid-cardsChannelName'}):
        full_txt = element.getText().replace('\n','').replace('  ','')
        sr_only = element.find('span',{'class': 'sr-only'}).getText().replace('\n','').replace('  ','')
        for _ in range(2): # 2 evening time slots
            chaines.append(full_txt.replace(sr_only,''))  
            
    ### create and clean dataframe
    df = pd.DataFrame(data).T

    # append channels
    df['chaines'] = chaines
    #df = df.set_index('chaines')

    # merge broadcast columns
    df['diffusion'] = df.apply(lambda x: x['new']+x['live']+x['rebroadcast'],axis=1)
    df.drop(['new','live','rebroadcast'],axis=1,inplace=True)
    
    return df

def generate_report(df):
    with open('Programme.html','w',encoding='utf-8') as f:
        # header and internal css
        f.write('<!DOCTYPE html>\n<html>\n<head>\n<meta charset="UTF-8">\n \
            <meta http-equiv="Content-Language" content="fr-FR" />\n \
            <style> \
                body {font-family: Arial; background-color: #EEEEEE;}\n \
                h1 {color: #311B92;}\n \
                h2 {color: #0D47A1;}\n \
                h3 {color: #2196F3;}\n \
            </style>\n \
            <title>Programme TV</title>\n</head>\n')
        # body
        f.write('<body>\n<div>\n')
        f.write('<h1>Programme TV du {}</h1>\n'.format(date.today().strftime("%d/%m/%Y")))
        channel = ''
        for idx in list(df.index):
            extract = df.iloc[idx]
            # write channel
            if extract['chaines'] != channel:
                channel = extract['chaines']
                f.write('<hr>\n<h2>{}</h2>\n'.format(channel))
            # write main info
            f.write('<h3>{} - {} - {}</h3>\n'.format(
                extract['heure'],
                extract['titre'],
                extract['sous_titre'],
            ))
            # write meta
            f.write('<p><em>{} - {} - {}</em></p>\n'.format(
                extract['type'],
                extract['duree'],
                extract['diffusion'],
            ))
            # write desc
            f.write('<p>{}</p>\n'.format(
                extract['description'],
            ))
        # eof
        f.write('</div>\n</body>\n</html>')

if __name__ == '__main__':

    url = 'https://www.programme-tv.net/'
    page = requests.get(url)
    soup = bs4.BeautifulSoup(page.text,'html.parser')

    generate_report(get_content(soup))
    