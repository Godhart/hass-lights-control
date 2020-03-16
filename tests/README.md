Scripts below runs tests for lights_control object.

To run scripts with default params simply run following command from your shell: `python ./<script_name>`

After running script a folder with output result would be created:
* '.check_run_output' for script 'lights_control_check_1day_watchdog.py'
* '.1day_wd' for script 'lights_control_check_1day_watchdog.py'

You may also run script 'lights_control_check_1day_watchdog.py' to simulate your own configuration.
To perform this run script like this: 
```
python ./lights_control_check_1day_watchdog.py <path_to_your_config_relative_to_script> <result_folder_name>
```

For example to run this script with configuration 'example1' from 'example_configs' type:
```
python ./lights_control_check_1day_watchdog.py ../example_config/example1/lights_control.yaml .example1_1day_wd
```
