from ._hass_helpers import value_get, value_get_full, value_set, lights_switch_state, light_state, \
    lights_off, lights_on
from ._hass_mock import Hass as HassMock
from time import sleep
from datetime import datetime
from copy import copy, deepcopy
import re
import pprint
from .constants import STATE_ON, STATE_OFF


ALLOW_AUTO_MAGIC = True         # Allow automatic magic events creation for double clicks
ALLOW_POSITIONAL_CONF = False   # Allow configuration records in positional way
DISABLE_SENSORS_WITH_AUTOMATION = True  # Disable sensor actions with automations

LOG_PARSING = False     # Log configuration parsing
LOG_CALLS = False       # Log service calls starts besides watchdog
LOG_WATCHDOG = False    # Log watchdog calls starts


class _ChoppedTime(object):

    def __init__(self, value):
        if isinstance(value, str):
            self._value_str = value
            self._value = datetime.strptime(value, "%H:%M:%S")
            self._value_complete = None
        elif isinstance(value, datetime):
            self._value_complete = value
            self._value = datetime(year=1900, month=1, day=1, hour=value.hour, minute=value.minute, second=value.second)
            self._value_str = self._value.strftime("%H:%M:%S")
        elif isinstance(value, _ChoppedTime):
            self._value = value.value
            self._value_str = value.str
            self._value_complete = value.complete
        else:
            raise ValueError("value should an instance of str/datetime/_ChoppedTime! (got {})".format(type(value)))

    @property
    def value(self):
        return self._value

    @property
    def str(self):
        return self._value_str

    @property
    def complete(self):
        return self._value_complete

    def __str__(self):
        return self._value_str

    def __repr__(self):
        # return "_ChoppedTime("+self._value_str+")"
        return self._value_str


