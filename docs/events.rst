Events
------

While the SIS protocol is largely a simple command/response protocol, it does
also include facilities for device-initiated messages. These are often issued
by the device in response to a physical event; for example, manual configuration
using the device front panel, or a signal change on an input.

These are handled with an asynchronous callback system. Each protocol object
contains ``add_event_listener`` and ``remove_event_listener`` methods to add
listeners.

.. code-block:: python

   def handle_volume_event(event):
       print("New volume: %d" % event.value)

   def main():
      dev = ExtronDevice("COM3", part_number=PartNumber.EXTRON_MPS_112)
      with dev as mps112:
          mps112.add_event_listener("volume", handle_volume_event)


.. automethod:: sistrum._protocol.ExtronProtocol.add_event_listener
   :noindex:

.. automethod:: sistrum._protocol.ExtronProtocol.remove_event_listener
   :noindex:

.. autoclass:: sistrum.Event
   :members:
   :noindex:

.. autoclass:: sistrum.ValueChangeEvent
   :members:
   :show-inheritance:
   :noindex:

