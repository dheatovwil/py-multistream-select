# Multistream
--------------
[![Build Status](https://api.travis-ci.org/dheatovwil/py-multistream-select.svg?branch=master)](https://travis-ci.org/dheatovwil/py-multistream-select) [![codecov](https://codecov.io/gh/dheatovwil/py-multistream-select/branch/master/graph/badge.svg)](https://codecov.io/gh/dheatovwil/py-multistream-select)



This repository contains the python implementation of the [multistream-select](https://github.com/multiformats/multistream) protocol.

## Getting started
-------------------

## Running the tests
This project uses [pytest](https://docs.pytest.org/en/latest/).

On OSX, running `python -m pytest` runs all the tests. Amongst known issues, pytest might throw an `ImportError` if it cannot pull in the right libraries included in the test files. Try installing the library itself in debug mode using `pip install -e .` as it will then add `py-multistream-select` to your `PYTHONPATH`.

## Contributing
---------------

## License
-----------
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
