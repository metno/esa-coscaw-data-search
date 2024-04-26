[![pytest](https://github.com/metno/esa-coscaw-data-search/actions/workflows/pytest.yml/badge.svg)](https://github.com/metno/esa-coscaw-data-search/actions/workflows/pytest.yml)
[![codecov](https://codecov.io/gh/metno/esa-coscaw-data-search/branch/main/graph/badge.svg)](https://codecov.io/gh/metno/esa-coscaw-data-search)

# esa-coscaw-data-search
Tools to find data to be used in ESA COSCaW

## Example: Get OPeNDAP urls to Norkyst800 and MET Nordic

```
# import module
from fadg import find_and_collocate

# Set dataset url
url = "https://thredds.met.no/thredds/dodsC/remotesensingsatellite/polar-swath/2024/04/07/metopb-avhrr-20240407222827-20240407223536.nc"

# Initialize fadg object - this will find overlapping Norkyst800 datasets
coll = find_and_collocate.NorKyst800(url)

# Get url of nearest Norkyst800 dataset
norkyst_url = coll.get_odap_url_of_nearest()

```

Use other classes for other data types, e.g., `Meps` for Meps weather forecast data.

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


