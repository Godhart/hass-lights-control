# LightsControl

![HASS Lights Control add-on standalone test](https://github.com/Godhart/hass-lights-control/workflows/HASS%20Lights%20Control%20add-on%20standalone%20test/badge.svg)

## Intro

A component for HASS (Home Assistant) providing general lights control automation logic.

Since all business logic is buried within component all that is left is to provide simple rules description 
for your lights, switches and sensors and customize behaviour as necessary.

> NOTE: You can try to use component with other automation systems besides HASS as it' lightly depends on it.
See 'Using with other automation systems' section.

## Features

* Short and simple automation description for environments with high amount of lights/switch buttons/sensors
* Switch buttons, Sensors, HASS states and other automations can be used to control lights
* Scheduled PowerSaving allows use different automatic turn-off scenarios
* Scheduled on/off states and light's brightness change provides comfortable lighting and nightlights
* Per light automation control - toggle off sensor based actions, automatic power savings and brightness change 
  but keep switch buttons related actions

## Details

> NOTE: some of described features are not implemented yet and going to be supported soon.
> Check TODOs in the end of document.

### Environment

It's assumed that you have some sort of following infrastructure, attached to your Home Assistance:

* Lights
* Switch buttons (optionally)
* Sensors  (optionally)

### General Idea

From the point of view by LightsControl there is two general states for each light - ON state and OFF state.
Also there is two special states - CUSTOM brightness, BLACKOUT (turned off)

Every light's ON state and OFF state can be customized and scheduled so you may set comfortable brightness 
level and even use light as nightlight, preventing it from turning off.
By default ON state is *[light is turned on to max brightness]* and OFF state is *[light it turned off]*

LightsControl's first task is to ensure that light's are turned on or off according to schedule you have
specified. So as time passes it would rise or lower brightness according to schedule and depending
on light' state - ON state or OFF state.

When you toggle lights with button or sensor by default it would be toggled between ON and OFF state.

> TODO: Pictures for illustrating

### On/Off states schedule

As it's said there is two general states for evey light (ON state and OFF state) defining how light
behaves.

By default light is turned on to max brightness in ON state and is turned off in OFF state.

Using on/off states schedule you may specify different brightness level and even prevent lights turning on 
for ON state. Also you may define lights to be turned on to some brightness level when they are in OFF state so you can 
use them as nightlights.

### Custom states

Sometimes it's necessary to turn lights to max brightness, fade them out or totally power off.

Special switches button events (so called 'magic' events) or
lights control from GUI or by any other means bypassing LightsControl object, may set them to 
CUSTOM or BLACKOUT state depending on current ON/OFF state.

If lights are switched to CUSTOM or BLACKOUT state then LightsControl won't change their brightness by schedule and 
would use only power saving logic to toggle into OFF state in case if lights were not blacked out.

### Lights toggling

That section describes main logic that toggles light's state. Lights are toggled by switch buttons and sensors.
Due to different nature of those two sources logic behinds is also different.

#### Switch buttons

Switch button action is treated as explicit intent and it's always toggles light between ON/OFF/CUSTOM/BLACKOUT states.

By default switch button action toggles light between ON/OFF state and CUSTOM/BLACKOUT states are used only under certain 
circumstances.

`Magic` events are used to toggle light into CUSTOM or BLACKOUT state. Which state would be toggled
depends on ON/OFF state:
* if OFF state is `off` then light would be toggled between CUSTOM(MAX brightness) and ON state (CUSTOM first)
* if OFF state is `on` then light would be toggled between CUSTOM(MAX brightness) and BLACKOUT (CUSTOM first)

Any event besides `magic` would toggle lights back into ON/OFF state (ON after BLACKOUT, OFF after CUSTOM)

Switch button action would toggle lights ON for undefined or for constrained period of time depending on configuration.
For more information check Power savings section.

Switch button action allows toggle few lights at once without need to put them into group but groups are also supported.
You can even separate lights list that are toggled ON from lights that are toggled OFF. And even more - you can toggle 
lights only ON or only OFF with switch button action (which comes in handy when you need to turn OFF all lights at once
with some special button event).

> NOTE: It's not necessary that switch action is initiated by real switch button. Actually you can trigger switch action
simply by calling LightsControl's `switch` method and specifying switch_name and switch_event that are already in your 
configuration.

#### Sensors

Sensors actions are treated as implicit intent so they are only used to to toggle light's to ON state and/or retain it.

By default lights are toggled ON only for constrained period of time. For more information check Power savings section.

Sensor values are checked and appropriate actions are taken by LightsControl in case if:
* You set trigger in automation for case when sensor's value becomes active and calling `sensor` method of LightsControl
to take actions immediately
* Sensor is set as Triggerles so LightsControl would check it's state periodically (default period is 5 secs) 
and turn lights ON if sensor state treated as active
* State of any sensor that is mentioned in configuration would be checked before switching lights off automatically.
Lights won't be switched off until all sensors' values becomes inactive. Even if sensor is without automation and not 
used in triggerles configuration

#### Light/Switch Proxy

LightsControl also supports methods `turn_on`/`turn_off`/`toggle` that are supported by `light` and `switch` entities, so 
existing lights automations can be adopted easily.

#### Integration with other Components

If you have other lights automations besides LightsControl, it's better to avoid controlling lights directly since
that could switch lights into CUSTOM/BLACKOUT state and break some automation. 
So you better use LightsControl as proxy for lights toggling. 

Call LightsControl `switch`/`turn_on`/`turn_off`/`toggle` action to toggle lights. 
When calling `switch` method you can use existing switch_name and switch_event OR define 
new switch_name and switch_event in LightsControl configuration (anything that comes to your mind) and use it instead.

Basically any HASS state can be used as sensor. But don't forget to include that state into LightsControl
configuration as sensor, otherwise it wouldn't have effect.
Also don't forget to write automation for calling LightsControl `sensor` when state becomes active or use 
Triggerles_Sensor configuration.

### Power Savings

Another powerful feature of LightsControl is Power Savings.

There is two types of power savings:
* Automatic switch off after switch on
* General power savings - switch off lights it is turned on longer than necessary at certain period of time

#### Automatic Switch Off after Switch On

For `switch`/`turn_on`/`toggle` and `sensor` action you can define `switch off` timeout.

Switch off timeout schedules time when light should be turned off after it was switched on.
Switch off timeout is planned when lights are toggled into ON or CUSTOM state and is cleared when lights toggled 
OFF/BLACKOUT.

There is 5 scenarios scenarios depending on current action switch off timeout and already scheduled switch off time:
* Switch off timeout is   -1: scheduled switch off for lights would be cleared
* Switch off timeout is Zero:  scheduled switch off time would remain same if set, new switch off time wont be set
* Switch off timeout is greater than Zero:
  * If no switch off time is scheduled then new switch off time is set as *[current time + switch off timeout]*
  * If switch off time is already scheduled then:
     * If *[current time + switch off timeout]* > scheduled switch off then new switch off time is set
     * Otherwise scheduled switch off time would remain same

In other words: switch off time can be cleared, left untouched, or extended by actions.

By default switch off timeout for `switch`/`turn_on`/`toggle` actions is `-1` so by default they clears scheduled 
switch off.

Default switch off timeout for `sensor` action is `5` minutes.

Actual switching off would be delayed until all sensors associated with light become inactive.


#### General Power Savings

It's obvious that during some time usually there is no need in lighting - like day times, times you away, times you asleep.
And if lights were turned ON during this period of time it's low probability they they were turned ON for long time.

So you can define power savings schedule to turn off lights automatically if they are turned on for long time.

In a schedule you specify period of time, list of lights, time since last turn on action before switching off. 
Last action is any action with light that turns lights on like sensor trigger, switch button, turn on via GUI and so on.

Automatic minor actions by LightsControl like brightness change, turn off notifications are not taken into account.

If LightsControl noticed that lights are in ON state or CUSTOM state for long time then it would toggle it into OFF state.
If lights are in BLACKOUT state - LightsControl would take no action.

Actual switching off would be delayed until all sensors associated with light become inactive.


### Automatic Turn Off Notification\

Of course some times you want lights to be turned ON for longer period than defined by your power saving options
and don't want to surprisingly find your self in a dark place.

You can turn off automatics for that light (don't forget to turn them off after you are done) OR configure LightsControl
to notify you before turing lights off.

You can set time before turn off to notify you and notification manner. Right now it's:
* light flashing 
* brightness change (which is more comfortable than flashing but requires special lights)

If it's time for automatic switch off but notification is configured for that light then
LightsControl performs notification action before switching lights off so you may notice it.

After notification were made and before lights would be turned off any switch button's event for this light 
(except those with empty 'lights_on' list )or sensor trigger will toggle lights back into ON state. 
Next switch off time would depend on event's switch off timeout. 

> NOTE: if you have bi-stable switches with on/off state, not click switches, then switch flicking (ON->OFF->ON) 
would make lights flash as you do that if you don't set inertial delay for switch OFF state automation

## Configuration

This section describes how to configure LightsControl and HASS automations for your needs.

### LightsControl configuration

LightsControl have following configuration sections:

#### Switch buttons configuration

Switch buttons actions are configured with Switch map.
Switch map is a dictionary. Every dictionary record contains list with switch button action definitions.

Switch map format:
```yaml
switch_map:
  <map_record_name>:      # Contains list with switch button actions definitions
    # Keyworded entry (aka dictionary)
    - button: <button_name>
      event: <click_event>
      switch_off: <switch_off_time> (optional)
      lights_on: <on_group> (optional)
      lights_off: <off_group> (optional)
    # Positional entry (aka list, required to be turned on specially)
    - [<button_name>, <click_event>, <switch_off_time> (optional), <on_group> (optional), <off_group> (optional)]
    # Mandatory fields:
    #   map_record_name:   a name to distinguish record. Also is used as default value for entity name in on/off_group
    #   button_name:       name of switch button that triggers action. Not necessary to be a real HASS entity name, but 
    #                      still it's recommended to use real switch button entity name associated with this action 
    #                      to ease automation.
    #   click_event:       name of button's event that triggers action or list of such events. Not necessary to be
    #                      a real event name but still it's recommended to use real switch event name associated with this 
    #                      action to ease automation.
    # Optional fields:
    #   switch_off_time:   switch off time in minutes for this action - integer in range from -1 and toward infinity. 
    #                      -1: clears switch off schedule
    #                      0:  keeps switch off schedule
    #                      >0:  extends switch off schedule if current_time + switch_off_time greater than current schedule
    #   on_group:          a list of entities to turn ON,  for example [light.A, light.B]. 
    #                      If empty list is specified (not omitted) then switch button only turns lights off
    #   off_group:         a list of entities to turn OFF, for example [light.A, light.B]
    #                      If empty list is specified (not omitted) then switch button only turns lights on
    
    # Defaults:
    #   switch_off_time:   -1
    #   on_group:          map_record_name would be used as on_group by default (i.e. on = [<map_record_name>])
    #   off_group:         off_group by default would be same as on_group
    
    # Automatic names completions:
    #   if button_name don't contains '.' then prefix 'button.' would be appended  
    #   if entity name in on_group or off_group don't contains '.' then prefix 'light.' would be appended 
```

#### Sensors configuration

Sensor actions are configured with Sensor map.
Sensor map is a dictionary. Every dictionary record contains list with sensor action definitions.

Sensor map format:
```yaml
sensor_map:
  <map_record_name>:      # Contains list with sensor action definitions
    # Keyworded entry (aka dictionary)
    - sensor: <sensor_name>
      value: <active_value> (optional)
      when: <active_time> (optional)
      switch_off: <switch_off_time> (optional)
      auto: <auto_trigger> (optional)
      lights_on: <on_group> (optional)
    # Positional entry (aka list, required to be turned on specially)
    - [<sensor_name>, <active_value> (optional), <active_time> (optional), <switch_off_time> (optional), 
       <auto_trigger> (optional), <on_group> (optional)]
    # Mandatory fields:
    #   map_record_name:   a name to distinguish record. Also is used as default value for entity name in on_group
    #   sensor_name:       a name of sensor
    # Optional fields:
    #   active_value:      sensor's state value which would be treated as active
    #                      possible active_value variants:
    #                      * scalar value - strict comparsion would be used
    #                      * list with two numbers - it would be checked that value falls within range between numbers
    #                      # TODO: other variants?
    #   active_time:       time range in which sensor should be used
    #                      Should be specified as single list with start/end time in format ["HH:MM:SS", "HH:MM:SS"]
    #                      or list of such lists like: [  ["HH:MM:SS", "HH:MM:SS"], ["HH:MM:SS", "HH:MM:SS"] ]
    #   switch_off_time:   switch off time in minutes for this action - integer in range from -1 and toward infinity. 
    #                      -1: clears switch off schedule
    #                      0:  keeps switch off schedule
    #                      >0:  extends switch off schedule if current_time + switch_off_time greater than current schedule
    #                      If value is not specified then it's -1
    #   auto_trigger:      specifies if LightsControl should poll sensor' state for checking active_value
    #                      if polled state is active_value then LightsControl assumes that sensor has been triggered
    #                      and toggles lights on according to record specification
    #                      0: don't poll. You should set HASS automation for turning light's on by sensor
    #                      1: do poll. LightsControl would turn lights automatically but with polling delay
    #                      Take a note: if you don't specify auto_trigger and don't set HASS automation
    #                      sensor's state will still be used to prevent lights from turning off automatically
    #                      but won't light it on
    #   on_group:          a list of entities to turn ON,  for example [light.A, light.B].  # TODO:
    
    # Defaults:
    #   active_value:      'on'
    #   active_time:       ["00:00:00", "23:59:59"]
    #   switch_off_time:   sensor_default_switch_off  - it's a configuration variable
    #   auto_trigger:      0
    #   on_group:          map_record_name would be used as on_group by default (i.e. on = [<map_record_name>])
    
    # Automatic names completions:
    #   if sensor_name don't contains '.' then prefix 'sensor.' would be appended  
    #   if entity name in on_group don't contains '.' then prefix 'light.' would be appended 
```

There is also variable that defines default sensors switch-off time:
```yaml
sensor_default_switch_off: <switch_off_time>
# switch_off_time:         Default switch off time for sensor actions in minutes
#                          If not specified then default switch off time would be 5 minutes 
```

#### General power savings

General power saving are defined with 'powersave' configuration variable.
Powersave is a dict. Every record is a power saving rule for certain period of time and for certain lights.

```yaml
power_save:
  <rule_name>:
    timeout: <switch_off_time> (optional)
    when: <active_time>   (optional)
    lights: <lights_list> (optional)
    # Mandatory fields:
    #   rule_name:         a name to distinguish record. Also is used as default value for entity name in lights field
    # Optional fields:     
    #   switch_off_time:   time of inactivity after which light may be turned off
    #                      no activity means no switch buttons actions or no triggered sensor actions
    #   active_time:       time range in which lights may be turned off for power savings
    #                      Should be specified as single list with start/end time in format ["HH:MM:SS", "HH:MM:SS"]
    #                      or list of such lists like: [  ["HH:MM:SS", "HH:MM:SS"], ["HH:MM:SS", "HH:MM:SS"] ]
    #   lights_list:       entities names that should be maintained by this power saving rule
    
    # Defaults:
    #   active_time:       ["00:00:00", "23:59:59"]
    #   switch_off_time:   60
    #   lights_list:       rule_name would be used as lights by default (i.e. lights_list = [<rule_name>])
    
    # Automatic names completions:
    #   if entity name in lights_list don't contains '.' then prefix 'light.' would be appended 
```

#### On/Off state customization

ON and OFF states are configured with `on_state` and `off_state` configuration variables accordingly.

Format:
```yaml
on_state:  # Specified state would be applied to lights in ON state
  <rule_name>: 
    # Keyworded entry (aka dictionary)
    # Time based ON/OFF states
    - when: <active_time>
      state: <light_state>
      lights: <lights_list> (optional)
    # State based ON/OFF states
    - sensor: <hass_state_name>
      value: <active_value>
      state: <light_state>
      lights: <lights_list> (optional)
    
    # Positional entry (aka list, required to be turned on specially)
    - [<active_time>, <light_state>, <lights_list> (optional) ]
    - [<hass_state_name>, <active_value>, <light_state>, <lights_list> (optional)]

off_state: # Specified state would be applied to lights in OFF state
  # off state is specified in same manner as on_state

    # Mandatory fields:
    #   rule_name:         a name to distinguish record. Also is used as default value for entity name in lights_list
    #   active_time:       time range when specified state should be applied
    #                      Should be specified as single list with start/end time in format ["HH:MM:SS", "HH:MM:SS"]
    #                      or list of such lists like: [  ["HH:MM:SS", "HH:MM:SS"], ["HH:MM:SS", "HH:MM:SS"] ]
    #   hass_state_name:   if specified HASS state's value is treated as active then specified light_state would 
    #                      be applied to light
    #   active_value:      defines condition to treat HASS state's value as active
    #                      possible active_value variants:
    #                      * scalar value - strict comparsion would be used
    #                      * list with two numbers - it would be checked that value falls within range between numbers
    #                      # TODO: other variants? like list with ranges, list with values
    #   light_state:       To which state light should be switched
    #                      possible light_state variants:
    #                      * 'on'  - light would be turned on to max brightness
    #                      * 'off' - light would be turned off
    #                      * number in range from 0 to 255 - light would be turned on to specified brightness
    #                      * string with HASS state that contains 'on', 'off' or number in range 0 to 255
    #                      # TODO: list with 3 numbers - red, green, blue. light would be turned on with specified tint
    # Optional fields:
    #   lights_list:       entities names to which specified state should be applied
    
    # Defaults:
    #   lights_list:       rule_name would be used as lights by default (i.e. lights_list = [<rule_name>])
    
    # Automatic names completions:
    #   if entity name in lights_list don't contains '.' then prefix 'light.' would be appended 
```

#### Turn off notification

Following

```yaml
notify_turn_off:
  # Keyworded entry (aka dictionary)
  <rule_name>: 
    kind: <notify_kind>
    before: <before_turn_off>
    lights: <lights_list> (optional)
    args: <notify_kind_args> (optional)
  # Positional entry (aka list, required to be turned on specially)
  <rule_name>: [<notify_kind>, <before_turn_off>, <notify_kind_args> (optional)]
    # Mandatory fields:
    #   rule_name:         a name to distinguish record. Also is used as default value for entity name in lights_list
    #   notify_kind:       turn off notification kind
    #                      possible variants:
    #                      * flash - light would flash once and briefly
    #                      * dim   - lights brightness would be changed for period of notification
    #   before_turn_off:   time in seconds to notify before turn_off
    # Optional fields:
    #   lights_list:       entities names to which specified state should be applied
    #   notify_kind_args   list or dict with custom arguments for notification method, meaning depends on notification 
    #                      kind.
    #                      for flash method: [<period>, <flashes_count>] 
    #                                     or {period: <period>, count: <flashes_count>}
    #                        - period:         single flash period in ms (default is 10 ms)
    #                        - flashes_count:  consequent flashes count (default is 5)
    #                      for dim method: [<level>, <minimum_level>] 
    #                                   or {brightness: <level>, minimum: <minimum_levle>}
    #                        - level:          brightness level
    #                                          possible values:
    #                                          * integer in range [1,255] - absolute brightness level
    #                                          * float in range (0,1)     - fraction brightness level
    #                                            sets brightness as fraction of ON state brightness level
    #                                          * integer in range [-255,-1] - relative brightness change
    #                                            sets delta to ON state brightness level.
    #                                            resulting brightness = ON state brightness + level value
    #                        - minimum_level:  minimum brightness level for relative/fraction brightness change
    
    # Format: light_name: [notify_kind, notify_before_turn_off in seconds, notify_kind_args if there is any]
    # If there is no '.' in name then 'light.' wold be append
    # notify_kinds:
    #   "flash" - quickly blink lights. flash args:
    #      - period in ms (default is 10 ms)
    #      - flashes count (default is 5)
    #   "dim"   - change lights brightness. dim args:
    #      - brightness level
    #          values above 1 sets absolute brightness
    #          values in range 0 <= x < 1 sets fraction of current brightness
    #          values below 0 sets relative brightness change
    #         (default is 50% of current),
    #      - minimum brightness level (default is 10)
    
    # Defaults:
    #   lights_list:       rule_name would be used as lights by default (i.e. lights_list = [<rule_name>])
    
    # Automatic names completions:
    #   if entity name in lights_list don't contains '.' then prefix 'light.' would be appended 
```

#### Automation control

You can turn most of lights automations except swtiches and sensor without need to turn LightsControl off.
And you can do this on per light basis.

For this you need to create 'dummy' automation entities in your HASS configuration. All is required - give them names,
but no triggers and actions.

For example (HASS automations configuration):
```yaml
automation:
   - alias: <light_entity_name>
     trigger: # TODO: something that would never happend
     action:  # TODO: something not harmful
```

Then map these automation objects to lights in LightsControl configuration like this:

```yaml
automation_map:
    <automation_entity_name>: <light_entity_name>
    <automation_entity_name>: [<light_entity_name_1>, <light_entity_name_2>, ...]
    # Automatic names completions:
    #   if light_entity_name name don't contains '.' then prefix 'light.' would be appended 
    #   if automation_entity_name name don't contains '.' then prefix 'automation.' would be appended 
```

Now when you turn off automation for some lights LightsControl would only toggle them to ON/OFF/CUSTOM/BLACKOUT state
by switch button actions or sensor's triggers.

### A Note about Groups

You can use groups as entities names in LightsControl configuration. On start LightsControl would extract lights
list for each group you mentioned, store it and would be using stored group mapping. It's required to properly
manage state of each light in a group.

If you ever modify HASS groups and do `hass.reload_groups`, LightsControl still be using stored values.
To make LightsControl use new groups definition without LightsControl restart/HASS reboot call
`lights_control.reload_groups` for LightsControl entity.

## Services

> TODO: Services description

## HASS Configuration Hints

### Making it work in HASS

> TODO: Describe necessary configuration for HASS automation, give example

### How to reduce configuration size

> TODO: General recommendations to use templates, refer to Zigbee for example

### Zigbee recommendations

> TODO: Describe necessary configuration for HASS automation, give example

# Using with other automation systems

There is no detailed description for this yet but you can try to figure it out by your self with following hints:

1. Replace `lights_control_core\_hass_helpers.py` methods so they would interact with your automation system
2. Bind core logic to your automation system. For HASS bindings are done int `__init__.py` of this folder

This should be enough.

# TODOs:

> TODO: make sure groups are supported properly

> TODO: make sure that automation for groups update works

> TODO: support turn_on/turn_off/toggle/set_level so LightsControl can be used as light proxy

> TODO: resolve overlapping time ranges

> TODO: support lights tinting. can be combined with brightness?

> TODO: support ANDing sensor conditions
