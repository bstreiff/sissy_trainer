Connectivity
------------

This library sits on top of `pyserial`_.

Any parameter accepting a URL may therefore accept any type of URL supported
by pyserial as noted in its documentation on `URL Handlers`_.

Note that only serial (RS-232) communication is supported at this time.
Although some Extron models do support interfaces over Telnet, use of the
``socket://`` URL scheme with such devices is expected to fail.

There exist several models of Extron devices that utilize a physical DE-9
port for serial, but also repurpose pins for other uses. For example, the
DVS 204 and DVS 304 series utilize the DCD, DTR, DSR, and RTS pins for
"contact closure" for inputs 1 through 4, and the RI pin for an infrared
receiver. These features are not supported by this library, and it is
recommended that those pins be no-connects; this may require building a
custom serial cable.

.. _pyserial: https://pyserial.readthedocs.io/en/latest/
.. _URL Handlers: https://pyserial.readthedocs.io/en/latest/url_handlers.html
