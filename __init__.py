"""Support for LightsControl logic"""
import logging
import voluptuous as vol

from homeassistant.const import (
    EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP)
# TODO: check if some CONF constants can be imported from homeassistant.const import CONF_XXX
import homeassistant.helpers.config_validation as cv
from homeassistant.exceptions import TemplateError
from homeassistant.loader import bind_hass

_LOGGER = logging.getLogger(__name__)

LIGHTS_CONTROL = None

DOMAIN = 'lights_control'
# VERSION = '1.0.0'

# Custom configuration names
CONF_SWITCH_MAP = "switch_map"
CONF_SENSOR_MAP = "sensor_map"
CONF_SENSOR_DEFAULT_SWITCH_OFF = "sensor_default_switch_off"
CONF_POWER_SAVE = "power_save"
CONF_ON_STATE = "on_state"
CONF_OFF_STATE = "off_state"
CONF_NOTIFY_TURN_OFF = "notify_turn_off"
CONF_AUTOMATION_MAP = "automation_map"

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        # TODO: deep schema
        vol.Optional(CONF_SWITCH_MAP, default={}): dict,
        vol.Optional(CONF_SENSOR_MAP, default={}): dict,
        vol.Optional(CONF_SENSOR_DEFAULT_SWITCH_OFF, default=5): int,
        vol.Optional(CONF_POWER_SAVE, default={}): dict,
        vol.Optional(CONF_ON_STATE, default={}): dict,
        vol.Optional(CONF_OFF_STATE, default={}): dict,
        vol.Optional(CONF_NOTIFY_TURN_OFF, default={}): dict,
        vol.Optional(CONF_AUTOMATION_MAP, default={}): dict,
    }),
}, extra=vol.ALLOW_EXTRA)   # TODO: what ALLOW_EXTRA is about?

ATTR_NAME = "name"
ATTR_VALUE = "value"
ATTR_NAME_TEMPLATE = "value_template"
ATTR_VALUE_TEMPLATE = "value_template"

SERVICE_SWITCH = "switch"
SERVICE_SWITCH_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_VALUE): cv.match_all,
    }
)

SERVICE_SWITCH_TEMPLATE = "switch_template"
SERVICE_SWITCH_TEMPLATE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME_TEMPLATE): cv.template,
        vol.Required(ATTR_VALUE_TEMPLATE): cv.template,
    }
)

SERVICE_SENSOR = "sensor"
SERVICE_SENSOR_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_VALUE): cv.match_all,
    }
)

SERVICE_SENSOR_TEMPLATE = "sensor_template"
SERVICE_SENSOR_TEMPLATE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME_TEMPLATE): cv.template,
        vol.Required(ATTR_VALUE_TEMPLATE): cv.template,
    }
)

SERVICE_ON_LIGHT_CHANGE = "on_light_change"
SERVICE_ON_LIGHT_CHANGE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_VALUE): cv.match_all,
    }
)

SERVICE_ON_LIGHT_CHANGE_TEMPLATE = "on_light_change_template"
SERVICE_ON_LIGHT_CHANGE_TEMPLATE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_NAME_TEMPLATE): cv.template,
        vol.Required(ATTR_VALUE_TEMPLATE): cv.template,
    }
)

SERVICE_WATCH_DOG = "watchdog"
SERVICE_WATCH_DOG_SCHEMA = vol.Schema(
    {
    }
)

SERVICE_RELOAD_GROUPS = "reload_groups"
SERVICE_RELOAD_GROUPS_SCHEMA = vol.Schema(
    {
    }
)

SERVICE_RESTART = "restart"
SERVICE_RESTART_SCHEMA = vol.Schema(
    {
    }
)

SERVICE_DUMP = "dump"
SERVICE_DUMP_SCHEMA = vol.Schema(
    {
    }
)


# NOTE: @bind_hass is to indicate that first argument is HASS


@bind_hass
def switch(
    hass,
    name,
    value
):
    """React to flick of the switch"""
    hass.services.call(
        DOMAIN,
        SERVICE_SWITCH,
        {
            ATTR_NAME: name,
            ATTR_VALUE: value
        },
    )


