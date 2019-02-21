"""
Support for PlayStation 4 console.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.ps4/
"""
from datetime import timedelta
import logging
import socket
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
import homeassistant.util as util
from homeassistant.components.media_player import (
    ENTITY_IMAGE_URL, MEDIA_TYPE_MUSIC, MediaPlayerDevice,
    SUPPORT_SELECT_SOURCE, SUPPORT_STOP, SUPPORT_TURN_OFF, SUPPORT_TURN_ON,
)
from homeassistant.components.ps4 import DOMAIN as PLATFORM
from homeassistant.const import (
    ATTR_ENTITY_ID, ATTR_COMMAND, CONF_HOST, CONF_NAME, CONF_REGION,
    CONF_TOKEN, STATE_IDLE, STATE_OFF, STATE_PLAYING, STATE_UNKNOWN,
)
from homeassistant.util.json import load_json, save_json


DEPENDENCIES = ['ps4']
REQUIREMENTS = ['pyps4-homeassistant==0.2.5']

SERVICE_COMMAND = 'send_command'
_LOGGER = logging.getLogger(__name__)

SUPPORT_PS4 = SUPPORT_TURN_OFF | SUPPORT_TURN_ON | \
    SUPPORT_STOP | SUPPORT_SELECT_SOURCE


DEFAULT_NAME = "PlayStation 4"
DEFAULT_REGION = 'R1'
ICON = 'mdi:playstation'
GAMES_FILE = '.ps4-games.json'
MEDIA_IMAGE_DEFAULT = None

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=3)
MIN_TIME_BETWEEN_FORCED_SCANS = timedelta(seconds=5)

REGIONS = ('R1', 'R2', 'R3', 'R4', 'R5')

COMMANDS = (
    'up',
    'down',
    'right',
    'left',
    'enter',
    'back',
    'option',
    'ps',
    'key_off',
    'cancel',
    'open_rc',
    'close_rc',
)

PS4_COMMAND_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.comp_entity_ids,
    vol.Required(ATTR_COMMAND): vol.In(list(COMMANDS))
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Log Warning if PS4 in configuration.yaml."""
    if config.get(PLATFORM, config) is not None:
        msg = """Configuration for PlayStation 4 using
            'configuration.yaml' is not supported.
            Use integrations to add PlayStation 4."""
        _LOGGER.warning(msg)
        return True


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up PS4 from a config entry."""
    config = config_entry

    await _async_setup_platform(hass, config, async_add_devices, None)


async def _async_setup_platform(hass, config, async_add_devices,
                                discovery_info=None):
    """Set up PS4 Platform."""
    import pyps4_homeassistant as pyps4

    games_file = hass.config.path(GAMES_FILE)
    creds = config.data[CONF_TOKEN]

    for device in config.data['devices']:
        host = device.get(CONF_HOST)
        region = device.get(CONF_REGION)
        name = device.get(CONF_NAME)
        ps4 = pyps4.Ps4(host, creds)
        hass.data[PLATFORM] = PS4Data()
        async_add_devices([
            PS4Device(name, config, host, region, ps4, games_file)], True)

    async def async_service_handle(hass):
        """Handle for services."""
        async def async_service_command(call):
            entity_ids = call.data.get(ATTR_ENTITY_ID)
            command = call.data.get(ATTR_COMMAND)
            for device in hass.data[PLATFORM].devices:
                device = device
                if device.entity_id in entity_ids:
                    await device.async_send_command(command)

        hass.services.async_register(
            PLATFORM, SERVICE_COMMAND, async_service_command,
            schema=PS4_COMMAND_SCHEMA)

    await async_service_handle(hass)


class PS4Data():
    """Init Data Class."""

    def __init__(self):
        """Init Class."""
        self.devices = []


