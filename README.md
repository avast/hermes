# Hermes
Hermes is an SMTP honeypot built on top of the Salmon mail server (https://pypi.org/project/salmon-mail/). It has all the features of Salmon, but our code has been added to create a honeypot so it is now only used as an SMTP server and it is not reasonable to use it like anything else.

## Features
All hermes features can be set in the `configuration/salmon.yaml` configuration file, which is located in the `salmon-honeypot/configuration/` path after installation. If you decide to install honeypot using Ansible playbook, this file is created interactively.

* Honeypot supports Python 3.
* Periodic inspection that the honeypot is running.
* SMTP server listening on the required port and IP address.
* SMTP AUTH command support. Credentials can be set in the configuration file.
* You can configure exim 4 (port and IP address).
* You can turn off e-mail relaying completely. Or you can leave it on and the honeypot will decide which e-mail to relay.
* Possibility to save eml file and email attachment.
* Destroying of attachments, links, and reply-to field.
* Rule file where it is possible to specify the e-mail to be relayed.
* MQTT support.
* Intelligent spam relaying.
* Fast honeypot start, stop, restart using commands `salmon-receiver <start|stop|restart>` and `salmon-relay <start|stop|restart>`.

## Installation
### Shell script
Honeypot can be installed using a shell script in `configuration/install.sh`. The script must be run from the `configuration` directory as:

    ./install.sh -p <path>

The path is either a relative or absolute path to the directory where the honeypot is to be installed. The directory must already exist.
The script is primarily intended for users who do not have Ansible installed. The script assumes that the honeypot doesn't exist before the script is run. You must also clone the source repository first.
After installation, it's up to you if you want to have two cron jobs to delete old records from the maybe_test_emails table and to check that the honeypot is running. It is also highly recommended to use logrotate because salmon-honeypot logs can be large after some time. By default, the debug level is set to DEBUG in `salmon-honeypot/salmon-relay/myproject/config/logging.conf` after installation. I recommend changing the level to INFO or the salmon.log file will be very long very soon. Also add on line 12 helo_data = hermes to the file /etc/exim4/conf.d/transport/30_exim4-config_remote_smtp. The ansible playbook takes care of this itself.

### Ansible
Honeypot can be installed using the Ansible playbook in `ansible/honeypot.yml`.
You don't need to have the git repository cloned on your local host. You need files from the `ansible` directory and you need to have Ansible installed on your local host.
You can find [here](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html) how to install Ansible according to the Linux distribution. I recommend installation using pip3:

    pip3 install ansible

Missing packages on your local host can be `pip3`, `sshpass`. Install as:

    sudo apt install python3-pip
    sudo apt install sshpass

If you have ansible installed, go to the `ansible` directory where the playbook is located. Change the IP address of the managed host in the `inventory` file. Make sure you're using the correct version of the ansible configuration file using the ansible command `ansible --version`, which must show you something like this:

```
ansible 2.9.9
  config file = /path/to/git_repository/ansible/ansible.cfg
  configured module search path = ['$HOME/.ansible/plugins/modules', '/usr/share/ansible/plugins/modules']
  ansible python module location = $HOME.local/lib/python3.7/site-packages/ansible
  executable location = $HOME.local/bin/ansible
  python version = 3.7.3 (default, Dec 20 2019, 18:57:59) [GCC 8.3.0]
```

Run playbook as:

    ansible-playbook honeypot.yml

You will be prompt to type the password for the remote host. At the end of the installation you will need to type some specifications for `salmon.yaml`.
The playbook will add two cron jobs (see `crontab -e`) and it will add a logrotate setting to `/etc/logrotate.d/salmon`.
If you want to log on to the remote host other than as root, you must change `remote_user = root` to `remote_user = your_user` and `become_ask_pass = false` to `become_ask_pass = true` in the `ansible.cfg` file.

If you want to run a program that checks the `run/queue` directory for incoming e-mails, go to `salmon-honeypot/salmon-receiver/myproject/run/` after installation and run:

    python3 new_email_inotify.py -r <your_email_address>

## Testing
In `relay/new/tests` there are tests written using pytest. Go to the test directory (after installation) and run the tests as:

    ./run_tests.sh

This runs the tests in `test_models.py`, `test_mailparser.py`, and `test_conclude.py`. Don't run the tests in any other way as they need to have the `SALMON_SETTINGS_MODULE` environmental variable set. These tests use their own configuration file `testing_salmon.yaml` and in memory database.
Another test is in the `test_permeability.py` file. Run as:

    python3 test_permeability.py -p "<absolute_path_to_directory_with_eml>"

or if you want to use an ssh connection (assuming that port 22 is open)

    python3 test_permeability.py -p "<path_to_directory_with_eml>" --scp --password "<password_for_host>" --username "<username_for_host>" --hostname "<hostname|IP>"

or if you want to test only 10 e-mails in the directory

    python3 test_permeability.py -p "<absolute_path_to_directory_with_eml>" -n 10

There is also a test `test_honeypot_working.py` located in the directory `salmon-honeypot/configuration/` after installation. This test will try to send an e-mail using salmon-honeypot and then check your inbox to see if the e-mail has arrived. Run as:

    python3 test_honeypot_working.py --listenhost "<IP_of_salmon_receiver>" --listenport <port_of_salmon_receiver> --recipient "<your_email_address>" --password "<your_password>"

By default it uses `imap.seznam.cz` imap server so if you want to use e-mail address from another account, you have to specify another imap server using `--imap "<imap_server>"`.

## Statistics
See honeypot statistics after installation in `salmon-honeypot/salmon-relay/myproject`:

    cd salmon-honeypot/salmon-relay/myproject
    ./statistics.sh
