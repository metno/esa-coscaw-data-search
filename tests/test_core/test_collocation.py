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

from pytz import timezone
from unittest.mock import Mock
from dateutil.parser import parse

from collocation.with_dataset import Collocate
from collocation.with_dataset import METNordic
from collocation.with_dataset import NorKyst800
from collocation.with_dataset import AromeArctic
from collocation.with_dataset import Meps
from collocation.with_dataset import WeatherForecast


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


class MockNcDataset:

    # S1B_IW_RAW__0SDV_20190107T171737_20190107T171810_014391_01AC8B_78F4.zip
    time_coverage_start = "20190107T171737"
    time_coverage_end = "20190107T171810"

    def __init__(self, *args, **kwargs):
        return None


class MockNcDataset2:

    ACQUISITION_START_TIME = "20190107T171737"

    def __init__(self, *args, **kwargs):
        return None


class Fail:

    def __init__(self, *args, **kwargs):
        raise OSError


@pytest.mark.core
def testCollocate__execute(s1filename, monkeypatch):
    """ Test that the csw connection is called, and that the function
    returns a dict.
    """
    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_dataset.CatalogueServiceWeb", MockCSW)
        mp.setattr("collocation.with_dataset.netCDF4.Dataset", MockNcDataset)
        coll = Collocate(s1filename)
        records = coll._execute([])
        assert records["rec1"].references == refs


@pytest.mark.core
def testCollocate__set_dataset_date(s1filename, monkeypatch):
    """ Test setting the time
    """
    class SelectMock(Mock):
        pass

    tt = datetime.datetime(2019, 1, 7, 17, 17, 37, tzinfo=timezone("utc"))
    with monkeypatch.context() as mp:
        smock = SelectMock()
        smock.side_effect = [OSError, MockNcDataset()]
        mp.setattr("collocation.with_dataset.netCDF4.Dataset", smock)
        coll = Collocate(s1filename)
        assert coll.time == tt

    with monkeypatch.context() as mp:
        smock = SelectMock()
        smock.side_effect = [OSError, MockNcDataset2()]
        mp.setattr("collocation.with_dataset.netCDF4.Dataset", smock)
        coll = Collocate(s1filename)
        assert coll.time == tt


@pytest.mark.core
def testCollocate_get_odap_url_of_nearest(s1filename, csw_records, monkeypatch):
    """ Test that the nearest record in time_coverage_start has the
    correct opendap url.
    """
    class SelectMock(Mock):
        pass

    with monkeypatch.context() as mp:
        smock = SelectMock()
        smock.side_effect = [MockNcDataset(), MockDataset(), MockDataset2()]
        mp.setattr("collocation.with_dataset.netCDF4.Dataset", smock)
        mp.setattr("collocation.with_dataset.CatalogueServiceWeb", MockCSW)
        coll = Collocate(s1filename)
        tt = coll.get_odap_url_of_nearest()
        assert tt == ("https://thredds.met.no/thredds/dodsC/meps25epsarchive/2024/04/06/10/"
                      "meps_mbr007_sfc_20240406T10Z.ncml")


# This blocks ipdb and does not block opendap access, so it is omitted:
#   @pytest.mark.core
#   def test_odap_fails():
#       url = ("https://thredds.met.no/thredds/dodsC/meps25epsarchive/2024/04/06/10/"
#              "meps_mbr007_sfc_20240406T10Z.ncml")
#       with pytest.raises(Exception):
#           import requests
#           r = requests.get("https://google.com")
#           #ds = netCDF4.Dataset(url)
#           #tt = ds.time_coverage_start


@pytest.mark.core
def testCollocate_get_collocations(s1filename, monkeypatch):
    """ Test that get_collocations returns a dict of records.
    """
    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_dataset.CatalogueServiceWeb", MockCSW)
        mp.setattr("collocation.with_dataset.netCDF4.Dataset", MockNcDataset)
        coll = Collocate(s1filename)
        records = coll.get_collocations()
        assert records["rec1"].references == refs