class LightsControlConfig(object):
    _switch_map_var = 'variable.lights_control_switch_map'
    _on_state_var = 'variable.lights_control_on_state'
    _off_state_var = 'variable.lights_control_off_state'
    _power_save_var = 'variable.lights_control_powersave'
    _notify_turn_off_var = 'variable.lights_control_notify_turn_off'
    _sensor_timeout_var = 'variable.lights_control_sensor_default_switch_off'
    _sensor_map_var = 'variable.lights_control_sensor_map'
    _automation_map_var = 'variable.lights_control_automation_map'

    def __init__(self, h, use_variable=False,
                 on_state=None, off_state=None, power_save=None, notify_turn_off=None,
                 switch_map=None, sensor_map=None, sensor_timeout=None, automation_map=None):
        self._entities = {}
        self._groups = {}
        self._configuration = {}
        self._h = h
        self._hass = h['hass']
        self._logger = h['logger']
        self._use_variable = use_variable
        self.on_state = {}
        self.off_state = {}
        self.power_save = {}
        self.notify_turn_off = {}
        self.switch_map = {}
        self.sensor_map = {}
        self.sensor_timeout = {}
        self.automation_map = {}

        if not use_variable:
            self._intial_data = {
                'on_state': deepcopy(on_state),
                'off_state': deepcopy(off_state),
                'power_save': deepcopy(power_save),
                'notify_turn_off': deepcopy(notify_turn_off),
                'switch_map': deepcopy(switch_map),
                'sensor_map': deepcopy(sensor_map),
                'sensor_timeout': sensor_timeout,
                'automation_map': automation_map
            }
        else:
            self._intial_data = {}
        self._log("LightsControl component just inited")

    @property
    def as_dict(self):
        """ Return configuration as dictionary """
        config = {}
        config['on_state'] = self.on_state
        config['off_state'] = self.off_state
        config['power_save'] = self.power_save
        config['notify_turn_off'] = self.notify_turn_off
        config['switch_map'] = self.switch_map
        config['sensor_map'] = self.sensor_map
        config['sensor_timeout'] = self.sensor_timeout
        config['automation_map'] = self.automation_map
        return deepcopy(config)

    def _log(self, message):
        self._logger.info(message)

    def _warning(self, message):
        self._logger.warning(message)

    def _error(self, message):
        self._logger.error(message)

    @staticmethod
    def _update_prefix(value, default_prefix):
        """ Append prefix into string or list's items there is no prefix"""
        if isinstance(value, str):
            return [value, default_prefix + value]['.' not in value]
        elif isinstance(value, (list, tuple)):
            return [[v, default_prefix + v]['.' not in v] for v in value]
        else:
            raise ValueError("Value type should be string/list/tuple (got {})".format(type(value)))

    @staticmethod
    def _update_keys_prefix(value, default_prefix):
        """ Append prefix into key if it don't contains prefix """
        if not isinstance(value, dict):
            raise ValueError("Value type should be dict (got {})".format(type(value)))
        result = {LightsControlConfig._update_prefix(k, default_prefix): v for k, v in value.items()}
        return result

    def load(self):
        """ Loads configuration. Previous configuration would be dropped completely"""
        self._entities = {}
        self._groups = {}
        self._configuration = {}
        if self._use_variable:
            h = self._h
            data = {
                'on_state': value_get(h, self._on_state_var, {}),
                'off_state': value_get(h, self._off_state_var, {}),
                'power_save': value_get(h, self._power_save_var, {}),
                'notify_turn_off': value_get(h, self._notify_turn_off_var, {}),
                'switch_map': value_get(h, self._switch_map_var, {}),
                'sensor_map': value_get(h, self._sensor_map_var, {}),
                'sensor_timeout': value_get(h, self._sensor_timeout_var, 5),
                'automation_map': value_get(h, self._automation_map_var, {})
            }
        else:
            data = deepcopy(self._intial_data)

        self._parse_on_off_config(data['on_state'], is_on_state=True)
        self._parse_on_off_config(data['off_state'], is_on_state=False)
        self._parse_power_save_config(data['power_save'])
        self._parse_notify_config(data['notify_turn_off'])
        self._parse_switch_config(data['switch_map'])
        self._parse_sensor_default_timeout(data['sensor_timeout'])
        self._parse_sensor_config(data['sensor_map'])
        self._parse_automation_config(data['automation_map'])

        self.reload_groups()

    def _parse_record(self, keywords, min_len, *args, **kwargs):
        """ Parses configuration record with positional OR keyworded args """
        result = {}

        if not ALLOW_POSITIONAL_CONF and (len(args)) > 0:
            raise ValueError("Unexpected format: positional args are disabled!")

        if not (len(args) > 0 and len(kwargs) == 0 or len(args) == 0 and len(kwargs) > 0):
            raise ValueError("Unexpected format: "
                             "Only 'all positional' or 'all keyworded' case is supported")

        if not (len(args) > 0 or len(kwargs) > 0):
            raise ValueError("Unexpected format: "
                             "Excepted list or dict")

        if len(args) > 0:
            record = args
        else:
            record = kwargs

        if LOG_PARSING:
            self._log("Parsing record:\n  format: {}\n  data: {} ".format(pprint.pformat(keywords), pprint.pformat(
                record, indent=4)))

        if isinstance(record, (list, tuple)):
            for i in range(0, len(keywords)):
                if i < len(record):
                    result[keywords[i][0]] = record[i]
                else:
                    if i < min_len:
                        raise ValueError("Unexpected format: "
                                         "Excepted at least {} positional arguments"
                                         " ({})".format(min_len, keywords[:min_len]))
                    result[keywords[i][0]] = keywords[i][1]
        else:
            for i in range(0, len(keywords)):
                if i < min_len and keywords[i][0] not in record:
                    raise ValueError("Unexpected format: "
                                     "Field {} is mandatory".format(keywords[i][0]))
                result[keywords[i][0]] = record.get(keywords[i][0], keywords[i][1])

        for i in range(0, len(keywords)):
            f = keywords[i]
            if len(f) > 2 and f[2] is not None:
                value_check = False
                if isinstance(f[2], tuple) and not all(isinstance(item, type) for item in f[2]):
                    assert not any(isinstance(item, type) for item in f[2]), "Mixed type/value check is not allowed!"
                    value_check = True
                if not value_check:
                    if not isinstance(result[f[0]], f[2]) and (i < min_len or result[f[0]] != f[1]):
                        raise ValueError("Unexpected value type for {}: Expected: {}, got: {}".format(
                            f[0], f[2], type(result[f[0]])))
                else:
                    if result[f[0]] not in f[2] and (i < min_len or result[f[0]] != f[1]):
                        raise ValueError("Unexpected value for {}: Expected any of: {}, got: {}".format(
                            f[0], f[2], result[f[0]]))
            if result[f[0]] is not None:
                if len(f) > 3 and f[3] is not None:
                    result[f[0]] = LightsControlConfig._update_prefix(result[f[0]], f[3])
                if len(f) > 4 and f[4] is not None and not isinstance(result[f[0]], f[4]):
                    if f[4] == list:
                        if isinstance(result[f[0]], tuple):
                            result[f[0]] = list(result[f[0]])
                        else:
                            result[f[0]] = [result[f[0]]]
                    elif f[4] == tuple:
                        if isinstance(result[f[0]], list):
                            result[f[0]] = tuple(result[f[0]])
                        else:
                            result[f[0]] = (result[f[0]])
                    else:
                        result[f[0]] = f[4](result[f[0]])

        return result

    @staticmethod
    def _validated_time(data, nested=None):
        """ Validates time entry and converts it to _ChoppedTime """
        if nested is False:
            if not isinstance(data, (list, tuple)):
                return None
            if len(data) != 2:
                return None
            data = list(data)
            for i in range(0, 2):
                if not isinstance(data[i], str):
                    return None
                data[i] = data[i].strip()
                m = re.search(r"^(\d\d):(\d\d):(\d\d)$", data[i])
                if m is None:
                    return None
                hh, mm, ss = m.groups()
                if int(hh) >= 24:
                    return None
                if int(mm) >= 60:
                    return None
                if int(ss) >= 60:
                    return None
                data[i] = _ChoppedTime(data[i])
            return data
        elif nested is True:
            if not isinstance(data, (list, tuple)):
                return None
            data = list(data)
            if len(data) == 0:
                return None
            for i in range(0, len(data)):
                new_value = LightsControlConfig._validated_time(data[i], nested=False)
                if new_value is None:
                    return None
                data[i] = new_value
            return data
        else:
            new_value = LightsControlConfig._validated_time(data, nested=False)
            if new_value is None:
                new_value = LightsControlConfig._validated_time(data, nested=True)
            else:
                new_value = [new_value]
            return new_value

    def _entity_is_kind_of(self, entity, kind):
        for group_kind in self._entities[entity]['kind'].values():
            if kind in group_kind:
                return True
        return False

    def _update_entities(self, entities_list, kind, group=None):
        """ Updates list of entities mentioned in configuration. Extrapolates all groups """
        for item in entities_list:
            if item[:6] != "group.":
                if group is None:
                    group = "_self_"
                if item not in self._entities:
                    self._entities[item] = {'kind': {group: [kind]}, 'groups': [group]}
                else:
                    if group not in self._entities[item]['kind']:
                        self._entities[item]['kind'][group] = [kind]
                    elif kind not in self._entities[item]['kind'][group]:
                        self._entities[item]['kind'][group].append(kind)
                    if group not in self._entities[item]['groups']:
                        self._entities[item]['groups'].append(group)
            else:
                if group is not None:
                    raise ValueError("LightsControl: group '{}' is registered with not None group argument".format(
                        item))

                if item not in self._groups:
                    self._groups[item] = {'kind': [kind], 'entities': []}
                else:
                    if kind not in self._groups[item]['kind']:
                        self._groups[item]['kind'].append(kind)

    def _reload_group(self, name, entities):
        """ Updates data about group content and entity-group relations """
        exclude_from_group = [e for e in self._groups[name]['entities'] if e not in entities]
        self._groups[name]['entities'] = entities
        for entity in exclude_from_group:
            if entity not in self._entities:    # TODO: check with assert as this case shouldn't exist if all is OK
                continue
            self._entities[entity]['groups'] = list(set([g for g in self._entities[entity]['groups'] if g != name]))
            if name in self._entities[entity]['kind']:
                del self._entities[entity]['kind'][name]
        for kind in self._groups[name]['kind']:
            self._update_entities(entities, kind, name)

    def _get_group_entities(self, group):
        """ Get's all entities that are in specified group """
        state = value_get_full(self._h, group, None)
        if state is None:
            self._error("Failed to find group '{}'".format(group))
            return []
        value = state['attributes'].get('entity_id', None)
        if value is None:
            self._error("Failed to get entities of group '{}'".format(group))
            return []
        if not isinstance(value, (str, list, tuple)):
            self._error("Unexpected format for entities of group '{}'".format(group))
            return []
        if isinstance(value, str):
            value = [value]
        return list(value)

    def reload_groups(self):
        """ Reloads groups and updates entities list to maintain objects coherecny """
        for k in self._groups:
            entities = self._get_group_entities(k)
            self._reload_group(k, entities)

    def entities_list(self, kind, names, chain=None):
        """
        Returns all entities of specified kind that were mentioned in configuration for specified group.
        Extrapolates nestsed groups
        """
        el = []
        if chain is None:
            chain = []
        if len(chain) >= 10:
            self._error("LightsControl: Looks like there is groups loop or excessive groups nesting: {}."
                        " Stopping recursion!".format('->'.join(chain)))
            return el
        if isinstance(names, str):
            names = [names]
        for item in names:
            if item in chain:
                continue
            if isinstance(item, (list, tuple)):
                el += self.entities_list(kind, item, chain)
            elif item in self._entities and self._entity_is_kind_of(item, kind):
                el.append(item)
            elif item in self._groups:
                el += self.entities_list(kind, self._groups[item]['entities'], chain+[item])
        return el

    @property
    def all_lights(self):
        """ Returns list of all lights"""
        return self.entities_of_kind('light')

    def entities_of_kind(self, kind):
        """ Returns list of all entities of specified kind"""
        result = []
        for k in self._entities.keys():
            if self._entity_is_kind_of(k, kind):
                result.append(k)
        return result

    def _parse_rules_map(self, rules_map, map_name, key_field, parse_method, list_allowed):
        """
        Parses complicated dictionary config (in which value is list of list records or dict records
        Returns normalized dict of rules
        """

        if LOG_PARSING:
            self._log("Parsing rules_map:\n  map_name={}\n  key_field={}\n  parse_method={}\n"
                      "  data: {} ".format(map_name, key_field, parse_method, pprint.pformat(rules_map, indent=4)))

        result = {}

        if not isinstance(rules_map, dict):
            self._error("LightsControl: Unexpected {} format:"
                        " 'dict' expected".format(map_name))
            return {}

        for k, v in rules_map.items():
            if not isinstance(v, (list, tuple)):
                self._error("LightsControl: Unexpected {} format for '{}' rule:"
                            " 'list' expected".format(map_name, k))
                continue
            rules = []
            for item in v:
                if isinstance(item, (list, tuple)):
                    rule = parse_method(k, *item)
                    if not isinstance(rule, list):
                        rules.append(rule)
                    else:
                        rules += rule
                elif isinstance(item, dict):
                    rule = parse_method(k, **item)
                    if not isinstance(rule, list):
                        rules.append(rule)
                    else:
                        rules += rule
                else:
                    self._error("LightsControl: Unexpected {} format for '{}' rule:"
                                " 'list' or 'dict' expected".format(map_name, k))
                continue
            for rule in rules:
                if rule is None:
                    continue
                if key_field != list:
                    key = rule[key_field]
                else:
                    key = k
                if key not in result:
                    result[key] = []
                result[key].append(rule)

        return result

    def _parse_dict_config(self, config, config_name, parser, list_allowed=False):
        """ Parses simple dictionary config """
        result = {}

        if LOG_PARSING:
            self._log("Parsing dict_config:\n  config_name={}\n  list_allowed={}\n"
                      "data: {}".format(config_name, list_allowed, pprint.pformat(config, indent=4)))

        if not isinstance(config, dict):
            self._error("LightsControl: Unexpected {} format:"
                        " 'dict' expected".format(config_name))
            return {}

        for k, v in config.items():
            if isinstance(v, dict):
                rule = parser(k, **v)
            elif not list_allowed:
                self._error("LightsControl: Unexpected {} format for {}:"
                            " 'dict' expected".format(config_name, k))
                continue
            elif isinstance(v, (list, tuple)):
                rule = parser(k, *v)
            else:
                self._error("LightsControl: Unexpected {} format for {}:"
                            " 'dict' or 'list' expected".format(config_name, k))
                continue
            if rule is None:
                continue
            result[k] = rule

        result = {k: v for k, v in result.items() if v is not None}
        return result

    def _parse_switch_config(self, rules_map):
        self.switch_map = {}
        self.switch_map = self._parse_rules_map(rules_map, 'switch map', 'button', self._parse_switch_routine,
                                                list_allowed=True)

    def _parse_sensor_config(self, rules_map):
        self.sensor_map = {}
        self.sensor_map = self._parse_rules_map(rules_map, 'sensor map', 'sensor', self._parse_sensor_routine,
                                                list_allowed=True)

    def _parse_on_off_config(self, onoff_state, is_on_state):
        if is_on_state:
            self.on_state = {}
            self.on_state = self._parse_rules_map(onoff_state, 'on state', list, self._parse_on_off_record,
                                                  list_allowed=True)
        else:
            self.off_state = {}
            self.off_state = self._parse_rules_map(onoff_state, 'off state', list, self._parse_on_off_record,
                                                   list_allowed=True)

    def _parse_power_save_config(self, power_save):
        self.power_save = {}
        self.power_save = self._parse_dict_config(power_save, 'power save', self._parse_power_save_record)

    def _parse_notify_config(self, notify):
        self.notify_turn_off = {}
        self.notify_turn_off = self._parse_dict_config(notify, 'notify turn off', self._parse_notify_record)

    def _parse_automation_config(self, config):
        self.automation_map = {}
        result = {}
        config_name = 'automation map'

        if not isinstance(config, dict):
            self._error("LightsControl: Unexpected {} format:"
                        " 'dict' expected".format(config_name))
            return

        for k, v in config.items():
            if isinstance(v, (str, list, tuple)):
                if isinstance(v, str):
                    result[k] = [v]
                else:
                    result[k] = list(v)
            else:
                self._error("LightsControl: Unexpected {} format for {}:"
                            " 'str' or 'list' expected".format(config_name, k))
                continue

        for k, v in result.items():
            result[k] = self._update_prefix(v, 'light.')

        result = self._update_keys_prefix(result, 'automation.')
        self._update_entities(list(result.keys()), 'automation')
        self.automation_map = result

    def _parse_sensor_default_timeout(self, config):
        self.sensor_timeout = 5
        config_name = 'sensor default timeout'
        if not isinstance(config, int):
            self._error("LightsControl: Unexpected {} format:"
                        " 'int' expected".format(config_name))
            return
        self.sensor_timeout = config

    def _parse_switch_routine(self, rule, *args, **kwargs):
        template = (('button',     None, str, 'button.'),
                    ('event',      None, (str, list), None, list),
                    ('switch_off', -1,   int),
                    ('lights_on',  [rule], (str, list, tuple), 'light.', list),
                    ('lights_off', None, (str, list, tuple), 'light.', list),
                    ('magic', [False, None][ALLOW_AUTO_MAGIC], (bool, int), None, bool))

        try:
            data = self._parse_record(template, 2, *args, **kwargs)
        except Exception as e:
            self._error("LightsControl: Failed to parse switch map rule '{}' due to exception: {}".format(
                rule, e))
            return None

        if data['lights_off'] is None:
            data['lights_off'] = copy(data['lights_on'])

        events = {}
        events_list = []
        for event in list(set(data['event'])):
            events[event] = copy(data)
            events[event]['event'] = [event]
            # If double click is alternative to another click then alternate brightness level
            # Magic = True when there is TWO events, event name contains 'double'
            if data['magic'] is None:
                if len(data['event']) == 2 and 'double' in event:
                    events[event]['magic'] = True
                else:
                    events[event]['magic'] = False
            events_list.append(events[event])
        try:
            self._update_entities(data['lights_on'], 'light')
            self._update_entities(data['lights_off'], 'light')
            self._update_entities([data['button']], 'button')
        except Exception as e:
            self._error("LightsControl: Failed to parse switch map rule '{}' due to exception: {}".format(
                rule, e))
            return None

        return events_list

    def _parse_sensor_routine(self, rule, *args, **kwargs):
        template = (('sensor',        None,   str, 'sensor.'),
                    ('value',         STATE_ON),
                    ('when',          ["00:00:00", "23:59:59"],   list),
                    ('switch_off',    self.sensor_timeout,     int),
                    ('auto',          False,  (bool, int)),
                    ('lights_on',     [rule], (str, list, tuple), 'light.', list))

        try:
            data = self._parse_record(template, 1, *args, **kwargs)
        except Exception as e:
            self._error("LightsControl: Failed to parse sensor map rule '{}' due to exception: {}".format(
                rule, e))
            return None

        # TODO: Validate value
        if data['value'] is None:
            self._error("LightsControl: Unexpected sensor routine format for '{}' rule:"
                        "'value' field shouldn't be None".format(rule))
            return None

        if data['when'] is not None:
            validated_time = self._validated_time(data['when'])
            if validated_time is None:
                self._error("LightsControl: Unexpected sensor time format for '{}' rule:"
                            " time range as ['HH:MM:SS','HH:MM:'SS'] or list of such items expected"
                            " (got {})".format(rule, data['when']))
                return None
            else:
                data['when'] = validated_time

        try:
            self._update_entities(data['lights_on'], 'light')
            self._update_entities([data['sensor']], 'sensor')
        except Exception as e:
            self._error("LightsControl: Failed to parse sensor map rule '{}' due to exception: {}".format(
                rule, e))
            return None

        return data

    def _parse_on_off_record(self, rule, *args, **kwargs):
        template_1 = (('when',         None,   list),
                      ('state',        None,   (int, str)),
                      ('lights',       [rule], (str, list, tuple), 'light.', list))

        template_2 = (('sensor',       None,   str, 'sensor.'),
                      ('value',        None),
                      ('state',        None,   (int, str)),
                      ('lights',       [rule], (str, list, tuple), 'light.', list))

        if len(args) > 0:
            if isinstance(args[0], (list, tuple)):
                template = template_1
            else:
                template = template_2
        else:
            if 'value' in kwargs:
                template = template_2
            else:
                template = template_1

        try:
            data = self._parse_record(template, [2, 3][template == template_2], *args, **kwargs)
        except Exception as e:
            self._error("LightsControl: Failed to parse on or off rule '{}' due to exception: {}".format(
                rule, e))
            return None

        if 'when' in data:
            validated_time = self._validated_time(data['when'])
            if validated_time is None:
                self._error("LightsControl: Unexpected time range for on or off for '{}' rule:"
                            " time range as ['HH:MM:SS','HH:MM:'SS'] or list of such items expected"
                            " (got {})".format(rule, data['when']))
                return None
            else:
                data['when'] = validated_time

        try:
            self._update_entities(data['lights'], 'light')
            if 'sensor' in data:
                entities = data['sensor']
                if isinstance(entities, str):
                    entities = [entities]
                self._update_entities(entities, 'sensor')
        except Exception as e:
            self._error("LightsControl: Failed to parse on or off rule '{}' due to exception: {}".format(
                rule, e))
            return None

        return data

    def _parse_power_save_record(self, rule, **kwargs):
        template = (('timeout', 60, int),
                    ('when',    ["00:00:00", "23:59:59"], list),
                    ('lights', [rule], (str, list, tuple), 'light.', list))

        try:
            data = self._parse_record(template, 0, **kwargs)
        except Exception as e:
            self._error("LightsControl: Failed to parse power save rule '{}' due to exception: {}".format(
                rule, e))
            return None

        if data['when'] is not None:
            validated_time = self._validated_time(data['when'])
            if validated_time is None:
                self._error("LightsControl: Unexpected power save time format for '{}' rule:"
                            " time range as ['HH:MM:SS','HH:MM:'SS'] or list of such items expected"
                            " (got {})".format(rule, data['when']))
                return None
            else:
                data['when'] = validated_time
        else:
            data['when'] = self._validated_time([["00:00:00", "23:59:59"]])

        try:
            self._update_entities(data['lights'], 'light')
        except Exception as e:
            self._error("LightsControl: Failed to parse power save rule '{}' due to exception: {}".format(
                rule, e))
            return None

        return data

    def _parse_notify_record(self, rule, *args, **kwargs):
        template_list = (('kind',   None, ("flash", "dim")),
                         ('before', None, int),
                         ('args',   None, (list, dict)))

        template_dict = (('kind',   None, ("flash", "dim")),
                         ('before', None, int),
                         ('lights', [rule], (str, list, tuple), 'light.', list),
                         ('args',   None, (list, dict)))

        try:
            if len(args) > 0:
                data = self._parse_record(template_list, 2, *args)
            else:
                data = self._parse_record(template_dict, 2, **kwargs)
        except Exception as e:
            self._error("LightsControl: Failed to parse notify turn off rule '{}' due to exception: {}".format(
                rule, e))
            return None

        try:
            self._update_entities(data['lights'], 'light')
        except Exception as e:
            self._error("LightsControl: Failed to parse notify turn off rule '{}' due to exception: {}".format(
                rule, e))
            return None

        def flash_args(args):
            result = {'period': 10, 'count': 5}
            if args is None:
                return result
            if isinstance(args, (list, tuple)):
                if len(args) != 2:
                    raise ValueError("Flash requires exactly two arguments")
                result['period'] = args[0]
                result['count'] = args[1]
            elif isinstance(args, dict):
                if len(args) != 2:
                    raise ValueError("Flash requires exactly two fields - 'period' and 'count'")
                if 'period' not in args:
                    raise ValueError("Flash args requires 'period' field")
                if 'count' not in args:
                    raise ValueError("Flash args requires 'count' field")
                result['period'] = args['period']
                result['count'] = args['count']
            else:
                raise ValueError("Wrong type for arguments: Expected list or dict, got {}".format(type(args)))
            return result

        def dim_args(args):
            result = {'brightness': 0.5, 'minimum': 10}
            if args is None:
                return result
            if isinstance(args, (list, tuple)):
                if len(args) != 2:
                    raise ValueError("Dim requires exactly two arguments")
                result['brightness'] = args[0]
                result['minimum'] = args[1]
            elif isinstance(args, dict):
                if len(args) != 2:
                    raise ValueError("Dim requires exactly two fields - 'brightness' and 'minimum'")
                if 'brightness' not in args:
                    raise ValueError("Dim args requires 'brightness' field")
                if 'minimum' not in args:
                    raise ValueError("Flash args requires 'minimum' field")
                result['brightness'] = args['brightness']
                result['minimum'] = args['minimum']
            else:
                raise ValueError("Wrong type for arguments: Expected list or dict, got {}".format(type(args)))
            return result

        try:
            if data['kind'] == 'flash':
                data['args'] = flash_args(data['args'])
            else:
                data['args'] = dim_args(data['args'])
        except ValueError as e:
            self._error("LightsControl: Failed to parse notify turn off rule '{}' due to exception: {}".format(
                rule, e))
            return None

        return data

    def _expand_map_record(self, config_name, record, key_fields, kind, list_wanted, result):
        """ Updates dict with values specified in key_field as key referencing ccresponding rules record """
        entities = []
        for k in key_fields:
            if kind is not None:
                entities += self.entities_list(kind, record[k])
            else:
                entities += record[k]
        entities = list(set(entities))
        for entity in entities:
            if list_wanted:
                if entity not in result:
                    result[entity] = []
                result[entity].append(record)
            else:
                if entity not in result:
                    result[entity] = record
                else:
                    result[entity] = None
                    self._error("LightsControl: overlapping records for {} in '{}'".format(entity, config_name))

    def _expand_map(self, config_name, data, key_fields, kind, list_wanted, go_deeper=False):
        """ Returns dict with values specified in key_field as key referencing corresponding rules record """
        result = {}
        for k, v in data.items():
            if go_deeper:
                records = v
            else:
                records = [v]
            for record in records:
                self._expand_map_record(config_name, record, key_fields, kind, list_wanted, result)
        result = {k: v for k, v in result.items() if v is not None}
        return result

    def _remap(self, config_name, data, key_fields, kind, list_wanted, go_deeper=False):
        """ Returns dict with values specified in key_field as second level key referencing corresponding rules record """
        result = {}
        for k, v in data.items():
            if go_deeper:
                records = v
            else:
                records = [v]
            result[k] = {}
            for record in records:
                self._expand_map_record(config_name, record, key_fields, kind, list_wanted, result[k])
            result[k] = {m: v for m, v in result[k].items() if v is not None}
        return result

    def power_save_lights(self):
        result = self._expand_map('power save', self.power_save, ['lights'], 'light', list_wanted=True, go_deeper=False)
        return result

    def notify_turn_off_lights(self):
        result = self._expand_map('notify turn off', self.notify_turn_off, ['lights'], 'light', list_wanted=False,
                                  go_deeper=False)
        return result

    def switch_events(self):
        result = self._remap('switch map', self.switch_map, ['event'], None, list_wanted=True, go_deeper=True)
        return result

    def sensor_remap(self):
        result = self._remap('sensor map', self.sensor_map, ['lights_on'], 'light', list_wanted=True, go_deeper=True)
        return result

    def sensor_lights(self):
        result = self._expand_map('sensor map', self.sensor_map, ['lights_on'], 'light', list_wanted=True, go_deeper=True)
        return result

    def on_state_lights(self):
        result = self._expand_map('on state', self.on_state, ['lights'], 'light', list_wanted=True, go_deeper=True)
        return result

    def off_state_lights(self):
        result = self._expand_map('off state', self.off_state, ['lights'], 'light', list_wanted=True, go_deeper=True)
        return result

    def automation_map_lights(self):
        result = {}
        config_name = 'automation map'
        for k, v in self.automation_map.items():
            entities = self.entities_list('light', v)
            for entity in entities:
                if entity not in result:
                    result[entity] = k
                else:
                    result[entity] = None
                    self._error("LightsControl: overlapping records for {} in '{}'".format(entity, config_name))

        result = {k: v for k, v in result.items() if v is not None}
        return result


