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
import logging
import datetime

from pytz import timezone
from unittest.mock import Mock
from dateutil.parser import parse

from fadg.find_and_collocate import SearchCSW
from fadg.find_and_collocate import Collocate
from fadg.find_and_collocate import METNordic
from fadg.find_and_collocate import NorKyst800
from fadg.find_and_collocate import AromeArctic
from fadg.find_and_collocate import Meps
from fadg.find_and_collocate import WeatherForecast


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


class MockRecord:

    def __init__(self, *args, **kwargs):
        return None


class MockCSW:

    test = "test"

    def __init__(self, *args, **kwargs):
        return None

    def getrecords2(self, *args, **kwargs):
        rec1 = MockRecord()
        rec1.references = refs
        rec2 = MockRecord()
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
    geospatial_lon_min = -3.
    geospatial_lon_max = 5.
    geospatial_lat_min = 58.
    geospatial_lat_max = 65.

    def __init__(self, *args, **kwargs):
        return None


class MockNcDataset2:

    ACQUISITION_START_TIME = "20190107T171737"
    geospatial_lon_min = -3.
    geospatial_lon_max = 5.
    geospatial_lat_min = 58.
    geospatial_lat_max = 65.

    def __init__(self, *args, **kwargs):
        return None


class MockDataset1:

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


class MockDataset3:

    def __init__(self, *args, **kwargs):
        self.time_coverage_start = "2019-01-06T10:00:00Z"
        self.time_coverage_end = "2019-01-06T10:02:00Z"

    def close(self):
        return None


class MockDataset4:

    def __init__(self, *args, **kwargs):
        self.time_coverage_start = "2019-01-07T10:00:00Z"
        self.time_coverage_end = "2019-01-07T10:02:00Z"

    def close(self):
        return None


class Fail:

    def __init__(self, *args, **kwargs):
        raise OSError


@pytest.mark.live
def testSearchCSW_Init():
    """Test data search for time, location and freetext.
    """
    point = [4.0, 59.0, 4.0, 59.9]
    ds = SearchCSW(time=datetime.datetime(2024, 4, 18, 13, 0, 0, tzinfo=timezone("utc")),
                   bbox=point)
    assert len(ds.records.keys()) > 0


@pytest.mark.core
def testSearchCSW_Init_offline(monkeypatch):
    """Offline test of SearchCSW init function.
    """
    polygon = [[-5.0, 47.0], [-5.0, 55.0], [20., 55.0], [20.0, 47.0], [-5.0, 47.0]]
    with pytest.raises(NotImplementedError) as ee:
        ds = SearchCSW(time=datetime.datetime(2024, 4, 18, 13, 0, 0, tzinfo=timezone("utc")),
                       bbox=polygon)
    assert str(ee.value) == "SearchCSW does not yet support more complex geographic search."

    mm = MockRecord()
    mm.references = refs
    bbox = [-2, 60, 3, 65]
    with monkeypatch.context() as mp:
        mp.setattr(SearchCSW, "_execute",
                   lambda *a, **k: {"no.met:d65b856f-4450-46db-a4aa-e532cf9dc33e": mm})
        # With time, text and bbox
        ds = SearchCSW(time=datetime.datetime(2024, 4, 18, 13, 0, 0, tzinfo=timezone("utc")),
                       text="Arome", bbox=bbox)
        assert len(ds.urls) == 1
        # Without inputs
        ds = SearchCSW()
        assert len(ds.urls) == 1


@pytest.mark.core
def testCollocate__execute(s1filename, monkeypatch):
    """ Test that the csw connection is called, and that the function
    returns a dict.
    """
    with monkeypatch.context() as mp:
        mp.setattr("fadg.find_and_collocate.CatalogueServiceWeb", MockCSW)
        mp.setattr("fadg.find_and_collocate.netCDF4.Dataset", MockNcDataset)
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
        mp.setattr("fadg.find_and_collocate.netCDF4.Dataset", smock)
        coll = Collocate(s1filename)
        assert coll.time == tt

    with monkeypatch.context() as mp:
        smock = SelectMock()
        smock.side_effect = [OSError, MockNcDataset2()]
        mp.setattr("fadg.find_and_collocate.netCDF4.Dataset", smock)
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
        smock.side_effect = [
            MockNcDataset(),  # Init Collocate
            MockDataset1(),    # assert_available
            MockDataset1(),    # get_time_coverage
            MockDataset2(),   # assert_available
            MockDataset2()    # get_time_coverage
        ]
        mp.setattr("fadg.find_and_collocate.netCDF4.Dataset", smock)
        mp.setattr("fadg.find_and_collocate.CatalogueServiceWeb", MockCSW)
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
        mp.setattr("fadg.find_and_collocate.CatalogueServiceWeb", MockCSW)
        mp.setattr("fadg.find_and_collocate.netCDF4.Dataset", MockNcDataset)
        coll = Collocate(s1filename)
        records = coll.get_collocations()
        assert records["rec1"].references == refs


