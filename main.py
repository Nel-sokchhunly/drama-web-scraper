from bs4 import BeautifulSoup
import requests
import re
from pymongo import MongoClient
import schedule
import time
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

# dramacool
base_url = 'https://www2.dramacool.sk'
drama_detail_base_url = 'https://www2.dramacool.sk/drama-detail/'
drama_search_base_url = 'https://www2.dramacool.sk/search?type=movies&keyword='


def scrape_drama_info(drama_title):
    """
    this functions uses to fetch the drama information from the dramacool website.

    :param drama_title:String = it is the title query of the drama that will be fetch
    
    :return:    title:String = the official title of the drama
    :return:    query_title:String = the query title to use for link
    :return:    other_name:List<String> = list contains other alternative names of the drama
    :return:    image_info:Object{src, alt} = it is an object of the drama poster info
    :return:    description:List<String> = it is a list of drama description paragraph
    :return:    status:String = the status of the drama
    :return:    genre:list<String> = the list of genre of this drama
    :return:    trailer_embed_link:String = url string of the trailer embed youtube link
    :return:    episodes:List<Object> = list of existing episode
    """
    try:
        drama_information = {
            'title': '',
            'query_title': drama_title,
            'other_name': [],
            'image_info': {},
            'description': [],
            'status': '',
            'genre': [],
            'trailer_embed_link': '',
            'episodes': [],
            'last_updated': datetime.now()
        }

        html_file = requests.get(f'{drama_detail_base_url}{drama_title}').text

        drama_soup = BeautifulSoup(html_file, 'lxml')
        drama_detail = drama_soup.find('div', class_='details')
        # drama-info finds all p tag inside drama_details
        drama_info = drama_detail.find_all('p')

        drama_information['title'] = drama_detail.find('h1').text  # title of the drama
        # include the image link and alt text
        drama_information['image_info'] = drama_detail.find('div',
                                                            class_='img').img.attrs

        # description
        # description is a list because description can contains multiple paragraphs
        # so each element inside the list represent a paragraph
        for element in drama_info:
            # description
            if re.search(r'.+[.]$', element.get_text()):
                drama_information['description'].append(element.text)
            # drama status and genre
            for text in element.stripped_strings:
                clean_text = repr(text).lower()
                if 'status' in clean_text:
                    drama_information['status'] = drama_info[
                        drama_info.index(element)].span.next_sibling.strip().replace(';', '')
                if 'genre' in clean_text:
                    genre_list_tag = drama_info[drama_info.index(element)].find_all('a')
                    for genre in genre_list_tag:
                        drama_information['genre'].append(genre.get_text())

                # find all available episodes
        episodes_list_wrapper = drama_soup.find('ul', class_="list-episode-item-2 all-episode")
        episodes_list = episodes_list_wrapper.find_all('a', class_='img')
        for episode in episodes_list:
            ep_title = episode.find('h3').text
            link = episode['href']
            upload_time = episode.find('span', class_='time').text
            ep_type = episode.find('span', class_='type').text

            episode_html = requests.get(f'{base_url}{link}').text
            episode_soup = BeautifulSoup(episode_html, 'lxml')
            video_wrapper = episode_soup.find('div', class_='watch_video watch-iframe')
            ep_streaming_link = 'https:' + video_wrapper.find('iframe')['src']

            drama_information['episodes'].append({
                'title': ep_title,
                'link': f'{base_url}{link}',
                'ep_streaming_link': ep_streaming_link,
                'upload_time': upload_time,
                'type': ep_type
            })

        # reversing the list so the list start from ep 1 instead of the latest episode
        drama_information['episodes'].reverse()

        # get trailer link
        trailer_div = drama_soup.find('div', class_='trailer')
        if trailer_div:
            drama_information['trailer_embed_link'] = trailer_div.find('iframe')['src']

        # other name
        other_name_wrapper = drama_detail.find('p', class_='other_name')
        others_name_list = other_name_wrapper.find_all('a')
        for a_tag in others_name_list:
            drama_information['other_name'].append(a_tag['title'].strip())

        return drama_information
    except Exception:
        return None


def job():
    # connecting database
    client = MongoClient(
        f'mongodb+srv://admin:{os.environ.get("DB_PASSWORD")}@cluster0.smkuq.mongodb.net/myFirstDatabase?retryWrites=true&w=majority')
    db = client['drama-list']
    user_object_docs = db['user-drama-list'].find()  # get all document inside the user-drama-list collection
    drama_list_col = db['drama']

    print('Getting all the drama to scrape and adding it to the scrape list...')
    drama_list = set()
    for item in user_object_docs:
        for drama in item['drama_list']:
            drama_list.add(drama)
    print("Done inserting drama name into fetching list!")

    print("Executing the scarper function...")
    scraped_drama = []
    for drama in drama_list:
        print(f'Scraping {drama}...')
        data = scrape_drama_info(drama)
        if data is not None:
            scraped_drama.append(data)
            print(f'Done scraping {drama}')
        else:
            print(f'Something goes wrong with scarping {drama}\nproceed to another drama')
    print('Done scarping!')

    # adding new scraped data into the database
    drama_stored_in_database = list(drama_list_col.find({}, {'title': 1}))
    # getting the list of drama that stored in the database to validate
    # either the scraped drama has already exist in the database
    drama_names = list(map(lambda x: x['title'], drama_stored_in_database))
    if len(scraped_drama) > 0:
        print('Adding new scrape data into the database...')
        for drama in scraped_drama:
            # checking if the drama already exist in the database
            # if so, just update the document instead of adding a new one
            if drama['title'] in drama_names:
                drama_list_col.update_one(
                    {'title': drama['title']},
                    {'$set': {
                        'episodes': drama['episodes'],
                        'last_updated': drama['last_updated']
                    }}
                )
                # this line mean the drama doesn't exist in the database
                # then we add it as a new document
            else:
                drama_list_col.insert_one(drama)


# TODO: create a job to run through the stored drama list and delete
#       those that doesn't have in the drama-list in the user documents
schedule.every().hour.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)