@pytest.mark.core
def testCollocate_Init(s1filename, monkeypatch):
    """ Test initialization of Collocate.
    """
    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_dataset.netCDF4.Dataset", MockNcDataset)
        coll = Collocate(s1filename)
        tt = datetime.datetime(2019, 1, 7, 17, 17, 37, tzinfo=timezone("utc"))

        assert coll.url == s1filename
        assert coll.time == tt
        assert coll.time.tzinfo == timezone("utc")

    # Test init with time input
    coll = Collocate(s1filename, tt)
    assert coll.time == tt
    coll = METNordic(s1filename, tt)
    assert coll.time == tt
    coll = NorKyst800(s1filename, tt)
    assert coll.time == tt
    coll = AromeArctic(s1filename, tt)
    assert coll.time == tt
    coll = Meps(s1filename, tt)
    assert coll.time == tt


@pytest.mark.core
def testCollocate_assert_available(monkeypatch):
    """ Test that assert_available raises error if a dataset is not
    available.
    """
    url = "lkjlkj"
    with pytest.raises(ValueError) as ee:
        Collocate.assert_available(url)
    assert str(ee.value) == "The archive file %s is not available. Try another dataset." % url


@pytest.mark.core
def testCollocate_set_csw_connection(s1filename, monkeypatch):
    """ Test establishment of CSW connection but without actual
    connection to a CSW service.
    """
    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_dataset.CatalogueServiceWeb", MockCSW)
        mp.setattr("collocation.with_dataset.netCDF4.Dataset", MockNcDataset)
        coll = Collocate(s1filename)
        coll._set_csw_connection()
        assert coll.conn_csw.test == "test"


@pytest.mark.core
def testCollocate_search_functions(s1filename, monkeypatch):
    """ Test that search xml files can be created from the search
    objects returned by the search functions.

    Note: Ideally, we should mock the owslib but this has not been
    done here, partly because of laziness and partly to better
    understand owslib..
    """
    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_dataset.netCDF4.Dataset", MockNcDataset)
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
        mp.setattr("collocation.with_dataset.netCDF4.Dataset", MockDataset)
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
        smock.side_effect = [MockNcDataset(), MockDataset(), MockDataset2(), MockDataset(),
                             MockDataset2()]
        mp.setattr("collocation.with_dataset.netCDF4.Dataset", smock)
        mp.setattr("collocation.with_dataset.CatalogueServiceWeb", MockCSW)
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
        mp.setattr("collocation.with_dataset.CatalogueServiceWeb", MockCSW)
        mp.setattr("collocation.with_dataset.netCDF4.Dataset", MockNcDataset)
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
        mp.setattr("collocation.with_dataset.CatalogueServiceWeb", MockCSW)
        mp.setattr("collocation.with_dataset.netCDF4.Dataset", MockNcDataset)
        coll = Meps(s1filename)
        records = coll.get_collocations()
        assert records["rec1"].references == refs


@pytest.mark.core
def testAromeArctic(s1filename, monkeypatch):
    """ Test AromeArctic
    """
    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_dataset.CatalogueServiceWeb", MockCSW)
        mp.setattr("collocation.with_dataset.netCDF4.Dataset", MockNcDataset)
        coll = AromeArctic(s1filename)
        records = coll.get_collocations()
        assert records["rec1"].references == refs


@pytest.mark.core
def testMETNordic(s1filename, monkeypatch):
    """ Test METNordic
    """
    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_dataset.CatalogueServiceWeb", MockCSW)
        mp.setattr("collocation.with_dataset.netCDF4.Dataset", MockNcDataset)
        coll = METNordic(s1filename)
        records = coll.get_collocations()
        assert records["rec1"].references == refs

    with monkeypatch.context() as mp:
        mp.setattr("collocation.with_dataset.netCDF4.Dataset", MockNcDataset)
        coll = METNordic(s1filename)
        url = coll.get_odap_url_of_nearest()
        assert url == ("https://thredds.met.no/thredds/dodsC/metpparchivev3/"
                       "2019/01/07/met_analysis_1_0km_nordic_20190107T17Z.nc")


@pytest.mark.core
def testWeatherForecast(s1filename):
    with pytest.raises(NotImplementedError):
        WeatherForecast(s1filename)
