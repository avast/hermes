#!/bin/bash

DIRECTORY="salmon-honeypot"
GREEN='\e[32m'
RED='\033[0;31m'
NOCOLOR='\033[0m'
python_ver=`python3 --version`
IFS='.'
read -ra ADDR <<< "$python_ver"
version="${ADDR[1]}"

usage()
{
    echo "Tell me where this honeypot should be installed"
    echo "Usage: $0 -p <path>" 1>&2; exit 1;
}

while getopts "p:" opt; do
    case "${opt}" in
        p)
            p=${OPTARG}
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

echo "path = $(readlink -e $p)"
if [ -z "${p}" ]; then
    usage
fi

if [ ! -d $SALMON_PATH ]; then
    echo "The directory should already exist"
    usage
fi
SALMON_PATH=$(readlink -e ${p})
echo "This installation script can be run only from the configuration directory"
echo "where is also saved, are you in the directory?"
read -p "Press enter to continue"

setup_of_packages()
{
    pkgs=("exim4-daemon-light" "git" "python3-distutils" "build-essential" "libffi-dev" "python3" "python3-dev" "python3-pip" "automake" "autoconf" "libtool" "libfuzzy-dev" "sqlite3" "libsqlite3-dev")

    for needed_pkg in "${pkgs[@]}"
        do
            dpkg -s $needed_pkg > /dev/null 2>&1;
            if [ "$?" -ne "0" ]; then
                echo "Installing missing package $needed_pkg"
                sudo apt-get install $needed_pkg -y > /dev/null 2>&1;
                if [ "$?" -ne "0" ]; then
                    echo -e "${RED}ERROR: Couldn't install $needed_pkg ${NOCOLOR}"
                fi
            fi
        done

    daemon_smtp_ports=`cat /etc/exim4/exim4.conf.template | sed -n '33p'`
    if [ $daemon_smtp_ports != "daemon_smtp_ports=2500" ]; then
        sudo sed -i -e '32a\daemon_smtp_ports=2500' /etc/exim4/exim4.conf.template
    fi

    cat /etc/exim4/update-exim4.conf.conf | grep internet > /dev/null 2>&1;
    if [ "$?" -ne "0" ]; then
        sudo sed -i s/dc_eximconfig_configtype=\'local\'/dc_eximconfig_configtype=\'internet\'/ /etc/exim4/update-exim4.conf.conf
    fi

    sudo systemctl restart exim4

    ps -ef | grep exim4 | grep -v grep > /dev/null 2>&1;
    [ $?  -eq "0" ] && echo -e "${GREEN} exim4 is running ${NOCOLOR}" || echo -e "${RED} exim4 is not running, check /var/log/exim4/ ${NOCOLOR}"
}

setup_of_salmon()
{
    if [ ! -d $HOME/bin ]; then
        mkdir $HOME/bin
    fi

    chmod +x salmon-receiver.sh
    cp -r salmon-receiver.sh $HOME/bin
    chmod +x salmon-relay.sh
    cp -r salmon-relay.sh $HOME/bin

    CONFIGURATION=$(readlink -e .)

    cd /usr/bin/
    if [ ! -f /usr/bin/salmon-receiver ]; then
        sudo ln -s $HOME/bin/salmon-receiver.sh salmon-receiver
    fi
    if [ ! -f /usr/bin/salmon-relay ]; then
        sudo ln -s $HOME/bin/salmon-relay.sh salmon-relay
    fi

    cd $CONFIGURATION
    RECEIVER=$(readlink -e ../receiver)
    RELAY=$(readlink -e ../relay)
    cd $SALMON_PATH
    if [ ! -d $DIRECTORY ]; then
        mkdir $DIRECTORY
        chmod 755 $DIRECTORY
        cd $DIRECTORY
        export WORK_PATH=$(readlink -e .)
        sudo pip install virtualenv
        mkdir configuration
    else
        cd $DIRECTORY
        export WORK_PATH=$(readlink -e .)
        sudo pip install virtualenv
        mkdir configuration
    fi
}

append_directory()
{
    printf "\ndirectory:
    queuepath: $WORK_PATH/salmon-receiver/myproject/run/queue
    undeliverable_path: $WORK_PATH/salmon-receiver/myproject/run/undeliverable
    rawspampath: $WORK_PATH/salmon-receiver/myproject/run/rawspams
    attachpath: $WORK_PATH/salmon-receiver/myproject/run/attachments\n">>$WORK_PATH/configuration/salmon.yaml
}

