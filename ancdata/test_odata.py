import ancdata.odata as odata


def test_odata():
    s1filename = 'sentinel-1/S1B_IW_RAW__0SDV_20190107T171737_20190107T171810_014391_01AC8B_78F4.zip'

    norkyst_url, met_nordic_url = odata.get_odap(s1filename)
    print(s1filename)
    print(norkyst_url)
    print(met_nordic_url)
    assert norkyst_url == 'https://thredds.met.no/thredds/fileServer/fou-hi/norkyst800m-1h/NorKyst-800m_ZDEPTHS_his.an.2019010700.nc'


