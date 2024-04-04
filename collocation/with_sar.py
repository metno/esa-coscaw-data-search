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

from dateutil.parser import parse


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
    url_path = "https://thredds.met.no/thredds/fileServer/fou-hi/norkyst800m-1h"
    url_file = "NorKyst-800m_ZDEPTHS_his.an.%04d%02d%02d00.nc" % (sar_date.year, sar_date.month,
                                                                  sar_date.day)
    norkyst_url = os.path.join(url_path, url_file)

    return norkyst_url


def _get_met_nordic_url(sar_date):
    """TODO: Add docstring
    """
    url_path = "https://thredds.met.no/thredds/fileServer/metpparchivev3"
    url_file = "met_analysis_1_0km_nordic"
    datetimeStr = "%04d%02d%02dT%02d" % (sar_date.year, sar_date.month, sar_date.day,
                                         sar_date.hour)
    met_nordic_url = "%s/%04d/%02d/%02d/%s_%sZ.nc" % (url_path, sar_date.year, sar_date.month,
                                                      sar_date.day, url_file, datetimeStr)

    return met_nordic_url


def _get_sar_date(sar_filename):
    """TODO: Add docstring
    """
    fname = os.path.basename(sar_filename)
    date_string = fname.split("_")[5]

    sar_date = parse(date_string)

    return sar_date
