"""
fadg : find_and_collocate.py
======================

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
import netCDF4
import logging
import datetime

import numpy as np

from pytz import timezone
from dateutil.parser import parse

from owslib import fes
from owslib.csw import CatalogueServiceWeb


class SearchCSW:
    """Find data in a given time interval and location.

    Note: owslib only handles bounding box search by maximum and
    minimum longitude and latitude. This is very limited and
    impractical for searches near the poles, so we should avoid owslib
    and rather use jinja to fill out a template xml.

    TODO: implement search for polygon intersection using an xml
    template and jinja.

    Input
    =====
    time : datetime.datetime (default now)
        If the file cannot be opened with netCDF4, provide the time
    dt : float (default 24)
        Time interval in hours before and after the given time
    bbox : float list (default [-180, -90, 180, 90])
       A bounding box for the search area specified by latitude and
       longitude, i.e., bbox = [lon_min, lat_min, lon_max, lat_max]
    """
    def __init__(self, time=None, dt=24, bbox=None, text=None,
                 crs="urn:ogc:def:crs:OGC:1.3:CRS84", *args, **kwargs):

        self.time = time
        if self.time is None:
            self.time = datetime.datetime.now(timezone("utc"))

        self.bbox = bbox
        if self.bbox is None:
            self.bbox = [-180, -90, 180, 90]
        if len(np.array(self.bbox).shape) != 1:
            raise NotImplementedError("SearchCSW does not yet support more complex "
                                      "geographic search.")

        constraints = []

        # Create temporal search objects
        temporal_search_start, temporal_search_end = self._temporal_filter(dt=dt)

        # Add temporal search objects to the list of constraints
        constraints.append(temporal_search_start)
        constraints.append(temporal_search_end)

        bbox_search = fes.BBox(self.bbox, crs=crs)
        constraints.append(bbox_search)

        if text is not None:
            constraints.append(self._get_free_text_search(text))

        self.records = self._execute([fes.And(constraints)], *args, **kwargs)

        self.urls = []

        for key, record in self.records.items():
            self.urls.append(SearchCSW.get_odap_url(record))

    @staticmethod
    def get_odap_url(record):
        """ Return OPeNDAP url of given CSW record.
        """
        if len(record.references) == 0:
            return None

        for scheme in record.references:
            if "opendap" in scheme["scheme"].lower():
                url = scheme["url"]
                break
        return url

    def _get_free_text_search(self, text):
        """ Return CSW search object based on any match with the input
        string.
        """
        property_name = "csw:AnyText"
        return self._get_prop_search(text, property_name)

    def _get_title_search(self, text):
        """ Return CSW search object for title search.
        """
        property_name = "dc:title"
        return self._get_prop_search(text, property_name)

    def _get_prop_search(self, text, property_name):
        """ Return CSW search object for given property and text.
        """
        return fes.PropertyIsLike(property_name, literal=text, escapeChar="\\", singleChar="_",
                                  wildCard="%", matchCase=True)

    def _set_csw_connection(self, endpoint="https://data.csw.met.no"):
        """ Sets connection to OGC CSW service.
        """
        self.conn_csw = CatalogueServiceWeb(endpoint, timeout=60)

    def _execute(self, filter_list, pagesize=10, max_records=1000,
                 endpoint="https://data.csw.met.no"):
        """ Execute CSW search using the provided filter list, and
        return a dictionary of all the resulting records. Limit the
        number of retrieved records using the keyword max_records.
        """
        csw_records = {}
        start_position = 0

        # Connect to the CSW service
        self._set_csw_connection(endpoint=endpoint)

        next_record = 1
        while next_record != 0:
            # Iterate pages until the requested max_records is reached
            self.conn_csw.getrecords2(
                constraints=filter_list,
                startposition=start_position,
                maxrecords=pagesize,
                outputschema="http://www.opengis.net/cat/csw/2.0.2",
                esn="full")
            csw_records.update(self.conn_csw.records)
            next_record = self.conn_csw.results["nextrecord"]
            start_position += pagesize + 1  # Last one is included.
            if start_position >= max_records:
                next_record = 0

        return csw_records

    def _temporal_filter(self, dt=24):
        """ Take datetime-like objects and return a fes filter for
        date range.

        NOTE: the "begin" search seems to be performed on the date of
        each record (the dataset publication_date), not the actual
        time_coverage_start or time_coverage_end. This appear to be a
        bug in pycsw. The "end" search seems to correctly represent
        time_coverage_end. Also, it seems that the "OrEqual"
        requirement doesn not come into effect. We need to search +/-
        1 day in order to get anything. The time delta can be
        increased through the keyword dt but should not be less than
        24 hours.

        TODO: check and fix issues with temporal search!

        Input
        =====
        dt : int
            Search interval in hours (+/-)
        """
        start = (self.time - datetime.timedelta(hours=dt)).strftime("%Y-%m-%d %H:%M:%S")
        stop = (self.time + datetime.timedelta(hours=dt)).strftime("%Y-%m-%d %H:%M:%S")

        propertyname = "apiso:TempExtent_begin"  # same as record date?
        begin = fes.PropertyIsLessThanOrEqualTo(propertyname=propertyname, literal=stop)
        # begin = fes.PropertyIsGreaterThanOrEqualTo(propertyname=propertyname, literal=time)
        # propertyname = "apiso:TempExtent_end"  # same as time_coverage_end?
        propertyname = "apiso:TempExtent_begin"  # search record date only
        end = fes.PropertyIsGreaterThanOrEqualTo(propertyname=propertyname, literal=start)
        # end = fes.PropertyIsLessThanOrEqualTo(propertyname=propertyname, literal=time)

        return begin, end


class Collocate(SearchCSW):
    """Given a dataset filename or OPeNDAP url, find the closest
    dataset in time and space of the given type. The dataset must be
    netCDF4 type, and contain ACDD metadata time_coverage_start.

    Input
    =====
    url : string
        Dataset OPeNDAP url or filename.
    """

    def __init__(self, url, time=None, bbox=None):

        self.url = url

        self.time = None
        self.polygon = None
        self.conn_csw = None

        try:
            ds = netCDF4.Dataset(self.url)
        except OSError:
            ds = netCDF4.Dataset(self.url + "#fillmismatch")
        # Read time of dataset
        try:
            date_string = ds.time_coverage_start
        except AttributeError:
            # Special exception for Sentinel 1 data..
            date_string = ds.ACQUISITION_START_TIME

        # Set central time of collocation
        time = parse(date_string)
        self.time = time.replace(tzinfo=time.tzinfo or timezone("utc"))

        # Set bounding box
        self.bbox = [float(ds.geospatial_lon_min), float(ds.geospatial_lat_min),
                     float(ds.geospatial_lon_max), float(ds.geospatial_lat_max)]

    def get_collocations(self, constraints=None, dt=24, endpoint="https://data.csw.met.no",
                         crs="urn:ogc:def:crs:OGC:1.3:CRS84"):
        """ Uses SAR time, plus other provided constraints (optional)
        to find collocated dataset(s).

        Note: owslib seems to be limited to bbox search based on
        squares in lat/lon... Spatial search should be based on border
        polygon, and is therefore omitted but should be added.

        TODO: ADD SPATIAL SEARCH

        Input
        =====
        constraints : list
            List of CSW search objects defining other constraints.
        dt : int
            Search interval in hours (+/-)
        """
        if constraints is None:
            constraints = []

        # Create temporal search objects
        temporal_search_start, temporal_search_end = self._temporal_filter(dt=dt)

        # Add temporal search objects to the list of constraints
        constraints.append(temporal_search_start)
        constraints.append(temporal_search_end)

        # Location search
        bbox_search = fes.BBox(self.bbox, crs=crs)
        constraints.append(bbox_search)

        # Search and return dict
        return self._execute([fes.And(constraints)], endpoint=endpoint)

    @staticmethod
    def get_time_coverage(odap):
        """ Return time_coverage_start and time_coverage_end of the
        given record converted to datetime.datetime objects.

        Note: the record does not contain proper times (except the
        date), so we need to read it from OPeNDAP - or don't we?
        """
        ds = netCDF4.Dataset(odap)
        start = parse(ds.time_coverage_start)
        end = parse(ds.time_coverage_end)
        ds.close()

        return start, end

    @staticmethod
    def assert_available(url):
        """ Assert that the dataset is available.
        """
        try:
            netCDF4.Dataset(url)
        except OSError:
            raise ValueError("The archive file %s is not available. Try another dataset." % url)
        return None

    def _get_nearest_by_time(self, records, index, rel=0):
        """ Returns the record that is closest to self.time by given
        index. The index indicates either time_coverage_start (0) or
        time_coverage_end (1).

        Input
        =====
        records : list
            of owslib.catalogue.csw2.CswRecord
        index : int (0 or 1)
            0 for searching by time_coverage_start and 1 for searching
            by time_coverage_end
        rel : int (0, 1, or 2)
            Indicates the relative position in time between the two
            datasets. If rel=0, the search will cover both before and
            after Collocate.time. If rel=1, the search will cover
            times before Collocate.time. If rel=2, the search will
            cover times after Collocate.time.
        """
        times = np.array([])
        keys = []
        if not bool(records):
            raise ValueError("Input records dict is empty.")
        for key, record in records.items():
            odap = Collocate.get_odap_url(record)
            try:
                self.assert_available(odap)
            except ValueError as ee:
                logging.debug(ee)
            else:
                tt = Collocate.get_time_coverage(odap)
                times = np.append(times, tt[index])
                keys.append(key)

        if len(keys) == 0:
            raise ValueError("No available datasets for the given search interval.")

        index = None
        delta = times - self.time
        if rel == 0:
            index = np.abs(delta).argmin()
        if rel == 1:
            if not (delta < datetime.timedelta(0)).any():
                raise ValueError("No available datasets before %s." % self.time.isoformat())
            dm = delta
            dm[dm > datetime.timedelta(0)] = delta.min()
            index = dm.argmax()
        if rel == 2:
            if not (delta > datetime.timedelta(0)).any():
                raise ValueError("No available datasets after %s." % self.time.isoformat())
            dm = delta
            dm[dm < datetime.timedelta(0)] = delta.max()
            index = dm.argmin()
        if rel not in [0, 1, 2]:
            raise ValueError("rel must be 0, 1 or 2")

        return records[keys[index]]

    def get_nearest_collocation_by_time_coverage_start(self, records, **kwargs):
        """ Returns the record that has time_coverage_start closest to
        self.time.
        """
        return self._get_nearest_by_time(records, 0, **kwargs)

    def get_nearest_collocation_by_time_coverage_end(self, records, **kwargs):
        """ Returns the record that has time_coverage_end closest to
        self.time.
        """
        return self._get_nearest_by_time(records, 1, **kwargs)

    def get_odap_url_of_nearest(self, *args, **kwargs):
        """ Returns the OPeNDAP url of the nearest collocated
        dataset.
        """
        url = None
        rel = kwargs.pop("rel", 0)
        records = self.get_collocations(*args, **kwargs)
        if bool(records):
            nearest = self.get_nearest_collocation_by_time_coverage_start(records, rel=rel)
            url = Collocate.get_odap_url(nearest)
        return url


class AromeArctic(Collocate):
    """ Class for collocating Arome-Arctic weather forecasts with
    another dataset.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_collocations(self, subset="deterministic", *args, **kwargs):
        """ Returns Arome-Arctic records collocated with the dataset
        given by url.
        """
        subsets = {
            "deterministic": "Arome-Arctic 2.5Km deterministic",
            "lagged subset": "Arome-Arctic 2.5Km lagged subset",
            "lagged vc": "Arome-Arctic 2.5Km lagged vc",
            "lagged tracking": "Arome-Arctic 2.5Km lagged tracking",
        }
        constraints = []
        # constraints.append(self._get_title_search("Arome-Arctic")) # this does not work
        constraints.append(self._get_free_text_search(subsets[subset]))
        return super().get_collocations(constraints, *args, **kwargs)