install_receiver()
{
    echo -e "${GREEN}Installing receiver${NOCOLOR}"
    virtualenv -p /usr/bin/python3 $WORK_PATH/salmon-receiver
    source $WORK_PATH/salmon-receiver/bin/activate
    cd $WORK_PATH/salmon-receiver
    pip install PyYAML==5.3.1
    pip install salmon-mail==3.2.0
    pip install apscheduler==2.1.2
    pip install inotify
    salmon gen myproject
    cp -r $RECEIVER/changed/queue.py lib/python3.$version/site-packages/salmon/
    cp -r $RECEIVER/changed/server.py lib/python3.$version/site-packages/salmon/
    cp -r $RECEIVER/changed/smtpd.py lib/python3.$version/site-packages/salmon/
    cp -r $RECEIVER/changed/handlers/queue.py lib/python3.$version/site-packages/salmon/handlers/
    cp -r $RECEIVER/changed/boot.py myproject/config/
    cp -r $RECEIVER/changed/settings.py myproject/config/
    cp -r $RECEIVER/changed/sample.py myproject/app/handlers/
    cp -r $RECEIVER/new/new_email_inotify.py $WORK_PATH/salmon-receiver/myproject/run/
    cp -r $CONFIGURATION/salmon.yaml $WORK_PATH/configuration/
    cp -r $CONFIGURATION/rules.json $WORK_PATH/configuration/
    mkdir -p myproject/run/queue/cur
    mkdir -p myproject/run/queue/new
    mkdir -p myproject/run/queue/tmp
    mkdir -p myproject/run/rawspams
    mkdir -p myproject/run/undeliverable
    mkdir -p myproject/run/attachments
    append_directory
    deactivate
    cd $WORK_PATH
}

install_relay()
{
    echo -e "${GREEN}Installing relay${NOCOLOR}"
    virtualenv -p /usr/bin/python3 $WORK_PATH/salmon-relay
    source $WORK_PATH/salmon-relay/bin/activate
    cd $WORK_PATH/salmon-relay
    pip install PyYAML==5.3.1
    pip install salmon-mail==3.2.0
    pip install spacy
    pip install apscheduler==2.1.2
    pip install ssdeep
    pip install SQLAlchemy
    pip install psutil
    pip install pytest
    pip install essential_generators
    pip install scp
    pip install PrettyTable
    salmon gen myproject
    cp -r $RELAY/changed/queue.py lib/python3.$version/site-packages/salmon/
    cp -r $RELAY/changed/routing.py lib/python3.$version/site-packages/salmon/
    cp -r $RELAY/changed/server.py lib/python3.$version/site-packages/salmon/
    cp -r $RELAY/changed/mail.py lib/python3.$version/site-packages/salmon/
    cp -r $RELAY/changed/boot.py myproject/config/
    cp -r $RELAY/changed/settings.py myproject/config/
    cp -r $RELAY/changed/sample.py myproject/app/handlers/
    cp -r $RELAY/new/salmonconclude.py lib/python3.$version/site-packages/salmon/
    cp -r $RELAY/new/salmondb.py lib/python3.$version/site-packages/salmon/
    cp -r $RELAY/new/salmonmailparser.py lib/python3.$version/site-packages/salmon/
    cp -r $RELAY/new/salmonrelay.py lib/python3.$version/site-packages/salmon/
    cp -r $RELAY/new/salmonscheduler.py lib/python3.$version/site-packages/salmon/
    cp -r $RELAY/new/salmonspam.py lib/python3.$version/site-packages/salmon/
    cp -r $RELAY/new/base.py lib/python3.$version/site-packages/salmon/
    cp -r $RELAY/new/tests/* myproject/tests/
    cp -r $RELAY/new/salmonerrornotifier.py $WORK_PATH/configuration/
    cp -r $RELAY/new/salmondeleteold.py myproject/
    cp -r $RELAY/new/salmondeleteold.sh myproject/
    cp -r $CONFIGURATION/../print_statistics.py myproject/
    cp -r $CONFIGURATION/../statistics.sh myproject/
    cp -r $CONFIGURATION/../test_honeypot_working.py $WORK_PATH/configuration/
    pip install git+https://github.com/avast/iottl-dracula.git
    python -m spacy download en_core_web_sm
    deactivate
    pip3 install PyYAML
    pip3 install psutil
    cd $WORK_PATH
}

setup_of_packages
setup_of_salmon
install_receiver
install_relay
