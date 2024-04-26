"""
fadg : Main Config
==================

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
import yaml
import logging

logger = logging.getLogger(__name__)


class Config():

    def __init__(self):

        # Paths
        self.pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

        # Core Values, e.g., self.some_variable = None
        self.example = None

        return

    def readConfig(self, configFile=None):
        """Read the config file. If the configFile variable is not set,
        the class will look for the file in the source root folder.
        """
        if configFile is None:
            configFile = os.path.join(self.pkg_root, "config.yaml")

        if not os.path.isfile(configFile):
            logger.error("Config file not found: %s", configFile)
            return False

        try:
            with open(configFile, mode="r", encoding="utf8") as inFile:
                self._raw_conf = yaml.safe_load(inFile)
            logger.debug("Read config from: %s", configFile)
        except Exception as e:
            logger.error("Could not read file: %s", configFile)
            logger.error(str(e))
            return False

        # Read Values
        self._read_core()

        valid = self._validate_config()

        return valid

    ##
    #  Internal Functions
    ##

    def _read_core(self):
        """Read config values under 'dmci'."""
        conf = self._raw_conf.get("fadg", {})

        self.example = conf.get("example", self.example)

        return

    def _validate_config(self):
        """Check config variable dependencies. It needs to be called
        after all the read functions when all settings have been
        handled.
        """
        valid = True

        valid &= self._check_example_exists(self.example, "example")

        return valid

    def _check_example_exists(self, path, setting):
        """Check if an example exists, and if not report error."""
        if not isinstance(path, str):
            logger.error("Config value '%s' must be set", setting)
            return False
        return True

# END Class Config
