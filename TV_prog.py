import requests
import bs4
import pandas as pd
from tqdm import tqdm
from datetime import date
import os

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
        # Heure début
        info['heure'] = find_element(element, 'div', 'class', 'mainBroadcastCard-startingHour')
        # Titre
        info['titre'] = find_element(element, 'h3', 'class', 'mainBroadcastCard-title')
        # Sous-titre
        info['sous_titre'] = find_element(element, 'div', 'class', 'mainBroadcastCard-subtitle')
        # Type
        info['type'] = find_element(element, 'div', 'class', 'mainBroadcastCard-type')
        # Durée
        info['duree'] = find_element(element, 'span', 'class', 'mainBroadcastCard-durationContent')
        # Inédit
        info['new'] = find_element(element, 'div', 'class', 'mainBroadcastCard-new')
        # Direct
        info['live'] = find_element(element, 'div', 'class', 'mainBroadcastCard-live')
        # Redif
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
            
        # Autres ibfos
        info['genre'] = find_element(soup_desc, 'div', 'class', 'overview-overviewSubtitle')
        
        # Résumé (casting)
        if info['type'] == 'Cinéma':
            try:
                info['casting'] = soup_desc.find("meta",  property='og:description')['content'].split('...')[0]
            except AttributeError:
                info['casting'] =''   
        else:
            info['casting'] ='' 
        
        # Insertion dans data
        data[idy] = info
        idy += 1

    ### Trouve et clean les chaines
    chaines = []
    for element in soup.find_all('h2',{'class': 'homeGrid-cardsChannelName'}):
        full_txt = element.getText().replace('\n','').replace('  ','')
        sr_only = element.find('span',{'class': 'sr-only'}).getText().replace('\n','').replace('  ','')
        for _ in range(2): # 2 evening time slots
            chaines.append(full_txt.replace(sr_only,'')) 
            
    ### Import des images
    img_link = []
    for element in soup.find_all('div',{'class': 'pictureTagGenerator pictureTagGenerator-ratio-5-7'}):
        if element.find('img')['src'].startswith('https'):
            img_link.append(element.find('img')['src'])
        elif element.find('img')['data-src'].startswith('https'):
            img_link.append(element.find('img')['data-src'])
        else:
            img_link.append('no image')
    # Coupe la liste à la longeuer de la liste chaines (les autres images ne sont pas pertinentes)
    img_link = img_link[:len(chaines)]
    
    ### Création dataframe
    df = pd.DataFrame(data).T

    # append des chaines et des liens d'image
    df['chaines'] = chaines
    df['images'] = img_link

    # merge des colonnes de diffusion
    df['diffusion'] = df.apply(lambda x: x['new']+x['live']+x['rebroadcast'],axis=1)
    df.drop(['new','live','rebroadcast'],axis=1,inplace=True)
    
    return df

def generate_report(df,name_out):
    with open(name_out,'w',encoding='utf-8') as f:
        # header et css
        f.write('<!DOCTYPE html>\n<html>\n<head>\n<meta charset="UTF-8">\n \
            <meta http-equiv="Content-Language" content="fr-FR" />\n \
            <style> \
                body {font-family: Arial; background-color: #EEEEEE;}\n \
                h1 {color: #311B92;}\n \
                h2 {color: #0D47A1;}\n \
                h3 {color: #2196F3;text-decoration: underline;}\n \
                h4 {color: #808080;}\n \
                img {border-radius: 5px;}\n \
            </style>\n \
            <title>Programme TV</title>\n</head>\n')
        # body
        f.write('<body>\n<div>\n')
        f.write('<h1>Programme TV du {}</h1>\n'.format(date.today().strftime("%d/%m/%Y")))
        channel = ''
        for idx in list(df.index):
            extract = df.iloc[idx]
            # Infos chaines 
            if extract['chaines'] != channel:
                channel = extract['chaines']
                f.write('<hr>\n<h2>{}</h2>\n'.format(channel))
                # première partie de soirée
                f.write('<h3>{} - {} - {}</h3>\n'.format(
                    extract['heure'],
                    extract['titre'],
                    extract['sous_titre'],
                ))
            # sinon infos en plus petit (deuxième partie de soirée)
            else:
                f.write('<h4>{} - {} - {}</h4>\n'.format(
                    extract['heure'],
                    extract['titre'],
                    extract['sous_titre'],
                ))

            # Images
            f.write('<img src="{}" alt="image" />\n'.format(extract['images']))
            
            # infos meta
            f.write('<p><em>{} - {} - {} - {} - {}</em></p>\n'.format(
                extract['type'],
                extract['duree'],
                extract['diffusion'],
                extract['genre'],
                extract['casting'],
            ))
            
            # desc
            f.write('<p>{}</p>\n'.format(
                extract['description'],
            ))
        # eof
        f.write('</div>\n</body>\n</html>')

if __name__ == '__main__':

    name_out = 'Programme.html'
    # Si la dernière date de modif n'est pas aujourd'hui ou que le .html n'exite pas
    if name_out in os.listdir():
        if date.fromtimestamp(os.path.getmtime(name_out)) == date.today():
            pass
    else:
        url = 'https://www.programme-tv.net/'
        page = requests.get(url)
        soup = bs4.BeautifulSoup(page.text,'html.parser')

        df = get_content(soup)
        generate_report(df,name_out)
    