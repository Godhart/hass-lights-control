Hello! I want to introduce my component for Home Assistant.

It's in early stage - tested only for myself and I haven't tested it really thoroughly yet but I think you might be 
interested to try it.

# Short intro
I'm using HASS mostly for controlling lights and few power relays. In my setup there is about 20 light groups and 4 
relays by now. For each group there is at least one switch button. In addition to this there is bunch of sensors. 
Relays are turned on/off by automation rules only. 

> Just for a note: switch buttons, sensors and some relays are Aquara with zig-bee connection and integrated to 
HASS via MQTT. Lights switching and other relays are controlled by Arduino board running my own firmware with my own 
integration to HASS, but it's not a subject now.

It was rather easy to bind switches to lights and do some simple automations though configuration became large and there
were too much copy-pasting. 

> I didn't get idea of templating at that time since it was my first try and I was in hurry
to make it work. As I now understand more about templating I think that could probably help me a lot but still some things could be 
though.

In the end I got configuration that works but hard to support. Besides I hadn't found easy way for describing some 
automations that is more than just toggling lights by switch or sensor like notification before automatic turn-off,
time based power savings, dynamic lighting. 

I had described notification actions for few important places but when I wanted to apply those rules to other lights 
groups I just imagined how would configuration look and I came do decision that I need something else.

# LightsControl component
I've got idea that I need short description of automation rules that are specific to lighting control subject.

First I tried to accomplish this with a Python script but in the end I made custom HASS component which can be found
here [link].

That component covers common automation tasks for toggling lights and relays with switch buttons, sensors
(my own experience is limited to MQTT and Aquara) and by other HASS object's states.

Also component covers power savings logic and conditional/dynamic lighting (only brightness is supported yet),
provides notifications before turning lights off by blinking or dimming lights.

Also I'm going to make it work along with other dynamic lighting controllers a bit later.

Rules description is pretty short and fits into few screens for bunch of lights and switches so you can estimate 
expected result with single view. It's easy to review and edit it since you can understand it all and at once.

Besides that component and it's configuration can be tested/estimated in stand alone mode without need to embed 
it into HASS. To conduct tests HASS is mocked and time is simulated.
Example configuration and scripts for testing are included.

> It takes 40 seconds on my celeron laptop to simulate single hour for my setup with 1 second step. 
Timescale if about 1:80.

Check out more details on project's git hub page [link].

Have fun!
