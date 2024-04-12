"""
Collocation : with_sar.py
=========================

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
import datetime

import numpy as np

from dateutil import tz
from dateutil.parser import parse

from owslib import fes
from owslib.csw import CatalogueServiceWeb


class Collocate:
    """ Given a SAR dataset, find the closest dataset in time and
    space of the given type.

    Input
    =====
    sar_url : string
        OPeNDAP url to the file, or optionally the path to a local
        file.
    """

    def __init__(self, sar_url):

        self.sar_url = sar_url

        self.time = None
        self.polygon = None
        self.conn_csw = None

        self._set_sar_date()

        # Read location of SAR dataset

        # Set intersecting polygon

    def _set_sar_date(self):
        """ Set the central time of collocation, i.e., the time of
        the SAR dataset.
        """
        fname = os.path.basename(self.sar_url)
        # Read time of SAR dataset
        date_string = fname.split("_")[5]

        # Set central time of collocation
        time = parse(date_string)
        self.time = time.replace(tzinfo=time.tzinfo or tz.gettz("UTC"))

    def get_collocations(self, constraints=None, dt=24, endpoint="https://data.csw.met.no"):
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

        # Search and return dict
        return self._execute([fes.And(constraints)], pagesize=10, max_records=100,
                             endpoint=endpoint)

    @staticmethod
    def get_odap_url(record):
        """ Return OPeNDAP url of given record.
        """
        for scheme in record.references:
            if "opendap" in scheme["scheme"].lower():
                url = scheme["url"]
                break
        return url

    @staticmethod
    def get_time_coverage(record):
        """ Return time_coverage_start and time_coverage_end of the
        given record converted to datetime.datetime objects.

        Note: the record does not contain proper times (except the
        date), so we need to read it from OPeNDAP - or don't we?
        """
        odap = Collocate.get_odap_url(record)
        ds = netCDF4.Dataset(odap)
        start = parse(ds.time_coverage_start)
        end = parse(ds.time_coverage_end)
        ds.close()

        return start, end

    def _get_nearest_by_time(self, records, index):
        """ Returns the record that is closest to self.time by given
        index. The index indicates either time_coverage_start (0) or
        time_coverage_end (1).
        """
        times = np.array([])
        keys = []
        for key, record in records.items():
            tt = Collocate.get_time_coverage(record)
            times = np.append(times, tt[index])
            keys.append(key)

        return records[keys[np.abs(times-self.time).argmin()]]

    def get_nearest_collocation_by_time_coverage_start(self, records):
        """ Returns the record that has time_coverage_start closest to
        self.time.
        """
        return self._get_nearest_by_time(records, 0)

    def get_nearest_collocation_by_time_coverage_end(self, records):
        """ Returns the record that has time_coverage_end closest to
        self.time.
        """
        return self._get_nearest_by_time(records, 1)

    def _execute(self, filter_list, pagesize=10, max_records=100,
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
                esn='full')
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
        each record, not the actual time_coverage_start or
        time_coverage_end. This appear to be a bug in pycsw. The "end"
        search seems to correctly represent time_coverage_end. Also,
        it seems that the "OrEqual" requirement doesn't come into
        effect. We need to search +/- 1 day in order to get anything.
        The time delta can be increased through the keyword dt but
        should not be less than 24 hours.

        TODO: check and fix issues with temporal search!

        Input
        =====
        dt : int
            Search interval in hours (+/-)
        """
        start = (self.time - datetime.timedelta(hours=dt)).strftime("%Y-%m-%d %H:%M:%S")
        stop = (self.time + datetime.timedelta(hours=dt)).strftime("%Y-%m-%d %H:%M:%S")

        propertyname = "apiso:TempExtent_begin" # same as record date?
        begin = fes.PropertyIsLessThanOrEqualTo(propertyname=propertyname, literal=stop)
        #begin = fes.PropertyIsGreaterThanOrEqualTo(propertyname=propertyname, literal=time)
        #propertyname = "apiso:TempExtent_end" # same as time_coverage_end?
        propertyname = "apiso:TempExtent_begin" # search record date only
        end = fes.PropertyIsGreaterThanOrEqualTo(propertyname=propertyname, literal=start)
        #end = fes.PropertyIsLessThanOrEqualTo(propertyname=propertyname, literal=time)

        return begin, end

    def _get_title_search(self, text):
        """ Return CSW search object for title search.
        """
        property_name = "dc:title"
        return self._get_prop_search(text, property_name)

    def _get_free_text_search(self, text):
        """ Return CSW search object based on any match with the input
        string.
        """
        property_name = "csw:AnyText"
        return self._get_prop_search(text, property_name)

    def _get_prop_search(self, text, property_name):
        """ Return CSW search object for given property and text.
        """
        return fes.PropertyIsLike(property_name, literal=text, escapeChar='\\', singleChar='_',
                                  wildCard='%', matchCase=True)

    def _set_csw_connection(self, endpoint="https://data.csw.met.no"):
        """ Sets connection to OGC CSW service.
        """
        self.conn_csw = CatalogueServiceWeb(endpoint, timeout=60)


