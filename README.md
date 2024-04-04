# esa-coscaw-data-search
Tools to find data to be used in ESA COSCaW

## Get OPeNDAP urls to Norkyst800 and MET Nordic
Sentinel-1 acqusition time are read from filename and used in seach of model data

## Example:
```
# import module
import collocation

# Specify Sentinel-1 filename
s1filename = '/lustre/storeC-ext/users/coscaw/sentinel-1/2020/01/S1A_IW_RAW__0SDV_20200103T055642_20200103T055714_030632_03828E_875E.zip'

# Call function to get model urls matching Sentinel-1 
norkyst_url, met_nordic_url = collocation.with_sar.get_odap(s1filename)

```
