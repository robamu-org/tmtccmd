## How to set up the repository

It is recommended to fork this repository for new missions in a separate folder 
which will be the primary folder for the TMTC commander software.
In this example, we will clone this repository as a submodule in a `tmtc` folder, and we
will assume that the `tmtc` folder is located inside a folder called `obsw` which also contains
the primary OBSW. The following steps will be shown in the command line to be more generic.

It is assumed that this folder is already 
a git repository. If not, it can be transformed to one using `git init`.

```sh
cd obsw
mkdir tmtc
cd tmtc
git submodule add https://git.ksat-stuttgart.de/source/tmtccmd.git
```

Copy the contents of the `user` folder inside the `tmtccmd` folder to the `tmtc` folder
```sh
cd tmtccmd
cp tmtccmd/user/* . -r
cd ..
```

Optional: Install all required packages by running:
```sh
pip install -r requirements.txt
```

Now the script can be tested with the following command.
```sh
python tmtc_client_cli.py -h
```

It is recommended to use and setup PyCharm to also use the preconfigured
run configurations. A few run configurations have been provided. 
To use them, open the `tmtc` folder as a PyCharm project first.
Then copy the configuration files into the `runConfigurations` folder 
in the `.idea` folder.

```sh
cd tmtc
cp tmtccmd/runConfigurations/* .idea/runConfigurations/
```

## How to use the TMTC commander

The files copied from the user folder should provide a good set of adaption points to configure
the TMTC commander. For example, the config folder contains configuration for the possible global parameters,
object IDs, modes etc.

The `pus_tc` and `pus_tm` folder contain adaption points to pack telecommands and specify how to 
handle incoming telemetry. Right now, only the ECSS PUS packet standard is supported.

It is recommended to use PyCharm and load the run configurations
to have a starting point. PyCharm also provided the option  of remote deployment, which allows TMTC testing 
with remote setups (e.g. flatsat setup in a cleanroom).

Some configuration constants might be stored in a JSON file in the
config folder. To reset the configuration, delete the JSON file.

### Command line mode

The script can be used by specifying command line parameters.
Please run this script with the -h flag or without any command line parameters to 
display options. 

### Import run configurations in PyCharm
The PyCharm IDE can be used to comfortably manage a set of run configuations 
(for example tests for different services). These configurations were shared 
through the version control system git and should be imported automatically. 
If these configurations don't show up, try to open the tmtc folder as
a new PyCharm project in a new window. 
 
To add new configurations, go to Edit Configurations... 
in the top right corner in the drop-down menu.
Specify the new run configurations and set a tick at Share through VCS. 

### Examples

Example command to send a ping command. Specify the communication interface by 
adding `-c <number>` to the command.
```sh
tmtc_client_cli.py -m 3 -s 17
```

Example to run listener mode
```sh
tmtc_client_cli.py -m 1
```

## Architectural notes

Some additional information about the structure of this Python program 
are provided here.

### Modes and the TMTC queue
There are different communication modes. Run the client with the `-h` flag
to display the modes. The TMTC commander is able to send multiple telecommands
sequentially by using a provided queue. The queue is filled by the
developer. Some examples can be found in the `tc` folder. The queue
can also be filled with special commands, for example a wait command or 
a print command.

This application is also able to listen to telemetry packets in a separate thread.
The specific TM handling is also implemented by the developer. Some
examples can be found in the `tm` folder.

### Communication Interfaces

The communication interfaces decouple the used interface from the communication
logic. This enables to write the telecommand and telemetry specifications
without worrying about the used communication interface.

#### Serial Communication
Serial communication was implemented and is tested for Windows 10 and Ubuntu 20.04.
It requires the PySerial package installed.
It should be noted that there are several modes for the serial communication.
There is a fixed frame mode, and a mode based on a simple DLE transport layer.
When using the DLE transport layer, sent packets are encoded with DLE while 
received packets need to be DLE encoded.

## Common Issues

### Ethernet Communication
If there are issued with the Ethernet communcation, 
there might be a problematic firewall setting.
It might be necessary to allow UDP packets on certain ports

### PyCharm Problems
If PyCharm does not display console output, make sure the system interpreter
is set to `python.exe` and not `pythonw.exe`.

## Developers Information
Code Style: [PEP8](https://www.python.org/dev/peps/pep-0008/).

Can be enforced/checked by using Pylint as an external program in PyCharm.
Install it with pip and then install and set up the Pylint plugin in PyCharm.

There are a lot of features which would be nice, for example a GUI.
The architecture of the program should allow extension like that without
too many issues, as the sending and telemetry listening are decoupled.