class AromeArctic(Collocate):
    """ Class for collocating Arome-Arctic weather forecasts with
    Sentinel-1 SAR datasets.
    """

    def __init__(self, sar_url):
        super().__init__(sar_url)

    def get_collocations(self, subset="deterministic", *args, **kwargs):
        """ Returns Arome-Arctic records collocated with the dataset
        given by sar_url.
        """
        subsets = {
            "deterministic": "Arome-Arctic 2.5Km deterministic",
            "lagged subset": "Arome-Arctic 2.5Km lagged subset",
            "lagged vc": "Arome-Arctic 2.5Km lagged vc",
            "lagged tracking": "Arome-Arctic 2.5Km lagged tracking",
        }
        constraints = []
        #constraints.append(self._get_title_search("Arome-Arctic")) # this does not work
        constraints.append(self._get_free_text_search(subsets[subset]))
        #constraints.append(self._get_title_search(subset))
        return super().get_collocations(constraints, *args, **kwargs)


def _get_sar_date(sar_filename):
    """TODO: Add docstring
    """
    fname = os.path.basename(sar_filename)
    date_string = fname.split("_")[5]

    sar_date = parse(date_string)

    return sar_date


def get_odap(sar_filename):
    """A function for getting ocean (NorKyst800) and atmospheric
    (met_nordic) model data matching the date of the input Sentinel-1
    data. The date is extracted from the Sentinel-1 filename. The
    filename is expected to be on the form
    "S1B_IW_RAW__0SDV_20190107T171737_20190107T171810_014391_01AC8B_78F4.zip",
    where element 20190107T171737 will be used as search date.

    Parameters
    -----------
    sar_filename : string
        The SAR image as a filename

    Returns:
    ---------
    norkyst_url : string
        The OPeNDAP url to Norkyst800 data

    met_nordic_url : string
        The OPeNDAP url to MET Nordic data

    Example:
        norkyst_url, met_nordic_url =
            get_odap("S1B_IW_RAW__0SDV_20190107T171737_20190107T171810_014391_01AC8B_78F4.zip")
    """

    # Get sar datetime from filename
    sar_date = _get_sar_date(sar_filename)

    # Get url for ocean model
    norkyst_url = _get_norkyst_url(sar_date)

    # Get url for NWP model
    met_nordic_url = _get_met_nordic_url(sar_date)

    return norkyst_url, met_nordic_url


def _get_norkyst_url(sar_date):
    """ Returns the OPeNDAP url to a Norkyst800 dataset.

    The function currently uses a hardcoded url pattern but this
    should be replaced by a CSW search once the data is available
    through https://data.met.no
    """
    # Construct url
    url_path = "https://thredds.met.no/thredds/dodsC/fou-hi/norkyst800m-1h"
    url_file = "NorKyst-800m_ZDEPTHS_his.an.%04d%02d%02d00.nc" % (sar_date.year, sar_date.month,
                                                                  sar_date.day)
    norkyst_url = os.path.join(url_path, url_file)

    return norkyst_url


def _get_met_nordic_url(sar_date):
    """TODO: Add docstring
    """
    url_path = "https://thredds.met.no/thredds/dodsC/metpparchivev3"
    url_file = "met_analysis_1_0km_nordic"
    datetimeStr = "%04d%02d%02dT%02d" % (sar_date.year, sar_date.month, sar_date.day,
                                         sar_date.hour)
    met_nordic_url = "%s/%04d/%02d/%02d/%s_%sZ.nc" % (url_path, sar_date.year, sar_date.month,
                                                      sar_date.day, url_file, datetimeStr)

    return met_nordic_url
