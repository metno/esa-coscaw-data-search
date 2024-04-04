"""
Collocation : Config class test
===============================

Copyright 2021 MET Norway

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os
import pytest

from tools import causeOSError

from collocation.config import Config


@pytest.mark.core
def testCoreConfig_example(rootDir, filesDir, monkeypatch):
    """ Test that the example config value is correct. This is an
    example for how to use the config settings.
    """
    theConf = Config()

    # Set wrong value
    theConf.example = None

    # Fake path
    assert not theConf.readConfig(configFile="not_a_real_file")

    exampleConf = os.path.join(rootDir, "example-config.yaml")

    # Cause the open command to fail
    with monkeypatch.context() as mp:
        mp.setattr("builtins.open", causeOSError)
        assert not theConf.readConfig(configFile=exampleConf)

    theConf.readConfig(exampleConf)

    assert theConf.example == "some-example-text"
    assert theConf._validate_config() is True

    # Read with no file path set, but a folder that contains the test file
    theConf.pkg_root = os.path.join(filesDir, "core")
    theConf.readConfig(configFile=None)

    assert theConf.example == "some-example-text-in-test-config"
    assert theConf._validate_config() is True

    # Test that function fails if example attribute is not a string
    theConf.example = None
    assert theConf._validate_config() is False
