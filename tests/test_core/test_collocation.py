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
import datetime

from unittest.mock import Mock
from dateutil import tz
from dateutil.parser import parse

from collocation.with_sar import Collocate
from collocation.with_sar import METNordic
from collocation.with_sar import NorKyst800
from collocation.with_sar import AromeArctic
from collocation.with_sar import Meps
from collocation.with_sar import WeatherForecast


refs = [
    {
        "scheme": "OPENDAP:OPENDAP",
        "url": ("https://thredds.met.no/thredds/dodsC/meps25epsarchive/2024/04/06/10/"
                "meps_mbr007_sfc_20240406T10Z.ncml")
    },
    {
        "scheme": "OGC:WMS",
        "url": ("https://fastapi.s-enda.k8s.met.no/api/get_quicklook/2024/04/06/10/"
                "meps_mbr007_sfc_20240406T10Z.ncml?service=WMS&version=1.3.0&request"
                "=GetCapabilities?SERVICE=WMS&REQUEST=GetCapabilities")
    },
    {
        "scheme": "WWW:DOWNLOAD-1.0-http--download",
        "url": ("https://thredds.met.no/thredds/fileServer/meps25epsarchive/2024/04/"
                "06/10/meps_mbr007_sfc_20240406T10Z.ncml")
    }
]


class MockCSW:

    test = "test"

    def __init__(self, *args, **kwargs):
        return None

    def getrecords2(self, *args, **kwargs):
        class Record:
            pass
        rec1 = Record()
        rec1.references = refs
        rec2 = Record()
        rec2.references = refs
        self.records = {
            "rec1": rec1,
            "rec2": rec2,
        }
        # Force while loop to continue until
        # start_position >= max_records:
        self.results = {"nextrecord": 1}


@pytest.mark.core
def testCollocate__execute(s1filename, monkeypatch):
    """ Test that the csw connection is called, and that the function
    returns a dict.
    """
    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_sar.CatalogueServiceWeb", MockCSW)
        coll = Collocate(s1filename)
        records = coll._execute([])
        assert records["rec1"].references == refs


@pytest.mark.core
def testCollocate_get_odap_url_of_nearest(s1filename, csw_records, monkeypatch):
    """ Test that the nearest record in time_coverage_start has the
    correct opendap url.
    """
    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_sar.CatalogueServiceWeb", MockCSW)
        coll = Collocate(s1filename)
        tt = coll.get_odap_url_of_nearest()
        assert tt == ("https://thredds.met.no/thredds/dodsC/meps25epsarchive/2024/04/06/10/"
                      "meps_mbr007_sfc_20240406T10Z.ncml")


@pytest.mark.core
def testCollocate_get_collocations(s1filename, monkeypatch):
    """ Test that get_collocations returns a dict of records.
    """
    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_sar.CatalogueServiceWeb", MockCSW)
        coll = Collocate(s1filename)
        records = coll.get_collocations()
        assert records["rec1"].references == refs


@pytest.mark.core
def testCollocate_Init(s1filename):
    """ Test initialization of Collocate.
    """
    coll = Collocate(s1filename)
    tt = datetime.datetime(2019, 1, 7, 17, 17, 37, tzinfo=tz.gettz("UTC"))

    assert coll.sar_url == s1filename
    assert coll.time == tt
    assert coll.time.tzinfo == tz.gettz("UTC")


@pytest.mark.core
def testCollocate_set_csw_connection(s1filename, monkeypatch):
    """ Test establishment of CSW connection but without actual
    connection to a CSW service.
    """
    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_sar.CatalogueServiceWeb", MockCSW)
        coll = Collocate(s1filename)
        coll._set_csw_connection()
        assert coll.conn_csw.test == "test"


@pytest.mark.core
def testCollocate_search_functions(s1filename):
    """ Test that search xml files can be created from the search
    objects returned by the search functions.

    Note: Ideally, we should mock the owslib but this has not been
    done here, partly because of laziness and partly to better
    understand owslib..
    """
    coll = Collocate(s1filename)
    ss = coll._get_title_search("Arome-Arctic")
    assert ss.toXML().getchildren()[0].text == "dc:title"
    assert ss.toXML().getchildren()[1].text == "Arome-Arctic"
    ss = coll._get_free_text_search("whatever")
    assert ss.toXML().getchildren()[0].text == "csw:AnyText"
    assert ss.toXML().getchildren()[1].text == "whatever"
    start, end = coll._temporal_filter()
    assert start.toXML().getchildren()[1].text == "2019-01-08 17:17:37"