@bind_hass
def switch_template(
    hass,
    name_template,
    value_template
):
    """React to flick of the switch"""
    hass.services.call(
        DOMAIN,
        SERVICE_SWITCH,
        {
            ATTR_NAME_TEMPLATE: name_template,
            ATTR_VALUE_TEMPLATE: value_template
        },
    )


@bind_hass
def sensor(
    hass,
    name,
    value
):
    """React to sensor trigger"""
    hass.services.call(
        DOMAIN,
        SERVICE_SENSOR,
        {
            ATTR_NAME: name,
            ATTR_VALUE: value
        },
    )


@bind_hass
def sensor_template(
    hass,
    name_template,
    value_template
):
    """React to sensor trigger"""
    hass.services.call(
        DOMAIN,
        SERVICE_SENSOR,
        {
            ATTR_NAME_TEMPLATE: name_template,
            ATTR_VALUE_TEMPLATE: value_template
        },
    )


@bind_hass
def on_light_change(
    hass,
    name_template,
    value_template
):
    """React to lights state change"""
    hass.services.call(
        DOMAIN,
        SERVICE_ON_LIGHT_CHANGE,
        {
            ATTR_NAME_TEMPLATE: name_template,
            ATTR_VALUE_TEMPLATE: value_template
        },
    )


@bind_hass
def watchdog(
    hass
):
    """Do LightsControl automatics"""
    hass.services.call(
        DOMAIN,
        SERVICE_WATCH_DOG,
        {
        },
    )


@bind_hass
def reload_groups(
    hass
):
    """Reload groups"""
    hass.services.call(
        DOMAIN,
        SERVICE_RELOAD_GROUPS,
        {
        },
    )


@bind_hass
def restart(
    hass
):
    """Reload groups"""
    hass.services.call(
        DOMAIN,
        SERVICE_RESTART,
        {
        },
    )


