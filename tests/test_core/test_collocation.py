"""
Collocation : Collocation module tests
======================================

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
import pytest

from collocation.with_sar import get_odap
from collocation.with_sar import _get_sar_date


@pytest.mark.core
def test_get_odap():
    """ Test to find ocean and NWP model data matching Sentinel-1 file
    name.
    """

    # Sentinel-1 filename
    s1filename = (
        "sentinel-1/"
        "S1B_IW_RAW__0SDV_20190107T171737_20190107T171810_014391_01AC8B_78F4.zip")

    # Call odata to get url for matching model data
    norkyst_url, met_nordic_url = get_odap(s1filename)

    assert norkyst_url == ("https://thredds.met.no/thredds/fileServer/fou-hi/"
                           "norkyst800m-1h/NorKyst-800m_ZDEPTHS_his.an.2019010700.nc")
    assert met_nordic_url == ("https://thredds.met.no/thredds/fileServer/metpparchivev3/"
                              "2019/01/07/met_analysis_1_0km_nordic_20190107T17Z.nc")


@pytest.mark.core
def test__get_sar_date():
    """ Test for reading date from filename """
    s1filename = ("sentinel-1/"
                  "S1B_IW_RAW__0SDV_20190107T171737_20190107T171810_014391_01AC8B_78F4.zip")
    sd = _get_sar_date(s1filename)
    assert "%04d%02d%02dT%02d" % (sd.year, sd.month, sd.day, sd.hour) == "20190107T17"
