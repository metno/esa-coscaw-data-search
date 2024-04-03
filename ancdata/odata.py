#!/usr/bin/env python3
import os, sys
import subprocess
from datetime import datetime
from dateutil.parser import parse
import xml.etree.ElementTree as ET

NoData = -1

config_file = '../ancdata/config.xml'

def get_odap(sar_filename):
    """
    A function for getting ocean (NorKyst800) and atmospheric (met_nordic) model data matching the 
    date of the input Sentinel-1 data. The date is extracted from the Sentinel-1 filename.
    Filename is expected to be on the form S1B_IW_RAW__0SDV_20190107T171737_20190107T171810_014391_01AC8B_78F4.zip
    where element 20190107T171737 will be used as seach date.

    Parameters
    -----------
    sar_filename : string
                 The SAR image as a filename
    
    Returns:
    ---------
    string: norkyst_url, met_nordic_url
    
    Example:
        norkyst_url, met_nordic_url = 
            get_odap('S1B_IW_RAW__0SDV_20190107T171737_20190107T171810_014391_01AC8B_78F4.zip')
    
    """

    # Get sar datetime from filename
    sar_date = _get_sar_date(sar_filename)
    print(sar_date)
    
    # Get url elements from config.xml
    config = _read_config(config_file)
    
    # Get url for ocean model
    norkyst_url = _get_norkyst_url(sar_date, config)
    # Get data from url
    # norkyst_data = _get_norkyst_data(norkyst_url, config)    
    
    # Get url for NWP model
    met_nordic_url = _get_met_nordic(sar_date, config)
    # Get data from url
    # met_nordic_data = _get_met_nordict_data(met_nordic_url, config)
    
    return norkyst_url, met_nordic_url


#Example for manual download of Sentinel-1
#wget --no-check-certificate --user=nicob --password=L9N2qiwf --output-document=/lustre/storeC-ext/users/coscaw/sentinel-1/S1B_IW_RAW__0SDV_20190107T171737_20190107T171810_014391_01AC8B_78F4.zip "https://colhub-archive.met.no/odata/v1/Products('065997f8-7ca6-46f3-8052-be523d3e1ab4')/\$value"

#example for manual download met-nordic
#wget --no-check-certificate --output-document=/lustre/storeC-ext/users/coscaw/met-nordic/met_analysis_1_0km_nordic_20190107T17Z.nc https://thredds.met.no/thredds/fileServer/metpparchivev3/2019/01/07/met_analysis_1_0km_nordic_20190107T17Z.nc


#Example for manual download Nordkyst-800m
#wget --no-check-certificate --output-document=/lustre/storeC-ext/users/coscaw/met-nordic/NorKyst-800m_ZDEPTHS_his.an.2019012700.nc https://thredds.met.no/thredds/fileServer/fou-hi/norkyst800m-1h/NorKyst-800m_ZDEPTHS_his.an.2019012700.nc

def _read_config(file_path):
    # Parse the XML file
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Dictionary to store the settings
    settings = {}

    # Iterate over the 'setting' elements
    for setting in root.findall('setting'):
        name = setting.get('name')
        value = setting.text
        settings[name] = value
    return settings


def _get_norkyst_data(norkyst_url, config):
    norkyst_output = '%s/%s' % (config['norkyst_output'], os.path.basename(norkyst_url))
    cmd = 'wget --no-check-certificate --output-document=%s %s' % (norkyst_output, norkyst_url)
    try:
        subprocess.call(cmd, shell=True)
    except ValueError:
           raise ValueError("Not able to download norkyst data from %s" % norkyst_url)
        
    if os.path.isfile(norkyst_output) == False:
        print('Error: Not able to download file: %s' % (norkyst_output))
        sys.exit(-1)
    return norkyst_output
    
def _get_met_nordict_data(met_nordic_url, config):
    met_nordic_output = '%s/%s' % (config['met_nordic_output'], os.path.basename(met_nordic_url))
    cmd = 'wget --no-check-certificate --output-document=%s %s' % (met_nordic_output, met_nordic_url)
    try:
        subprocess.call(cmd, shell=True)
    except ValueError:
           raise ValueError("Not able to download norkyst data from %s" % met_nordic_url)
        
    if os.path.isfile(met_nordic_output) == False:
        print('Error: Not able to download file: %s' % (met_nordic_output))
        sys.exit(-1)
    return met_nordic_output
    
def _get_norkyst_url(sar_date, config):
    # Construct url
    url_path = config['norkyst_path']
    url_file = '%s.%04d%02d%02d00.nc' % (config['norkyst_prefile'], sar_date.year,sar_date.month,sar_date.day)    
    norkyst_url = '%s/%s' % (url_path, url_file)
    
    return norkyst_url

def _get_met_nordic(sar_date, config):
    url_path = config['met_nordic_path']
    url_file = config['met_nordic_prefile']
    datetimeStr = '%04d%02d%02dT%02d' % (sar_date.year,sar_date.month,sar_date.day,sar_date.hour)
    met_nordic_url = '%s/%04d/%02d/%02d/%s_%sZ.nc' % (url_path,sar_date.year,sar_date.month,sar_date.day,url_file,datetimeStr)
    
    return met_nordic_url
    
def _get_sar_date(sar_filename):    
    fname = os.path.basename(sar_filename)
    date_string = fname.split('_')[5]
    
    try:
        sar_date = parse(date_string)
    except ValueError:
           raise ValueError("Incorrect datetime format, got: %s, should be: YYYYMMDDThhmmss" % date_string)
    
    return sar_date