class PS4Device(MediaPlayerDevice):
    """Representation of a PS4."""

    def __init__(self, name, config, host, region, ps4, games_file):
        """Initialize the ps4 device."""
        self._config = config
        self._ps4 = ps4
        self._host = host
        self._name = name
        self._region = region
        self._state = STATE_UNKNOWN
        self._games_filename = games_file
        self._media_content_id = None
        self._media_title = None
        self._media_image = None
        self._source = None
        self._games = None
        self._source_list = None
        self._retry = 0
        self._info = None
        self._unique_id = None

    async def async_added_to_hass(self):
        """Subscribe PS4 events."""
        self.hass.data[PLATFORM].devices.append(self)

    @util.Throttle(MIN_TIME_BETWEEN_SCANS, MIN_TIME_BETWEEN_FORCED_SCANS)
    async def async_update(self):
        """Retrieve the latest data."""
        try:
            status = await self.hass.async_add_executor_job(
                self._ps4.get_status)
            if self._info is None and status is not None:
                await self.async_get_device_info(self._config, status)
        except socket.timeout:
            status = None
        if status is not None:
            self._retry = 0
            if status.get('status') == 'Ok':
                titleid = status.get('running-app-titleid')
                name = status.get('running-app-name')
                if titleid and name is not None:
                    self._state = STATE_PLAYING
                    if self._media_content_id != titleid:
                        self._media_content_id = titleid
                        self.hass.async_create_task(
                            self.async_get_title_data(titleid, name))
                else:
                    await self.async_idle()
            else:
                await self.async_state_off()
        elif self._retry > 5:
            await self.async_state_unknown()
        else:
            self._retry += 1
            self.schedule_update_ha_state()

    async def async_idle(self):
        """Set states for state idle."""
        await self.async_no_title()
        self._state = STATE_IDLE
        if self._games is None:
            await self.hass.async_create_task(self.async_update_list())

    async def async_state_off(self):
        """Set states for state off."""
        await self.async_no_title()
        self._state = STATE_OFF
        self.schedule_update_ha_state()

    async def async_state_unknown(self):
        """Set states for state unknown."""
        await self.async_no_title()
        self._state = STATE_UNKNOWN
        _LOGGER.debug("PS4 could not be reached")
        self._retry = 0
        self.schedule_update_ha_state()

    async def async_no_title(self):
        """Update if there is no title."""
        self._media_title = None
        self._media_content_id = None
        self._source = None

    async def async_get_title_data(self, titleid, name):
        """Get PS Store Data."""
        app_name = None
        art = None
        try:
            app_name, art = await self.hass.async_add_executor_job(
                self._ps4.get_ps_store_data, name, titleid, self._region)
        except TypeError:
            _LOGGER.error(
                "Could not find data in region: %s for PS ID: %s",
                self._region, titleid)
        finally:
            self._media_title = app_name or name
            self._source = self._media_title
            self._media_image = art
            await self.hass.async_create_task(self.async_update_list())

    async def async_update_list(self):
        """Update Game List, Correct data if different."""
        if self._games is None:
            self._games = await self.async_load_games()
        if self._games is not None:
            if self._media_content_id in self._games:
                store = self._games[self._media_content_id]
                if store != self._media_title:
                    self._games.pop(self._media_content_id)
            if self._media_content_id not in self._games:
                await self.async_add_games(
                    self._media_content_id, self._media_title)
                self._games = await self.async_load_games()
            self._source_list = list(sorted(self._games.values()))
            self.schedule_update_ha_state()

    async def async_load_games(self):
        """Load games for sources."""
        g_file = self._games_filename
        try:
            games = await self.hass.async_add_executor_job(load_json, g_file)
            return games
        except FileNotFoundError:
            _LOGGER.info("Could not find file: %s", g_file)
            games = {}
            await self.async_save_games(games)
            await self.async_load_games()

    async def async_save_games(self, games):
        """Save games to file."""
        g_file = self._games_filename
        try:
            await self.hass.async_add_executor_job(save_json, g_file, games)
        except OSError as error:
            _LOGGER.error("Could not save game list, %s", error)

    async def async_add_games(self, titleid, app_name):
        """Add games to list."""
        games = self._games
        if titleid is not None and titleid not in games:
            game = {titleid: app_name}
            _LOGGER.info("Adding %s to source list", game)
            games.update(game)
            await self.async_save_games(games)

    async def async_get_device_info(self, config, status):
        """Return device info for registry."""
        _sw_version = status['system-version']
        _sw_version = _sw_version[1:4]
        sw_version = _sw_version[0] + '.' + _sw_version[1:]
        self._info = {
            'config_entry_id': config.entry_id,
            'name': status['host-name'],
            'model': 'PlayStation 4',
            'identifiers': {
                (PLATFORM, status['host-id'])
            },
            'manufacturer': 'Sony Interactive Entertainment Inc.',
            'sw_version': sw_version
        }
        self._unique_id = status['host-id']

    @property
    def device_info(self):
        """Return information about the device."""
        return self._info

    @property
    def unique_id(self):
        """Return Unique ID for entity."""
        return self._unique_id

    @property
    def entity_picture(self):
        """Return picture."""
        if self._state == STATE_OFF:
            return None

        image_hash = self.media_image_hash
        if image_hash is not None:
            return ENTITY_IMAGE_URL.format(
                self.entity_id, self.access_token, image_hash)

        if self._media_content_id is None:
            return None

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def icon(self):
        """Icon."""
        return ICON

    @property
    def media_content_id(self):
        """Content ID of current playing media."""
        return self._media_content_id

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return MEDIA_TYPE_MUSIC

    @property
    def media_image_url(self):
        """Image url of current playing media."""
        if self._media_content_id is None:
            return MEDIA_IMAGE_DEFAULT
        try:
            return self._media_image
        except KeyError:
            return MEDIA_IMAGE_DEFAULT

    @property
    def media_title(self):
        """Title of current playing media."""
        return self._media_title

    @property
    def supported_features(self):
        """Media player features that are supported."""
        return SUPPORT_PS4

    @property
    def source(self):
        """Return the current input source."""
        return self._source

    @property
    def source_list(self):
        """List of available input sources."""
        return self._source_list

    async def async_turn_off(self):
        """Turn off media player."""
        await self.hass.async_add_executor_job(self._ps4.standby)
        self.schedule_update_ha_state()

    async def async_turn_on(self):
        """Turn on the media player."""
        await self.hass.async_add_executor_job(self._ps4.wakeup)
        self.schedule_update_ha_state()

    async def async_media_pause(self):
        """Send keypress ps to return to menu."""
        await self.hass.async_add_executor_job(self._ps4.remote_control, 'ps')

    async def async_media_stop(self):
        """Send keypress ps to return to menu."""
        await self.hass.async_add_executor_job(self._ps4.remote_control, 'ps')

    async def async_select_source(self, source):
        """Select input source."""
        for title_id, game in self._games.items():
            if source == game:
                _LOGGER.debug(
                    "Starting PS4 game %s (%s) using source %s",
                    game, title_id, source)
                await self.hass.async_add_executor_job(
                    self._ps4.start_title, title_id, self._media_content_id)
                self.schedule_update_ha_state()
                return

    async def async_send_command(self, command):
        """Send Button Command."""
        await self.hass.async_add_executor_job(
            self._ps4.remote_control, command)