@pytest.mark.core
def testCollocate_Init(s1filename, monkeypatch):
    """ Test initialization of Collocate.
    """
    with monkeypatch.context() as mp:
        mp.setattr("fadg.find_and_collocate.netCDF4.Dataset", MockNcDataset)
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
        mp.setattr("fadg.find_and_collocate.CatalogueServiceWeb", MockCSW)
        mp.setattr("fadg.find_and_collocate.netCDF4.Dataset", MockNcDataset)
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
        mp.setattr("fadg.find_and_collocate.netCDF4.Dataset", MockNcDataset)
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
    assert Collocate.get_odap_url(csw_record) == ("https://thredds.met.no/INVALID/thredds/dodsC/"
                                                  "meps25epsarchive/2024/04/06/10/"
                                                  "meps_mbr007_sfc_20240406T10Z.ncml")
    csw_record.references = []
    assert Collocate.get_odap_url(csw_record) is None


@pytest.mark.core
def testCollocate_get_time_coverage(csw_record, monkeypatch):
    """ Test that netCDF4.Dataset is called, and that correct times
    are returned.
    """
    with monkeypatch.context() as mp:
        mp.setattr("fadg.find_and_collocate.netCDF4.Dataset", MockDataset1)
        start, end = Collocate.get_time_coverage(csw_record)
        assert start == parse("2024-04-06T10:00:00Z")
        assert end == parse("2024-04-06T10:02:00Z")


@pytest.mark.core
def testCollocate_get_nearest_collocation_by_time(s1filename, csw_records, csw_4_records,
                                                  monkeypatch, caplog):
    """ Test that the nearest record in time_coverage_* is returned.
    """
    class SelectMock(Mock):
        pass

    caplog.set_level(logging.DEBUG)

    with monkeypatch.context() as mp:
        smock = SelectMock()
        smock.side_effect = [
            # Init Collocate
            MockNcDataset(),
            # Test get_nearest_collocation_by_time_coverage_start
            MockDataset1(),    # assert_available
            MockDataset1(),    # get_time_coverage
            MockDataset2(),   # assert_available
            MockDataset2(),   # get_time_coverage
            # Test get_nearest_collocation_by_time_coverage_end
            MockDataset1(),    # assert_available
            MockDataset1(),    # get_time_coverage
            MockDataset2(),   # assert_available
            MockDataset2(),   # get_time_coverage
            # Test failing _get_nearest_by_time(csw_records, 0, rel=1)
            MockDataset1(),    # assert_available
            MockDataset1(),    # get_time_coverage
            MockDataset2(),   # assert_available
            MockDataset2(),   # get_time_coverage
            # Test failing _get_nearest_by_time(csw_records, 0, rel=2)
            MockDataset3(),    # assert_available
            MockDataset3(),    # get_time_coverage
            MockDataset4(),   # assert_available
            MockDataset4(),   # get_time_coverage
            # Test _get_nearest_by_time(csw_4_records, 0, rel=1)
            MockDataset1(),    # assert_available
            MockDataset1(),    # get_time_coverage
            MockDataset2(),   # assert_available
            MockDataset2(),   # get_time_coverage
            MockDataset3(),    # assert_available
            MockDataset3(),    # get_time_coverage
            MockDataset4(),   # assert_available
            MockDataset4(),   # get_time_coverage
            # Test _get_nearest_by_time(csw_4_records, 0, rel=2)
            MockDataset1(),    # assert_available
            MockDataset1(),    # get_time_coverage
            MockDataset2(),   # assert_available
            MockDataset2(),   # get_time_coverage
            MockDataset3(),    # assert_available
            MockDataset3(),    # get_time_coverage
            MockDataset4(),   # assert_available
            MockDataset4(),   # get_time_coverage
            # Test coll._get_nearest_by_time(csw_records, 0, rel=4)
            MockDataset1(),    # assert_available
            MockDataset1(),    # get_time_coverage
            MockDataset2(),   # assert_available
            MockDataset2(),   # get_time_coverage
            # Init Collocate for testing _get_nearest_by_time
            MockNcDataset(),
        ]
        mp.setattr("fadg.find_and_collocate.netCDF4.Dataset", smock)
        mp.setattr("fadg.find_and_collocate.CatalogueServiceWeb", MockCSW)
        # Init Collocate
        coll = Collocate(s1filename)
        # assert_available and get_time_coverage
        tt = coll.get_nearest_collocation_by_time_coverage_start(csw_records)
        assert tt == csw_records["rec1"]
        # assert_available and get_time_coverage
        tt = coll.get_nearest_collocation_by_time_coverage_end(csw_records)
        assert tt == csw_records["rec1"]
        with pytest.raises(ValueError) as ee:
            # assert_available and get_time_coverage
            tt = coll.get_nearest_collocation_by_time_coverage_end({})
        assert str(ee.value) == "Input records dict is empty."

        with pytest.raises(ValueError) as ee:
            rec = coll._get_nearest_by_time(csw_records, 0, rel=1)
        assert "No available datasets before" in str(ee.value)
        with pytest.raises(ValueError) as ee:
            rec = coll._get_nearest_by_time(csw_records, 0, rel=2)
        assert "No available datasets after" in str(ee.value)
        rec = coll._get_nearest_by_time(csw_4_records, 0, rel=1)
        assert rec.time_coverage_start == "2019-01-07T10:00:00Z"
        rec = coll._get_nearest_by_time(csw_4_records, 0, rel=2)
        assert rec.time_coverage_start == "2024-04-06T10:00:00Z"

        with pytest.raises(ValueError) as ee:
            coll._get_nearest_by_time(csw_records, 0, rel=4)
        assert "rel must be 0, 1 or 2" == str(ee.value)

        def raiseVErr():
            raise ValueError("TEST")

        # Test _get_nearest_by_time fails when urls (in csw_records)
        # are invalid
        # Init Collocate
        coll = Collocate(s1filename)
        mp.setattr("fadg.find_and_collocate.Collocate.assert_available",
                   lambda *a, **k: raiseVErr())
        with pytest.raises(ValueError) as ee:
            recs = coll._get_nearest_by_time(csw_records, 0)
            assert recs == []
        assert "No available datasets" in str(ee.value)
        assert "TEST" in caplog.text