@pytest.mark.core
def testCollocate_get_odap_url(csw_record):
    """ Test that the opendap url is returned.
    """
    assert Collocate.get_odap_url(csw_record) == ("https://thredds.met.no/thredds/dodsC/"
                                                  "meps25epsarchive/2024/04/06/10/"
                                                  "meps_mbr007_sfc_20240406T10Z.ncml")


class MockDataset:

    def __init__(self, *args, **kwargs):
        self.time_coverage_start = "2024-04-06T10:00:00Z"
        self.time_coverage_end = "2024-04-06T10:02:00Z"

    def close(self):
        return None


class MockDataset2:

    def __init__(self, *args, **kwargs):
        self.time_coverage_start = "2024-04-07T10:00:00Z"
        self.time_coverage_end = "2024-04-07T10:02:00Z"

    def close(self):
        return None


@pytest.mark.core
def testCollocate_get_time_coverage(csw_record, monkeypatch):
    """ Test that netCDF4.Dataset is called, and that correct times
    are returned.
    """
    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_sar.netCDF4.Dataset", MockDataset)
        start, end = Collocate.get_time_coverage(csw_record)
        assert start == parse("2024-04-06T10:00:00Z")
        assert end == parse("2024-04-06T10:02:00Z")


@pytest.mark.core
def testCollocate_get_nearest_collocation_by_time(s1filename, csw_records, monkeypatch):
    """ Test that the nearest record in time_coverage_* is returned.
    """
    class SelectMock(Mock):
        pass

    with monkeypatch.context() as mp:
        smock = SelectMock()
        smock.side_effect = [MockDataset(), MockDataset2(), MockDataset(), MockDataset2()]
        mp.setattr("collocation.with_sar.netCDF4.Dataset", smock)
        mp.setattr("collocation.with_sar.CatalogueServiceWeb", MockCSW)
        coll = Collocate(s1filename)
        tt = coll.get_nearest_collocation_by_time_coverage_start(csw_records)
        assert tt == csw_records["rec1"]
        tt = coll.get_nearest_collocation_by_time_coverage_end(csw_records)
        assert tt == csw_records["rec1"]


@pytest.mark.core
def testNorKyst800(s1filename, monkeypatch):
    """ Test NorKyst800.
    """
    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_sar.CatalogueServiceWeb", MockCSW)
        coll = NorKyst800(s1filename)
        records = coll.get_collocations()
        assert records["rec1"].references == refs

    url = coll.get_odap_url_of_nearest()
    assert url == ("https://thredds.met.no/thredds/dodsC/fou-hi/"
                   "norkyst800m-1h/NorKyst-800m_ZDEPTHS_his.an.2019010700.nc")


@pytest.mark.core
def testMeps(s1filename, csw_records, monkeypatch):
    """ Test Meps
    """
    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_sar.CatalogueServiceWeb", MockCSW)
        coll = Meps(s1filename)
        records = coll.get_collocations()
        assert records["rec1"].references == refs


@pytest.mark.core
def testAromeArctic(s1filename, monkeypatch):
    """ Test AromeArctic
    """
    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_sar.CatalogueServiceWeb", MockCSW)
        coll = AromeArctic(s1filename)
        records = coll.get_collocations()
        assert records["rec1"].references == refs


@pytest.mark.core
def testMETNordic(s1filename, monkeypatch):
    """ Test METNordic
    """
    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_sar.CatalogueServiceWeb", MockCSW)
        coll = METNordic(s1filename)
        records = coll.get_collocations()
        assert records["rec1"].references == refs

    coll = METNordic(s1filename)
    url = coll.get_odap_url_of_nearest()
    assert url == ("https://thredds.met.no/thredds/dodsC/metpparchivev3/"
                   "2019/01/07/met_analysis_1_0km_nordic_20190107T17Z.nc")


@pytest.mark.core
def testWeatherForecast(s1filename):
    with pytest.raises(NotImplementedError):
        WeatherForecast(s1filename)
