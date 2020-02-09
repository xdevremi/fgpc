#!/usr/bin/env python3

import concurrent.futures
from datetime import datetime
import configparser
import webbrowser
import flickrapi

config = configparser.ConfigParser()
config.read('config.ini')

api_key = str(config.get('config', 'api_key'))
api_secret = str(config.get('config', 'api_secret'))

date_min = datetime.strptime(config.get('config', 'date_range_begin'), '%Y-%m-%d')
date_max = datetime.strptime(config.get('config', 'date_range_end'), '%Y-%m-%d')
timestamp_epoch = datetime(1970, 1, 1)
timestamp_min = int((date_min - timestamp_epoch).total_seconds())
timestamp_max = int((date_max - timestamp_epoch).total_seconds())

group_id = config.get('config', 'group_id')

max_workers = int(config.get('config', 'max_workers'))

page_begin = int(config.get('config', 'page_begin'))
page_end = int(config.get('config', 'page_end'))

flickr = flickrapi.FlickrAPI(api_key, api_secret)


def authenticate():
    print('Starting authentication...')
    if not flickr.token_valid(perms='write'):
        flickr.get_request_token(oauth_callback='oob')
        authorize_url = flickr.auth_url(perms='write')
        webbrowser.open_new_tab(authorize_url)
        verifier = str(input('Enter verifier code: '))
        flickr.get_access_token(verifier)
    print('Authentication complete.')


def print_pool_count():
    pool_count = int(flickr.groups.getInfo(group_id=group_id, format='parsed-json')['group']['pool_count']['_content'])
    print(f"Pool count: {pool_count:,d}")


def scan_pool(page=1):
    print(f'Requesting page {page}...')
    r = flickr.groups.pools.getPhotos(group_id=group_id, page=page, per_page=500, format='parsed-json')
    page = r['photos']['page']
    pages = r['photos']['pages']
    if page > pages:
        return
    print(f'Processing page {page} of {pages}.')
    matched_photo_ids = []
    for photo in r['photos']['photo']:
        timestamp = int(photo['dateadded'])
        if timestamp_min < timestamp < timestamp_max:
            matched_photo_ids.append(photo['id'])
    if matched_photo_ids:
        remove_photos(matched_photo_ids)


def remove_from_pool(photo_id):
    try:
        flickr.groups.pools.remove(group_id=group_id, photo_id=photo_id)
        print(f'Removed {photo_id}')
    except:
        print(f'Failed to remove {photo_id}')


def remove_photos(photo_ids):
    print(f'Using max_workers = {max_workers}')
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(remove_from_pool, photo_ids)


if __name__ == '__main__':
    authenticate()
    print_pool_count()
    for page in range(page_begin, page_end):
        scan_pool(page)
    print_pool_count()

