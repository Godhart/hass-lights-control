import datetime
from .constants import STATE_OFF
# import pprint

LOG_FAIL = True
LOG_FALLBACK = True
LOG_DEBUG = False


def value_get(h, obj, fallback=None):
    if LOG_DEBUG:
        h['logger'].info(f"hass_helpers: Getting value of {obj}")
    state = h['hass'].states.get(obj)
    if state is None:
        if LOG_FALLBACK:
            h['logger'].info(f"hass_helpers: Falling back state of {obj} to {fallback}")
        return fallback
    else:
        if LOG_DEBUG:
            h['logger'].info(f"hass_helpers: It's {state.state}")
        return state.state


def value_get_full(h, obj, fallback=None):
    if LOG_DEBUG:
        h['logger'].info(f"hass_helpers: Getting full state of {obj}")
    state = h['hass'].states.get(obj)
    if state is None:
        if fallback is None:
            if LOG_FAIL:
                h['logger'].info(f"hass_helpers: Failed to get full state of {obj}, returning None")
            return None
        else:
            if LOG_FALLBACK:
                h['logger'].info(f"hass_helpers: Falling back full state of {obj} to {fallback}")
            return {'state': fallback, 'attributes': {}}
    else:
        if LOG_DEBUG:
            h['logger'].info(f"hass_helpers: It's state: {state.state}, attributes: {state.attributes}")
        return {'state': state.state, 'attributes': state.attributes}


def value_set(h, obj, value):
    if obj[:9] != 'variable.':
        raise ValueError("hass_helpers: value set can be called only for variables")
    service_data = {'variable': obj, 'value': value}
    h['hass'].services.call('variable', 'set_variable_data', service_data, True)


def value_update(h, obj, fields):
    if obj[:9] != 'variable.':
        raise ValueError("hass_helpers: value update can be called only for variables")
    value = value_get(h, obj, None)
    assert value is not None, "State of entity {} wasn't found".format(obj)
    for f in fields:
        if f in value:
            value[f] = fields[f]
    value_set(h, obj, value)


def last_changed(h, obj):
    if LOG_DEBUG:
        h['logger'].info(f"hass_helpers: Getting last changed of {obj}")
    state = h['hass'].states.get(obj)
    if state is None:
        if LOG_FAIL:
            h['logger'].info(f"hass_helpers: Failed to get state. Falling back to current time")
        return datetime.datetime.now()
    else:
        if LOG_DEBUG:
            h['logger'].info(f"hass_helpers: last_changed: {state.last_changed}")
        return state.last_changed


def lights_on(h, obj):
    if obj[:6] == 'light.':
        service = 'light'
    elif obj[:7] == 'switch.':
        service = 'switch'
    else:
        raise ValueError("lights_on don't works with {}".format(obj))
    service_data = {'entity_id': obj}
    h['hass'].services.call(service, 'turn_on', service_data, True)
    if LOG_DEBUG:
        h['logger'].info("Entity {} switched on".format(obj))


def lights_off(h, obj):
    if obj[:6] == 'light.':
        service = 'light'
    elif obj[:7] == 'switch.':
        service = 'switch'
    else:
        raise ValueError("lights_ff don't works with {}".format(obj))
    service_data = {'entity_id': obj}
    h['hass'].services.call(service, 'turn_off', service_data, True)
    if LOG_DEBUG:
        h['logger'].info("Entity {} switched off".format(obj))


def lights_dim(h, obj, brightness):
    if obj[:6] == 'light.':
        service = 'light'
        service_data = {'entity_id': obj, 'brightness': brightness}
    elif obj[:7] == 'switch.':
        service = 'switch'
        service_data = {'entity_id': obj}
    else:
        raise ValueError("lights_dim don't works with {}".format(obj))
    h['hass'].services.call(service, 'turn_on', service_data, True)
    if LOG_DEBUG:
        h['logger'].info("Entity {} dimmed to {}".format(obj, brightness))


def lights_switch_state(h, obj, state):
    if state['state'] == STATE_OFF:
        lights_off(h, obj)
    elif 'brightness' not in state:
        lights_on(h, obj)
    else:
        lights_dim(h, obj, state['brightness'])


def light_state(h, obj):
    _ls = value_get_full(h, obj)
    if _ls is None:
        return None
    return {'state': _ls['state'], 'brightness': _ls['attributes'].get('brightness', 255)}
