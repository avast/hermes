source ../../bin/activate
export SALMON_SETTINGS_MODULE="tests.testing_settings"
pytest test_models.py -v --disable-pytest-warnings
pytest test_mailparser.py -v --disable-pytest-warnings
pytest test_conclude.py -v --disable-pytest-warnings
unset SALMON_SETTINGS_MODULE
deactivate
