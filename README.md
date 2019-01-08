
# py-multistream-select
 
[![Travis CI](https://api.travis-ci.org/dheatovwil/py-multistream-select.svg?branch=master)](https://travis-ci.org/dheatovwil/py-multistream-select) 
[![codecov.io](https://codecov.io/gh/dheatovwil/py-multistream-select/branch/master/graph/badge.svg)](https://codecov.io/gh/dheatovwil/py-multistream-select)

> an implementation of the multistream protocol in python

## Table of Contents

- [Install](#install)
- [Usage](#usage)
- [Contribute](#contribute)
- [License](#license)

## Install


`py-multistream-select` is a standard PyPI module which can be installed with:

```sh
pip install multistream-select
```

## Usage

### Example
```python
from multistream_select.multiselect import Multiselect
from multistream_select.multiselect_client import MultiselectClient

async def client_get_protocol(host_info):
  protocols = [ '/cats', '/dogs' ]
  stream = func_to_create_stream(host_info)
  client = MultiselectClient()
  return selected_protocol = await client.select_one_of(protocols, stream)

async def host_get_protocol(handlers):
  stream = func_to_create_stream()
  host = Multiselect()
  for protocol in handlers:
    host.add_handler(protocol, handlers[protocol])
  return host.negotiate(stream)
```

## Contribute

Contributions welcome. Please check out [the issues](https://github.com/dheatovwil/py-multistream-select/issues).

Check out our [contributing document](https://github.com/multiformats/multiformats/blob/master/contributing.md) for more information on how we work, and about contributing in general. Please be aware that all interactions related to multiformats are subject to the IPFS [Code of Conduct](https://github.com/ipfs/community/blob/master/code-of-conduct.md).

Small note: If editing the README, please conform to the [standard-readme](https://github.com/RichardLitt/standard-readme) specification.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