@pytest.mark.core
def testNorKyst800(s1filename, monkeypatch):
    """ Test NorKyst800.
    """
    with monkeypatch.context() as mp:
        mp.setattr("fadg.find_and_collocate.CatalogueServiceWeb", MockCSW)
        mp.setattr("fadg.find_and_collocate.netCDF4.Dataset", MockNcDataset)
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
        mp.setattr("fadg.find_and_collocate.CatalogueServiceWeb", MockCSW)
        mp.setattr("fadg.find_and_collocate.netCDF4.Dataset", MockNcDataset)
        coll = Meps(s1filename)
        records = coll.get_collocations()
        assert records["rec1"].references == refs


@pytest.mark.core
def testAromeArctic(s1filename, monkeypatch):
    """ Test AromeArctic
    """
    with monkeypatch.context() as mp:
        mp.setattr("fadg.find_and_collocate.CatalogueServiceWeb", MockCSW)
        mp.setattr("fadg.find_and_collocate.netCDF4.Dataset", MockNcDataset)
        coll = AromeArctic(s1filename)
        records = coll.get_collocations()
        assert records["rec1"].references == refs


@pytest.mark.core
def testMETNordic(s1filename, monkeypatch):
    """ Test METNordic
    """
    with monkeypatch.context() as mp:
        mp.setattr("fadg.find_and_collocate.CatalogueServiceWeb", MockCSW)
        mp.setattr("fadg.find_and_collocate.netCDF4.Dataset", MockNcDataset)
        coll = METNordic(s1filename)
        records = coll.get_collocations()
        assert records["rec1"].references == refs

    with monkeypatch.context() as mp:
        mp.setattr("fadg.find_and_collocate.netCDF4.Dataset", MockNcDataset)
        coll = METNordic(s1filename)
        url = coll.get_odap_url_of_nearest()
        assert url == ("https://thredds.met.no/thredds/dodsC/metpparchivev3/"
                       "2019/01/07/met_analysis_1_0km_nordic_20190107T17Z.nc")


@pytest.mark.core
def testWeatherForecast(s1filename):
    with pytest.raises(NotImplementedError):
        WeatherForecast(s1filename)
