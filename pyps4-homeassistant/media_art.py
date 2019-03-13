# -*- coding: utf-8 -*-
def get_ps_store_url(self, title, region):
    """Get URL for title search in PS Store."""
    import urllib
    import re

    regions = {'R1': 'US', 'R2': 'GB', 'R3': 'HK', 'R4': 'AU', 'R5': 'IN'}

    if region not in regions:
        _LOGGER.error('Region: %s is not valid', region)
        return
    else:
        region = regions[region]

    headers = {
        'User-Agent':
            'Mozilla/5.0 '
            '(Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'
    }

    if title is not None:
        title = re.sub('[^A-Za-z0-9]+', ' ', title)
        title = urllib.parse.quote(title.encode('utf-8'))
        _url = 'https://store.playstation.com/'\
            'valkyrie-api/en/{0}/19/faceted-search/'\
            '{1}?query={1}&platform=ps4'.format(region, title)

    url = [_url, headers]
    return url

def get_ps_store_data(self, title, title_id, region, url=None):
    """Store cover art from PS store in games map."""
    import requests
    import re

    if url is None:
        url = self.get_ps_store_url(title, region)
    req = None
    match_id = {}
    match_title = {}
    title = re.sub('[^A-Za-z0-9]+', ' ', title)
    type_list = ['Full Game', 'Game', 'PSN Game', 'Bundle', 'App']
    try:
        req = requests.get(url[0], headers=url[1])
        result = req.json()['included']
        if not result:
            title = title.split(' ')
            return self.get_ps_store_data(title[0], title_id, region, url=None)
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
            game = self._game(item)

            # Get Parent attr
            if 'parent' in game:
                if game['parent'] is not None:
                    has_parent = True
                    parent = game['parent']
                    parent_id = self._parse_id(parent['id'])
                    parent_title = parent['name']
                    parent_art = parent['url']
                    if parent_id == title_id:
                        return parent_title, parent_art

            if self._is_game_type(game, game_type):
                parse_id = self._parse_id(game['default-sku-id'])
                title_parse = game['name']

                # If passed SKU matches object SKU
                if parse_id == title_id:
                    cover_art = self._get_cover(game)
                    if cover_art is not None:

                        # If true likely a bundle, dlc, deluxe edition
                        if has_parent is False:
                            match_id.update({title_parse: cover_art})

                        # Most likely the intended item so return
                        if title.upper() == self._format_title(title_parse):
                            return title_parse, cover_art

                # Last resort filter if SKU wrong, but title matches.
                elif title.upper() == self._format_title(title_parse):
                    cover_art = self._get_cover(game)
                    if cover_art is not None:
                        if has_parent is False:
                            match_title.update({title_parse: cover_art})

    return self._get_similar(title, match_id, match_title)

def _game(self, item):
    """Create game object."""
    if 'attributes' in item:
        game = item['attributes']
        return game

def _is_game_type(self, game, game_type):
    """Check if item is a game and has SKU."""
    if 'game-content-type' in game and \
       game['game-content-type'] == game_type:
        if 'default-sku-id' in game:
            return True

def _parse_id(self, _id):
    """Parse SKU to simplified ID."""
    full_id = _id
    full_id = full_id.split("-")
    full_id = full_id[1]
    full_id = full_id.split("_")
    parse_id = full_id[0]
    return parse_id

def _format_title(self, title):
    """Format Title."""
    import re

    title = re.sub('[^A-Za-z0-9]+', ' ', title)
    title = title.upper()
    return title

def _get_cover(self, game):
    """Get cover art."""
    if 'thumbnail-url-base' in game:
        cover = 'thumbnail-url-base'
        cover_art = game[cover]
        return cover_art
    return

def _get_similar(self, title, match_id, match_title):
    """Return similar title."""
    if match_id:
        _LOGGER.info("Found similar titles: %s", match_id)
        for _title, url in match_id.items():
            if title.upper() in self._format_title(_title):
                _LOGGER.info("Using similar title: %s", _title)
                cover_art = url
                return _title, cover_art
    elif match_title:
        _LOGGER.warning(
            "Found matching titles with incorrect SKU: %s", match_title)
        for _title, url in match_title.items():
                _LOGGER.warning("Using matching title: %s", _title)
                cover_art = url
                return _title, cover_art
    return None, None