def setup(hass, config):
    """Setup LightsControl component."""
    from .lights_control_core.lights_control import LightsControl

    switch_map = config[DOMAIN].get(CONF_SWITCH_MAP, {})
    sensor_map = config[DOMAIN].get(CONF_SENSOR_MAP, {})
    sensor_default_switch_off = config[DOMAIN].get(CONF_SENSOR_DEFAULT_SWITCH_OFF, 5)
    power_save = config[DOMAIN].get(CONF_POWER_SAVE, {})
    on_state = config[DOMAIN].get(CONF_ON_STATE, {})
    off_state = config[DOMAIN].get(CONF_OFF_STATE, {})
    notify_turn_off = config[DOMAIN].get(CONF_NOTIFY_TURN_OFF, {})
    automation_map = config[DOMAIN].get(CONF_AUTOMATION_MAP, {})
    h = {'hass': hass, 'logger': _LOGGER, 'data': {}}

    global LIGHTS_CONTROL
    try:
        LIGHTS_CONTROL = LightsControl(h, False,
                                       on_state, off_state, power_save, notify_turn_off, switch_map, sensor_map,
                                       sensor_default_switch_off, automation_map)
    except Exception as e:
        _LOGGER.error("LightsControl failed on creation due to exception {}".format(e))
        return False

    def stop_lights_control(event):
        """Stop the LightsControl service."""
        global LIGHTS_CONTROL
        LIGHTS_CONTROL = None

    def start_lights_control(event):
        """Start the LightsControl service."""
        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_lights_control)

    def _render_name_value(template, data, render_name_data, render_value_data):
        name = data.get(ATTR_NAME_TEMPLATE)
        value = data.get(ATTR_VALUE_TEMPLATE)
        try:
            name.hass = hass
            name = name.render(render_name_data)
        except TemplateError as ex:
            _LOGGER.error(
                "Could not render %s's name_template: %s",
                template,
                ex,
            )
            name = None
        if not isinstance(name, str):
            _LOGGER.error(
                "Rendered from %s name is not a string!",
                template,
            )
            name = None
        try:
            value.hass = hass
            value = value.render(render_value_data)
        except TemplateError as ex:
            _LOGGER.error(
                "Could not render %s's value_template: %s",
                template,
                ex,
            )
            name = None
        return name, value

    def switch_service(call):
        """Handle calls to the switch service."""
        global LIGHTS_CONTROL
        if LIGHTS_CONTROL is not None:
            name = call.data.get(ATTR_NAME)
            value = call.data.get(ATTR_VALUE)
            if name is None:
                name, value = _render_name_value("switch_template", call.data, {}, {})
            if name is not None:
                LIGHTS_CONTROL.switch(name, value)
        else:
            _LOGGER.warning("{}: failed to do switch call since LightsControl is not running".format(DOMAIN))

    def sensor_service(call):
        """Handle calls to the sensor service."""
        global LIGHTS_CONTROL
        if LIGHTS_CONTROL is not None:
            name = call.data.get(ATTR_NAME)
            value = call.data.get(ATTR_VALUE)
            if name is None:
                name, value = _render_name_value("sensor_template", call.data, {}, {})
            if name is not None:
                LIGHTS_CONTROL.sensor(name, value)
        else:
            _LOGGER.warning("{}: failed to do sensor call since LightsControl is not running".format(DOMAIN))

    def on_light_change_service(call):
        """Handle lights state change"""
        global LIGHTS_CONTROL
        if LIGHTS_CONTROL is not None:
            name = call.data.get(ATTR_NAME, None)
            value = call.data.get(ATTR_VALUE, None)
            if name is None:
                name, value = _render_name_value("on_light_change_template", call.data, {}, {})
            if name is not None:
                LIGHTS_CONTROL.on_light_change(name, value)
        else:
            _LOGGER.warning("{}: failed to do on_light_change call since LightsControl is not running".format(DOMAIN))

    def watchdog_service(call):
        """Handle calls to the watchdog service."""
        global LIGHTS_CONTROL
        if LIGHTS_CONTROL is not None:
            LIGHTS_CONTROL.watchdog()
        else:
            _LOGGER.warning("{}: failed to do watchdog call since LightsControl is not running".format(DOMAIN))

    def reload_groups_service(call):
        """Handle calls to the reload_groups service."""
        global LIGHTS_CONTROL
        if LIGHTS_CONTROL is not None:
            LIGHTS_CONTROL.reload_groups()
        else:
            _LOGGER.warning("{}: failed to do reload_groups call since LightsControl is not running".format(DOMAIN))

    def restart_service(call):
        """Handle calls to the restart service."""
        global LIGHTS_CONTROL
        if LIGHTS_CONTROL is not None:
            LIGHTS_CONTROL.restart()
        else:
            _LOGGER.warning("{}: failed to do restart call since LightsControl is not running".format(DOMAIN))

    def dump_service(call):
        """Handle calls to the dump service."""
        global LIGHTS_CONTROL
        if LIGHTS_CONTROL is not None:
            LIGHTS_CONTROL.dump()
        else:
            _LOGGER.warning("{}: failed to do dump call since LightsControl is not running".format(DOMAIN))

    services = [
        (SERVICE_SWITCH, switch_service, SERVICE_SWITCH_SCHEMA),
        (SERVICE_SENSOR, sensor_service, SERVICE_SENSOR_SCHEMA),
        (SERVICE_ON_LIGHT_CHANGE, on_light_change_service, SERVICE_ON_LIGHT_CHANGE_SCHEMA),

        (SERVICE_SWITCH_TEMPLATE, switch_service, SERVICE_SWITCH_TEMPLATE_SCHEMA),
        (SERVICE_SENSOR_TEMPLATE, sensor_service, SERVICE_SENSOR_TEMPLATE_SCHEMA),
        (SERVICE_ON_LIGHT_CHANGE_TEMPLATE, on_light_change_service, SERVICE_ON_LIGHT_CHANGE_TEMPLATE_SCHEMA),

        (SERVICE_WATCH_DOG, watchdog_service, SERVICE_WATCH_DOG_SCHEMA),
        (SERVICE_RELOAD_GROUPS, reload_groups_service, SERVICE_RELOAD_GROUPS_SCHEMA),
        (SERVICE_RESTART, restart_service, SERVICE_RESTART_SCHEMA),
        (SERVICE_DUMP, dump_service, SERVICE_DUMP_SCHEMA),
    ]

    for s in services:
        hass.services.register(
            DOMAIN,
            s[0],
            s[1],
            schema=s[2],
        )

    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, start_lights_control)

    return True
