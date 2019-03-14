# -*- coding: utf-8 -*-
"""Media Art Functions."""
import logging

_LOGGER = logging.getLogger(__name__)


def get_ps_store_url(title, region, reformat=False):
    """Get URL for title search in PS Store."""
    import urllib
    import re

    headers = {
        'User-Agent':
            'Mozilla/5.0 '
            '(Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'
    }

    if title is not None:
        if reformat is True:
            title = re.sub('[^A-Za-z0-9]+', ' ', title)
        title = urllib.parse.quote(title.encode('utf-8'))
        _url = 'https://store.playstation.com/'\
            'valkyrie-api/{0}/19/faceted-search/'\
            '{1}?query={1}&platform=ps4'.format(region, title)

    url = [_url, headers]
    return url

def get_ps_store_data(title, title_id, region, url=None, reformat=False):
    """Store cover art from PS store in games map."""
    import requests
    import re

    if url is None:
        url = get_ps_store_url(title, region)
    req = None
    match_id = {}
    match_title = {}
    if reformat is True:
        title = re.sub('[^A-Za-z0-9]+', ' ', title)
    type_list = ['Full Game', 'Game', 'PSN Game', 'Bundle', 'App']
    try:
        req = requests.get(url[0], headers=url[1])
        result = req.json()['included']
        if not result:
            title = title.split(' ')
            title = title[0]
            url = get_ps_store_url(title, region)
            req = requests.get(url[0], headers=url[1])
            result = req.json()['included']
    except requests.exceptions.HTTPError as warning:
        _LOGGER.warning("PS cover art HTTP error, %s", warning)
        return
    except requests.exceptions.RequestException as warning:
        _LOGGER.warning("PS cover art request failed, %s", warning)
        return

    # Filter through each item in search request

    # Filter each item by prioritized type
    for game_type in type_list:
        for item in result:
            has_parent = False

            # Set each item as Game object
            game = _game(item)

            # Get Parent attr
            if 'parent' in game:
                if game['parent'] is not None:
                    has_parent = True
                    parent = game['parent']
                    parent_id = _parse_id(parent['id'])
                    parent_title = parent['name']
                    parent_title = _format_title(parent_title, reformat)
                    parent_art = parent['url']
                    if parent_id == title_id:
                        _LOGGER.debug("Parent ID Match")
                        return parent_title, parent_art
                    if title.upper() == parent_title:
                        _LOGGER.debug("Parent Title Match")
                        return parent_title, parent_art
                    if title.upper() in parent_title:
                        _LOGGER.debug("Parent Similar Title Match")
                        return parent_title, parent_art

            if _is_game_type(game, game_type):
                parse_id = _parse_id(game['default-sku-id'])
                title_parse = game['name']

                # If passed SKU matches object SKU
                if parse_id == title_id:
                    cover_art = _get_cover(game)
                    if cover_art is not None:

                        # If true likely a bundle, dlc, deluxe edition
                        if has_parent is False:
                            match_id.update({title_parse: cover_art})

                        # Most likely the intended item so return
                        if title.upper() == _format_title(title_parse,
                                                          reformat):
                            _LOGGER.debug("Direct Match")
                            return title_parse, cover_art

                # Last resort filter if SKU wrong, but title matches.
                elif title.upper() == _format_title(title_parse, reformat):
                    cover_art = _get_cover(game)
                    if cover_art is not None:
                        if has_parent is False:
                            match_title.update({title_parse: cover_art})

    s_title, s_art = _get_similar(title, match_id, match_title, reformat)
    if s_title is None or s_art is None:
        if reformat is False:
            return get_ps_store_data(TITLE, TITLE_ID, region, reformat=True)
    return s_title, s_art


def _game(item):
    """Create game object."""
    if 'attributes' in item:
        game = item['attributes']
        return game


def _is_game_type(game, game_type):
    """Check if item is a game and has SKU."""
    if 'game-content-type' in game and \
       game['game-content-type'] == game_type:
        if 'default-sku-id' in game:
            return True


def _parse_id(_id):
    """Parse SKU to simplified ID."""
    try:
        full_id = _id
        full_id = full_id.split("-")
        full_id = full_id[1]
        full_id = full_id.split("_")
        parse_id = full_id[0]
    except IndexError:
        parse_id = "None"
    return parse_id


def _format_title(title, reformat):
    """Format Title."""
    import re

    if reformat is True:
        title = re.sub('[^A-Za-z0-9]+', ' ', title)
    title = title.upper()
    return title


def _get_cover(game):
    """Get cover art."""
    if 'thumbnail-url-base' in game:
        cover = 'thumbnail-url-base'
        cover_art = game[cover]
        return cover_art
    return


def _get_similar(title, match_id, match_title, reformat):
    """Return similar title."""
    if match_id:
        for _title, url in match_id.items():
            if title.upper() in _format_title(_title, reformat):
                cover_art = url
                _LOGGER.debug("Similar Title Match")
                return _title, cover_art
    elif match_title:
        for _title, url in match_title.items():
                cover_art = url
                _LOGGER.debug("Wrong ID Match")
                return _title, cover_art
    return None, None
