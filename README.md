[![pytest](https://github.com/metno/esa-coscaw-data-search/actions/workflows/pytest.yml/badge.svg)](https://github.com/metno/esa-coscaw-data-search/actions/workflows/pytest.yml)
[![codecov](https://codecov.io/gh/metno/esa-coscaw-data-search/branch/main/graph/badge.svg)](https://codecov.io/gh/metno/esa-coscaw-data-search)

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

## Tests

The tests use `pytest`. To run all tests for all modules, run:
```bash
python -m pytest -vv
```

To add coverage, and to optionally generate a coverage report in HTML, run:
```bash
python -m pytest -vv --cov=dmci --cov-report=term-missing --cov-report=html
```
Coverage requires the `pytest-cov` package.