class LightsControl(object):
    _context_var = 'variable.lights_control_context'

    def __init__(self, h, use_variable=False,
                 on_state=None, off_state=None, power_save=None, notify_turn_off=None,
                 switch_map=None, sensor_map=None, sensor_timeout=None, automation_map=None,
                 mock_time_now=None):

        self._inited = None  # None - haven't tried init yet, False - failed to init, True - inited OK
        self._h = h          # Expected dict with 'hass'=HASS and 'logger'=LOGGER
        self._hass = h['hass']
        self._logger = h['logger']
        self._use_variable = use_variable       # If True then config would be read from 'variable' entities of HASS
        self._dump_context_to_variable = False  # For debug purposes context value may be dumped into 'variable' entity of HASS

        if mock_time_now is None:
            self._time_now = datetime.now
        else:
            self._time_now = mock_time_now

        self._config = LightsControlConfig(
            h=h,
            use_variable=use_variable,
            on_state=on_state, off_state=off_state, power_save=power_save, notify_turn_off=notify_turn_off,
            switch_map=switch_map, sensor_map=sensor_map, sensor_timeout=sensor_timeout,
            automation_map=automation_map)

        self.context = {}
        self.sensor_timeout = {}

        self.on_state = {}
        self.off_state = {}
        self.automation_map = {}
        self.switch_events = {}
        self.sensor_map = {}
        self.sensor_lights = {}
        self.power_save = {}
        self.notify_turn_off = {}
        self._scheduled_calls = []

    @staticmethod
    def _time_to_seconds(t):
        return t.timestamp()

    def restart(self):
        """ Totally restarts component - reloads configuration, reinitiates context """
        self._inited = False
        self._scheduled_calls = []
        self.context = {}
        self.sensor_timeout = {}

        self.on_state = {}
        self.off_state = {}
        self.automation_map = {}
        self.switch_events = {}
        self.sensor_map = {}
        self.sensor_lights = {}
        self.power_save = {}
        self.notify_turn_off = {}

        errors = False
        try:
            self._config.load()
        except Exception as e:
            self._error("LightsControl failed to start due to exception while parsing configuration: {}".format(e))
            errors = True

        config = self._config.as_dict

        self.sensor_timeout = config['sensor_timeout']

        self.reload_groups()
        self._inited = not errors

        if LOG_PARSING and not errors:
            self._log("  switch_events:" + pprint.pformat(self.switch_events, indent=4))
            self._log("  sensor_map:" + pprint.pformat(self.sensor_map, indent=4))
            self._log("  sensor_lights:" + pprint.pformat(self.sensor_lights, indent=4))
            self._log("  sensor_timeout:" + pprint.pformat(self.sensor_timeout, indent=4))
            self._log("  on_state:" + pprint.pformat(self.on_state, indent=4))
            self._log("  off_state:" + pprint.pformat(self.off_state, indent=4))
            self._log("  automation_map:" + pprint.pformat(self.automation_map, indent=4))
            self._log("  sensor_lights:" + pprint.pformat(self.automation_map, indent=4))
            self._log("  power_save:" + pprint.pformat(self.automation_map, indent=4))
            self._log("  notify_turn_off:" + pprint.pformat(self.automation_map, indent=4))

    def reload_groups(self):
        """ Reloads groups and updates entity-rule mapping accordingly """
        self._config.reload_groups()
        # Update other config data as it depends on groups (groups are extrapolated)
        self.on_state = self._config.on_state_lights()
        self.off_state = self._config.off_state_lights()
        self.automation_map = self._config.automation_map_lights()
        self.switch_events = self._config.switch_events()
        self.sensor_map = self._config.sensor_remap()
        self.sensor_lights = self._config.sensor_lights()
        self.power_save = self._config.power_save_lights()
        self.notify_turn_off = self._config.notify_turn_off_lights()
        if isinstance(self._hass, HassMock):
            lights = self._config.all_lights
            sensors = self._config.entities_of_kind('sensor')
            sensors = {k: STATE_OFF for k in sensors}
            automations = self._config.entities_of_kind('automation')
            self._hass.init_state(lights, sensors, automations)
        self._update_context()

    def _log(self, message):
        self._logger.info(message)

    def _warning(self, message):
        self._logger.warning(message)

    def _error(self, message):
        self._logger.error(message)

    def _schedule(self, call, *args, **kwargs):
        self._scheduled_calls.append((call, args, kwargs))

    def _scheduled_run(self):
        calls = self._scheduled_calls
        self._scheduled_calls = []
        for call, args, kwargs in calls:
            try:
                call(*args, **kwargs)
            except Exception as e:
                self._error(f"Failed to call {call} with args={args}, kwargs={kwargs} due to exception:\n{e}")

    @staticmethod
    def __light_is_on(state, off_state):
        """ Returns True if state is not STATE_OFF and is not same as off_state"""
        return state['state'] != STATE_OFF and \
                state['state'] != off_state['state'] and \
                ('brightness' not in off_state or state['brightness'] != off_state['brightness'])

    def _light_is_on(self, light, time_now):
        """ Returns True if light is on it it's state (brightness) is not same as off_state"""
        state = light_state(self._h, light)
        if state is None:
            return False
        _os = self._off_state(light, time_now=time_now)
        return self.__light_is_on(state, _os)

    def _update_context(self):
        """ Updates context - includes lights from configuration and initates their context according to their state
            removes from context lights that are no longer in configuration
        """
        lights = self._config.all_lights
        time_now = self._time_now()
        seconds_now = self._time_to_seconds(time_now)
        for light in lights:
            if light not in self.context:
                state = light_state(self._h, light)
                if state is None:
                    continue
                _os = self._off_state(light, time_now=time_now)
                # TODO: make context a class
                self.context[light] = \
                    {'is_on': int(self.__light_is_on(state, _os)),
                     # Current on state:
                     # * -1 - customized off (off_state won't be changed by watchdog)
                     # *  0 - off,
                     # *  1 - on,
                     # *  2 - customized on (on_state won't be changed by watchdog),
                     'switch_off': -1,      # Time to switch off light, in seconds. If negative - don't switch off
                     'notify': -1,          # Time to indicate that light would be switched off soon, in seconds
                     'notified': False,     # Used to determine if switch off notification action were already fired
                     'last_action_secs': seconds_now,  # Used to distinguish actions by LightsControl
                                            # from another light actions
                                            # (time in seconds when last action by LightsControl were committed)
                     'last_activity_secs': seconds_now  # Used to determine if power saving should be activated
                     }
        for light in list(self.context.keys()):
            if light not in lights:
                del self.context[light]
        self._save_context()

    def _save_context(self):
        """ For debug purposes only - saves context into external variable """
        if self._dump_context_to_variable:
            value_set(self._h, self._context_var, self.context)

    def _push_context(self):
        """ For debug purposes only - flushes context changes into external variable """
        # NOTE: no selective context update since it's full fledged component now. Does full dump
        self._save_context()
        return

    def _validate_time_range(self, time_range, go_deeper=True):
        if not isinstance(time_range, (list, tuple)):
            raise ValueError("time_range should be a list of 2 _ChoppedTime items or list of such lists")
        if len(time_range) < 1:
            return 2
        elif isinstance(time_range[0], _ChoppedTime):
            if len(time_range) != 2:
                raise ValueError("time_range should be a list of 2 _ChoppedTime items or list of such lists")
            else:
                return 1
        elif go_deeper:
            vr = [self._validate_time_range(item, go_deeper=False) for item in time_range]
            if not all(r == 1 for r in vr):
                raise ValueError("time_range should be a list of 2 _ChoppedTime items or list of such lists")
            else:
                return 2
        else:
            raise ValueError("time_range should be a list of 2 _ChoppedTime items or list of such lists")

    def _time_in_range(self, time_range, value=None):
        """ Ensures that given time falls into specified range. If value isn't specified then current time used """
        r = []
        vr = self._validate_time_range(time_range)

        if vr == 2:
            return any(self._time_in_range(item, value) for item in time_range)

        r.append(_ChoppedTime(time_range[0]))
        r.append(_ChoppedTime(time_range[1]))
        if value is None:
            value = self._time_now()
        value = _ChoppedTime(value)
        if r[0].value <= r[1].value:
            if r[0].value <= value.value <= r[1].value:
                return True
            else:
                return False
        else:
            if value.value >= r[0].value or value.value <= r[1].value:
                return True
            else:
                return False

    def _automation_is_active(self, name):
        """ Ensures that automation for specified entity is active """
        if name not in self.automation_map:
            return True
        if name not in self.context:
            return False
        return value_get(self._h, self.automation_map[name], STATE_ON) == STATE_ON

    @staticmethod
    def _value_is_within_range(value, activating_value):
        if isinstance(activating_value, (list, tuple)):
            try:
                if activating_value[0] <= value <= activating_value[1]:
                    return True
            except TypeError:
                return False
        else:
            if value == activating_value:
                return True
        return False

    def _off_state(self, light, time_now):
        """ Returns OFF state for specified light according to specified/current time """
        _os = {'state': STATE_OFF}
        if not self._automation_is_active(light):
            return _os
        if light not in self.context:
            return _os

        if light in self.off_state:
            states = self.off_state[light]
            for s in states:
                if 'when' in s:
                    if self._time_in_range(s['when'], time_now):
                        if isinstance(s['state'], str) and s['state'] not in (STATE_ON, STATE_OFF):
                            s['state'] = value_get(self._h, s['state'], STATE_OFF)
                        if s['state'] != STATE_OFF:
                            _os['state'] = STATE_ON
                            if s['state'] != STATE_ON and isinstance(s['state'], int) and 0 <= s['state'] <= 255:
                                _os['brightness'] = s['state']
                        break
                else:
                    value = value_get(self._h, s['sensor'])
                    if value is not None and self._value_is_within_range(value, s['value']):
                        if isinstance(s['state'], str) and s['state'] not in (STATE_ON, STATE_OFF):
                            s['state'] = value_get(self._h, s['state'], STATE_OFF)
                        if s['state'] != STATE_OFF:
                            _os['state'] = STATE_ON
                            if s['state'] != STATE_ON and isinstance(s['state'], int) and 0 <= s['state'] <= 255:
                                _os['brightness'] = s['state']
                        break

        return _os

    def _on_state(self, light, time_now):
        """ Returns ON state for specified light according to specified/current time """
        _os = {'state': STATE_ON, 'brightness': 255}
        if not self._automation_is_active(light):
            return _os
        if light not in self.context:
            return _os

        if light in self.on_state:
            states = self.on_state[light]
            for s in states:
                if 'when' in s:
                    if self._time_in_range(s['when'], time_now):
                        if isinstance(s['state'], str) and s['state'] not in (STATE_ON, STATE_OFF):
                            s['state'] = value_get(self._h, s['state'], STATE_ON)
                        if s['state'] != STATE_OFF:
                            if s['state'] != STATE_ON and isinstance(s['state'], int) and 0 <= s['state'] <= 255:
                                _os['brightness'] = s['state']
                        else:
                            _os = {'state': STATE_OFF}
                        break
                else:
                    value = value_get(self._h, s['sensor'])
                    if value is not None and self._value_is_within_range(value, s['value']):
                        if isinstance(s['state'], str) and s['state'] not in (STATE_ON, STATE_OFF):
                            s['state'] = value_get(self._h, s['state'], STATE_ON)
                        if s['state'] != STATE_OFF:
                            if s['state'] != STATE_ON and isinstance(s['state'], int) and 0 <= s['state'] <= 255:
                                _os['brightness'] = s['state']
                        else:
                            _os = {'state': STATE_OFF}
                        break
        return _os

    def _switch_on(self, entities, switch_off, time_now, max_brightness=False,
                   force_switch_on=False, force_switch_off=False):
        """ Switches on specified entities """
        lights = self._config.entities_list('light', entities)
        seconds_now = self._time_to_seconds(time_now)

        light_was_on = all(self.context[light]['is_on'] > 0 for light in lights)
        for light in lights:
            if light not in self.context:
                continue
            self.context[light]['is_on'] = [1, 2][max_brightness]
            self.context[light]['last_action_secs'] = seconds_now
            if switch_off > 0:
                next_switch_off = int(seconds_now) + 1 + switch_off * 60 - 1
                if force_switch_off or next_switch_off > self.context[light]['switch_off']:
                    self.context[light]['switch_off'] = next_switch_off
                    if light in self.notify_turn_off:
                        self.context[light]['notify'] = next_switch_off - self.notify_turn_off[light]['before']
                        self.context[light]['notified'] = False
            elif switch_off < 0:
                self.context[light]['switch_off'] = -1
                self.context[light]['notify'] = -1
                self.context[light]['notified'] = False
            else:  # if switch_off == 0
                # NOTE: switch_off isn't updated in case if switch_off == 0. That's used for brightness altering
                pass
        self._push_context()

        if force_switch_on or not light_was_on:
            if max_brightness:
                for light in lights:
                    if light not in self.context:
                        continue
                    self._schedule(lights_switch_state, self._h, light, {'state': STATE_ON, 'brightness': 255})
            else:
                for light in lights:
                    if light not in self.context:
                        continue
                    self._schedule(lights_switch_state, self._h, light, self._on_state(light, time_now=time_now))

    def _switch_off(self, entities, time_now):
        lights = self._config.entities_list('light', entities)
        seconds_now = self._time_to_seconds(time_now)
        for light in lights:
            if light not in self.context:
                continue
            self.context[light]['is_on'] = 0
            self.context[light]['switch_off'] = -1
            self.context[light]['notify'] = -1
            self.context[light]['notified'] = False
            self.context[light]['last_action_secs'] = seconds_now
            self._push_context()
            self._schedule(lights_switch_state, self._h, light, self._off_state(light, time_now=time_now))

    def _black_out(self, entities, time_now):
        lights = self._config.entities_list('light', entities)
        seconds_now = self._time_to_seconds(time_now)
        for light in lights:
            if light not in self.context:
                continue
            self.context[light]['is_on'] = -1
            self.context[light]['switch_off'] = -1
            self.context[light]['notify'] = -1
            self.context[light]['notified'] = False
            self.context[light]['last_action_secs'] = seconds_now
            self._push_context()
            self._schedule(lights_off, self._h, light)

    def _switch(self, routine, time_now):
        seconds_now = self._time_to_seconds(time_now)

        switch_name, switch_events, switch_off, on_group, off_group, magic_switch = \
            routine['button'], routine['event'], routine['switch_off'], \
            routine['lights_on'], routine['lights_off'], routine['magic']

        if len(on_group) == 0:
            all_is_on = True
            max_brightness = True
        else:
            all_is_on = all(self.context[item]['is_on'] > 0 for item in on_group)
            max_brightness = all(self.context[item]['is_on'] == 2 for item in on_group)
            # Switch click during turn off notification time don't turn's off lights, but turn's them on again
            if all_is_on and any(0 <= self.context[item]['notify'] <= seconds_now for item in on_group):
                all_is_on = False

        if magic_switch:
            on_off_groups_are_same = on_group == off_group
            lights = self._config.entities_list('light', on_group)
            for light in lights:
                # NOTE: if lights are on and there is no possibility to switch them off normally
                #   cut the power off by magic click
                if all_is_on and max_brightness \
                        and on_off_groups_are_same and self._off_state(light, time_now)['state'] != STATE_OFF:
                    self._black_out(light, time_now)
                else:
                    self.context[light]['last_activity_secs'] = seconds_now
                    self._push_context()
                    self._switch_on(light, 0, max_brightness=not max_brightness or not all_is_on,
                                    force_switch_on=True, force_switch_off=True, time_now=time_now)
        elif all_is_on and len(off_group) > 0:
            self._switch_off(off_group, time_now=time_now)
        else:
            lights = self._config.entities_list('light', on_group)
            for light in lights:
                self.context[light]['last_activity_secs'] = seconds_now
                self._push_context()
            self._switch_on(on_group, switch_off, force_switch_on=True, force_switch_off=True, time_now=time_now)

    def switch(self, switch_name, switch_event):
        if self._inited is None:
            self._log("LightsControl is loading configuration")
            self.restart()
        if not self._inited:
            return
        if LOG_CALLS:
            self._log("LightsControl: switch({},{})".format(switch_name, switch_event))
        if switch_name not in self.switch_events:
            return
        if switch_event not in self.switch_events[switch_name]:
            return
        # TODO: check entities doubling among routines
        time_now = self._time_now()
        for routine in self.switch_events[switch_name][switch_event]:
            self._switch(routine, time_now=time_now)
        self._scheduled_run()

    def turn_on(self, light, brightness=None):
        if self._inited is None:
            self.restart()
        if not self._inited:
            return
        pass    # TODO: use to turn ON light so LightsControl can easily replace light actions

    def turn_off(self, light):
        if self._inited is None:
            self.restart()
        if not self._inited:
            return
        pass    # TODO: use to turn OFF light so LightsControl can easily replace light actions

    def toggle(self, light):
        if self._inited is None:
            self.restart()
        if not self._inited:
            return
        pass    # TODO: use to toggle light ON/OFF so LightsControl can easily replace light actions

    def set_level(self, light, level):
        if self._inited is None:
            self.restart()
        if not self._inited:
            return
        pass    # TODO: use to set light's brightness so LightsControl can easily replace light actions

    def _sensor_is_active(self, name, activating_value, active_time, time_now, value=None):
        if not isinstance(time_now, _ChoppedTime):
            time_now = _ChoppedTime(time_now)
        if value is None:
            value = value_get(self._h, name)
        if value is not None:
            if self._time_in_range(active_time, time_now):
                if self._value_is_within_range(value, activating_value):
                    return True
        return False

    def _all_sensors_are_inactive(self, light, time_now):
        if light not in self.sensor_lights:
            return True
        if light not in self.context:
            return True
        if not isinstance(time_now, _ChoppedTime):
            time_now = _ChoppedTime(time_now)
        for routine in self.sensor_lights[light]:
            if self._sensor_is_active(routine['sensor'],
                                      activating_value=routine['value'],
                                      active_time=routine['when'],
                                      time_now=time_now):
                return False
        return True

    def _sensor(self, light, sensor_value, routine, time_now):
        if light not in self.context:
            return
        if DISABLE_SENSORS_WITH_AUTOMATION and not self._automation_is_active(light):
            return
        if self._sensor_is_active(routine['sensor'],
                                  activating_value=routine['value'],
                                  active_time=routine['when'],
                                  time_now=time_now, value=sensor_value):
            self.context[light]['last_activity_secs'] = self._time_to_seconds(time_now)
            self._push_context()
            self._switch_on(light, routine['switch_off'], time_now=time_now)

    def sensor(self, sensor_name, sensor_value):
        if self._inited is None:
            self._log("LightsControl is loading configuration")
            self.restart()
        if not self._inited:
            return
        if LOG_CALLS:
            self._log("LightsControl: sensor({},{})".format(sensor_name, sensor_value))
        if sensor_name not in self.sensor_map:
            return

        # TODO: check entities doubling among routines
        time_now = self._time_now()
        for light in sorted(self.sensor_map[sensor_name].keys()):
            for routine in self.sensor_map[sensor_name][light]:
                self._sensor(light, sensor_value, routine, time_now)
        self._scheduled_run()

    def _flash(self, light, period, times):
        # TODO: make it async or run in separate thread
        if light not in self.context:
            return
        is_on = value_get(self._h, light, STATE_OFF) == STATE_ON
        if False:
            self._log("LightsControl: blinking light {} {} times".format(light, times))

        for i in range(0, times):
            if is_on:
                self.context[light]['last_action_secs'] = self._time_to_seconds(self._time_now())
                self._push_context()
                lights_off(self._h, light)
                sleep(period/2)
                self.context[light]['last_action_secs'] = self._time_to_seconds(self._time_now())
                self._push_context()
                lights_on(self._h, light)
                sleep(period/2)
            else:
                self.context[light]['last_action_secs'] = self._time_to_seconds(self._time_now())
                self._push_context()
                lights_on(self._h, light)
                sleep(period/2)
                self.context[light]['last_action_secs'] = self._time_to_seconds(self._time_now())
                self._push_context()
                lights_off(self._h, light)
                sleep(period/2)

    def _powersave(self, light, time_now):
        seconds_now = self._time_to_seconds(time_now)
        if light not in self.power_save:
            return False
        if light not in self.context:
            return
        for ps in self.power_save[light]:
            if seconds_now - self.context[light]['last_action_secs'] < ps['timeout']*60:
                continue
            for time_range in ps['when']:
                if self._time_in_range(time_range, time_now):
                    return True
        return False

    def _watchdog(self, light, light_current_state, time_now):
        # algorithm is:
        # if light is on:
        #   time to switch_off = (light's switch_off time or powersave condition) and all associated sensors are inactive
        #   if it's time to switch_off:
        #       switch_off if necessary
        #   elif max_brightness is not set:
        #       compare switch_on state with current state
        #       if state differs:
        #           update state (on/off/change brightness)
        # if light is off and is not blacked out:
        #       compare switch_off state with current state
        #       if state differs:
        #           update state (on/off/change brightness)

        if light not in self.context:
            return

        if not self._automation_is_active(light):
            return

        seconds_now = self._time_to_seconds(time_now)

        # Check triggerles sensors
        if light in self.sensor_lights:
            for routine in self.sensor_lights[light]:
                if routine['auto'] \
                        and self._sensor_is_active(routine['sensor'],
                                                   activating_value=routine['value'],
                                                   active_time=routine['when'],
                                                   time_now=time_now):
                    self._switch_on(light, routine['switch_off'], time_now=time_now)
                    return  # No need to proceed since light were just turned on

        on_state = self.context[light]['is_on']
        switch_off_notify = False
        if on_state > 0:    # Light is on
            all_sensors_inactive = self._all_sensors_are_inactive(light, time_now=time_now)

            if self._powersave(light, time_now) and all_sensors_inactive:  # It's time to switch off
                if light in self.notify_turn_off:
                    self.context[light]['notify'] = seconds_now
                    self.context[light]['notified'] = False
                    self.context[light]['switch_off'] = seconds_now + self.notify_turn_off[light]['before']
                else:
                    self.context[light]['notify'] = -1
                    self.context[light]['notified'] = False
                    self.context[light]['switch_off'] = seconds_now

            if 0 <= self.context[light]['notify'] <= seconds_now:
                switch_off_notify = True
                if self.context[light]['notified'] is False:
                    self.context[light]['notified'] = True

                    if self.notify_turn_off[light]['kind'] == 'flash':
                        period = self.notify_turn_off[light]['args']['period']
                        times = self.notify_turn_off[light]['args']['count']
                        self._flash(light, period/1000, times)
                    elif self.notify_turn_off[light]['kind'] == 'dim':
                        dim = self.notify_turn_off[light]['args']['brightness']
                        if dim < 1:
                            if dim < 0:
                                dim += light_current_state['brightness']
                            else:
                                dim = int(light_current_state['brightness'] * dim)
                        min_brightness = self.notify_turn_off[light]['args']['minimum']
                        dim = max(dim, min_brightness)

                        dim_state = deepcopy(light_current_state)
                        dim_state['brightness'] = dim
                        self.context[light]['last_action_secs'] = seconds_now
                        self._push_context()
                        self._schedule(lights_switch_state, self._h, light, dim_state)
                    else:
                        raise ValueError("Notify kind should be 'flash' or 'dim', other kinds are not supported yet")

            # Turn off when it's time to switch off
            if 0 <= self.context[light]['switch_off'] <= seconds_now and all_sensors_inactive:
                self._switch_off(light, time_now=time_now)

            # Update on state if necessary and no turn_off notification
            elif on_state != 2 and not switch_off_notify:
                _os = self._on_state(light, time_now=time_now)
                if _os['state'] != light_current_state['state'] or (
                        _os['state'] == STATE_ON
                        and 'brightness' in _os
                        and 'brightness' in light_current_state
                        and _os['brightness'] != light_current_state['brightness']
                ):
                    self._switch_on(light, time_now=time_now, switch_off=0, force_switch_on=True)
                    # switch_off=0 since switch_off time shouldn't be altered

        else:   # Light is off. Update off state if necessary
            if self.context[light]['is_on'] != -1:
                _os = self._off_state(light, time_now=time_now)
                if _os['state'] != light_current_state['state'] or (
                    _os['state'] == STATE_ON
                    and 'brightness' in _os
                    and 'brightness' in light_current_state
                    and _os['brightness'] != light_current_state['brightness']
                ):
                    self._switch_off(light, time_now=time_now)

    def watchdog(self):
        if self._inited is None:
            self._log("LightsControl is loading configuration")
            self.restart()
        if not self._inited:
            return
        lights = self._config.all_lights
        if LOG_WATCHDOG:
            self._log("LightsControl is running watchdog routine for {}".format(lights))

        time_now = self._time_now()
        for l in sorted(lights):
            state = light_state(self._h, l)
            if state is not None:
                self._watchdog(l, state, time_now)
        self._scheduled_run()

    def on_light_change(self, light, time_now=None):
        """
        Updates current light state
        Main use is for case if light were turned on/off by GUI or some other means, not by LightsControl
        """
        if self._inited is None:
            self._log("LightsControl is loading configuration")
            self.restart()
        if not self._inited:
            return
        if light not in self.context:
            return
        if time_now is None:
            time_now = self._time_now()
        seconds_now = self._time_to_seconds(time_now)
        if self.context[light]['last_action_secs'] + 2 < seconds_now:  # NOTE: 2 seconds margin for self's action
            ls = light_state(self._h, light)
            if ls is None:
                return
            if ls['state'] == STATE_ON:
                self.context[light]['is_on'] = [1, 2][ls['state'] != self._on_state(light, self._time_now())]
            else:
                self.context[light]['in_on'] = [0, -1][ls['state'] != self._off_state(light, self._time_now())]
            self.context[light]['switch_off'] = -1
            self.context[light]['notify'] = -1
            self.context[light]['notified'] = False
            if self.context[light]['is_on'] > 0:
                self.context[light]['last_activity_secs'] = seconds_now
            self._push_context()

    def dump(self):
        if self._inited is None:
            self._log("LightsControl is loading configuration")
            self.restart()
        if not self._inited:
            self._log("Dump: LightsConotrol is failed to init")

        data = {
            'switch_events': self.switch_events,
            'sensor_map': self.sensor_map,
            'sensor_lights': self.sensor_lights,
            'sensor_timeout': self.sensor_timeout,
            'on_state': self.on_state,
            'off_state': self.off_state,
            'power_save': self.power_save,
            'notify_turn_off': self.notify_turn_off,
            'automation_map': self.automation_map,
            'context': self.context,
        }
        self._log("Dump:")
        self._log(pprint.pformat(data, indent=4))
