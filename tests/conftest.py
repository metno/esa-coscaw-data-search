"""
Collocation : Test configuration
================================

Copyright 2024 MET Norway

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
import sys
import pytest

# This does not work for opendap, so it is omitted:
#   import socket
#
#   class block_network(socket.socket):
#       def __init__(self, *args, **kwargs):
#           raise Exception("Network call blocked")
#   socket.socket = block_network

# Note: This line forces the test suite to import the package in
#       the current source tree
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

from fadg.config import Config  # noqa: E402

##
#  Directory Fixtures
##


@pytest.fixture(scope="session")
def rootDir():
    """The root folder of the repository."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))


@pytest.fixture(scope="session")
def filesDir():
    """A path to the reference files folder."""
    testDir = os.path.dirname(__file__)
    theDir = os.path.join(testDir, "files")
    return theDir

##
#  Objects
##


@pytest.fixture(scope="session")
def s1filename():
    # Sentinel-1 filename
    return (
        "sentinel-1/"
        "S1B_IW_RAW__0SDV_20190107T171737_20190107T171810_014391_01AC8B_78F4.zip")


refs = [
    {
        "scheme": "OPENDAP:OPENDAP",
        "url": ("https://thredds.met.no/INVALID/thredds/dodsC/meps25epsarchive/2024/04/06/10/"
                "meps_mbr007_sfc_20240406T10Z.ncml")
    },
    {
        "scheme": "OGC:WMS",
        "url": ("https://fastapi.s-enda.k8s.met.no/INVALID/api/get_quicklook/2024/04/06/10/"
                "meps_mbr007_sfc_20240406T10Z.ncml?service=WMS&version=1.3.0&request"
                "=GetCapabilities?SERVICE=WMS&REQUEST=GetCapabilities")
    },
    {
        "scheme": "WWW:DOWNLOAD-1.0-http--download",
        "url": ("https://thredds.met.no/INVALID/thredds/fileServer/meps25epsarchive/2024/04/"
                "06/10/meps_mbr007_sfc_20240406T10Z.ncml")
    }
]


@pytest.fixture(scope="session")
def csw_record():
    """ Fake csw record
    """
    class Record:
        pass
    record = Record()
    record.references = refs
    return record


@pytest.fixture(scope="session")
def csw_records():
    """ Dict of fake csw records
    """
    class Record:
        pass
    rec1 = Record()
    rec1.references = refs
    rec2 = Record()
    rec2.references = refs
    records = {
        "rec1": rec1,
        "rec2": rec2,
    }
    return records


@pytest.fixture(scope="session")
def csw_4_records():
    """ Dict of fake csw records
    """
    class Record:
        pass
    rec1 = Record()
    rec1.references = refs
    # Nearest after
    rec1.time_coverage_start = "2024-04-06T10:00:00Z"
    rec1.time_coverage_end = "2024-04-06T10:02:00Z"
    rec2 = Record()
    rec2.references = refs
    rec2.time_coverage_start = "2024-04-07T10:00:00Z"
    rec2.time_coverage_end = "2024-04-07T10:02:00Z"
    rec3 = Record()
    rec3.references = refs
    rec3.time_coverage_start = "2019-01-06T10:00:00Z"
    rec3.time_coverage_end = "2019-01-06T10:02:00Z"
    rec4 = Record()
    rec4.references = refs
    # Nearest before
    rec4.time_coverage_start = "2019-01-07T10:00:00Z"
    rec4.time_coverage_end = "2019-01-07T10:02:00Z"
    records = {
        "rec1": rec1,
        "rec2": rec2,
        "rec3": rec3,
        "rec4": rec4,
    }
    return records


@pytest.fixture(scope="function")
def tmpConf(monkeypatch):
    """Create a temporary configuration object."""
    theConf = Config()
    confFile = os.path.join(theConf.pkg_root, "example_config.yaml")
    theConf.readConfig(confFile)
    return theConf