class Meps(Collocate):
    """ Class for collocating Meps weather forecasts with another
    dataset.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_collocations(self, subset="surface", *args, **kwargs):
        """ Returns weather forecast records collocated with the dataset
        given by url. The title search is limited to control
        members only.
        """
        subsets = {
            "model level": "Meps 2.5 km deterministic model level parameters",
            "pressure level": "Meps 2.5 km deterministic pressure level parameters",
            "surface": "Meps 2.5 km deterministic surface parameters",
            "height level": "Meps 2.5 km deterministic height level parameters",
        }
        constraints = []
        # constraints.append(self._get_title_search(subsets[subset])) # this does not work
        constraints.append(self._get_free_text_search(subsets[subset]))
        return super().get_collocations(constraints, *args, **kwargs)


class METNordic(Collocate):
    """ Class for collocating MET Nordic weather analyses and
    forecasts with another dataset.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_collocations(self, *args, **kwargs):
        return super().get_collocations(*args, **kwargs)

    def get_odap_url_of_nearest(self):
        """ Returns the OPeNDAP url to a MET Nordic dataset.

        The function currently uses a hardcoded url pattern but this
        should be replaced by a CSW search using get_collocations
        function once the data is available through
        https://data.met.no.
        """
        url_path = "https://thredds.met.no/thredds/dodsC/metpparchivev3"
        url_file = "met_analysis_1_0km_nordic"
        datetimeStr = "%04d%02d%02dT%02d" % (self.time.year, self.time.month, self.time.day,
                                             self.time.hour)
        url = "%s/%04d/%02d/%02d/%s_%sZ.nc" % (url_path, self.time.year, self.time.month,
                                               self.time.day, url_file, datetimeStr)
        self.assert_available(url)

        return url


