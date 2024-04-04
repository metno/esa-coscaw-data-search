import pytest

import collocation

@pytest.mark.core
def test_with_sar():
    """ 
    Test to find ocean and NWP model data matching Sentinel-1 file name
    """
    """ Sentinel-1 filename """
    s1filename = 'sentinel-1/S1B_IW_RAW__0SDV_20190107T171737_20190107T171810_014391_01AC8B_78F4.zip'
    
    """ Call odata to get url for matching model data """
    norkyst_url, met_nordic_url = collocation.with_sar.get_odap(s1filename)

    assert norkyst_url == 'https://thredds.met.no/thredds/fileServer/fou-hi/norkyst800m-1h/NorKyst-800m_ZDEPTHS_his.an.2019010700.nc'
    assert met_nordic_url == 'https://thredds.met.no/thredds/fileServer/metpparchivev3/2019/01/07/met_analysis_1_0km_nordic_20190107T17Z.nc'


@pytest.mark.core
def test_get_sar_date():
    """ Test for reading date from filename """
    s1filename = 'sentinel-1/S1B_IW_RAW__0SDV_20190107T171737_20190107T171810_014391_01AC8B_78F4.zip'
    sd = collection.with_sar._get_sar_date(s1filename)
    assert '%04d%02d%02dT%02d' % (sd.year,sd.month,sd.day,sd.hour) == '20190107T17'


@pytest.mark.core
def test_read_config():
    """ Test for reading config from xml file """
    conf_file = 'ancdata/config.xml'
    config = collection.with_sar._read_config(conf_file)
    assert config['norkyst_path'] == 'https://thredds.met.no/thredds/fileServer/fou-hi/norkyst800m-1h'
    assert config['met_nordic_path'] == 'https://thredds.met.no/thredds/fileServer/metpparchivev3'