class WeatherForecast(Collocate):
    """ Class for collocating weather forecasts with another dataset.

    TODO: we need to add a proper geographical search based on polygon
    for this to work. In addition, the polygons must be added to the
    metadata files at data.met.no
    """

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "We need to add a proper geographical search based on "
            "polygons for this to work. In addition, the polygons "
            "must be added to the metadata files at data.met.no.")
        # super().__init__(ds_url)


class NorKyst800(Collocate):
    """ Class for collocating NorKyst800 ocean forecasts with another
    dataset.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_collocations(self, *args, **kwargs):
        return super().get_collocations(*args, **kwargs)

    def get_odap_url_of_nearest(self):
        """ Returns the OPeNDAP url to a Norkyst800 dataset.

        The function currently uses a hardcoded url pattern but this
        should be replaced by a CSW search using get_collocations
        function once the data is available through
        https://data.met.no.
        """
        # Construct url
        url_path = "https://thredds.met.no/thredds/dodsC/fou-hi/norkyst800m-1h"
        url_file = "NorKyst-800m_ZDEPTHS_his.an.%04d%02d%02d00.nc" % (self.time.year,
                                                                      self.time.month,
                                                                      self.time.day)
        url = os.path.join(url_path, url_file)
        self.assert_available(url)

        return url
