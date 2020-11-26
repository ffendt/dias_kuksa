"""
This script is to read CAN messages based on PGN - SAE J1939
according to the given dbcfile, and dependent on `dbcfeeder.py`
(https://github.com/eclipse/kuksa.val/blob/master/clients/feeder/dbc2val/dbcfeeder.py)
Therefore it needs to be located in the same directory where `dbcfeeder.py` is located.

To use the script, the following lines should be added to `dbcfeeder.py`.

	import j1939reader
	...
	j1939R = j1939reader.J1939Reader(cfg,canQueue,mapping)
	j1939R.start_listening()

	## `j1939reader.py` is comparable to `dbcreader.py`, so comment the following lines
	# dbcR = dbcreader.DBCReader(cfg,canQueue,mapping)
	# dbcR.start_listening()

Prior to using this script, j1939 and 
the relevamnt wheel-package should be installed first:

    $ pip3 install j1939
    $ git clone https://github.com/benkfra/j1939.git
    $ cd j1939
    $ pip install .
"""

import logging
import time
import cantools
import j1939

logging.getLogger('j1939').setLevel(logging.DEBUG)
logging.getLogger('can').setLevel(logging.DEBUG)

class J1939Reader(j1939.ControllerApplication):
    """CA to produce messages

    This CA produces simulated sensor values and cyclically sends them to
    the bus with the PGN 0xFEF6 (Intake Exhaust Conditions 1).
    """

    def __init__(self, cfg, rxqueue, mapper):
        # compose the name descriptor for the new ca
        name = j1939.Name(
            arbitrary_address_capable=0,
            industry_group=j1939.Name.IndustryGroup.Industrial,
            vehicle_system_instance=1,
            vehicle_system=1,
            function=1,
            function_instance=1,
            ecu_instance=1,
            manufacturer_code=666,
            identity_number=1234567
            )
        device_address_preferred = 128
        # old fashion calling convention for compatibility with Python2
        j1939.ControllerApplication.__init__(self, name, device_address_preferred)
        # adaptation
        self.queue=rxqueue
        self.cfg=cfg
        self.db = cantools.database.load_file(cfg['vss.dbcfile'])
        self.mapper=mapper
        self.canidwl = self.get_whitelist()
        self.parseErr=0

    def start(self):
        """Starts the CA
        (OVERLOADED function)
        """
        # add our timer event
        self._ecu.add_timer(0.500, self.timer_callback)
        # call the super class function
        return j1939.ControllerApplication.start(self)

    def timer_callback(self, cookie):
        """Callback for sending the IEC1 message

        This callback is registered at the ECU timer event mechanism to be
        executed every 500ms.

        :param cookie:
            A cookie registered at 'add_timer'. May be None.
        """
        # wait until we have our device_address
        if self.state != j1939.ControllerApplication.State.NORMAL:
            # returning true keeps the timer event active
            return True

        pgn = j1939.ParameterGroupNumber(0, 0xFE, 0xF6)
        data = [
            j1939.ControllerApplication.FieldValue.NOT_AVAILABLE_8, # Particulate Trap Inlet Pressure (SPN 81)
            j1939.ControllerApplication.FieldValue.NOT_AVAILABLE_8, # Boost Pressure (SPN 102)
            j1939.ControllerApplication.FieldValue.NOT_AVAILABLE_8, # Intake Manifold 1 Temperature (SPN 105)
            j1939.ControllerApplication.FieldValue.NOT_AVAILABLE_8, # Air Inlet Pressure (SPN 106)
            j1939.ControllerApplication.FieldValue.NOT_AVAILABLE_8, # Air Filter 1 Differential Pressure (SPN 107)
            j1939.ControllerApplication.FieldValue.NOT_AVAILABLE_16_ARR[0], # Exhaust Gas Temperature (SPN 173)
            j1939.ControllerApplication.FieldValue.NOT_AVAILABLE_16_ARR[1],
            j1939.ControllerApplication.FieldValue.NOT_AVAILABLE_8, # Coolant Filter Differential Pressure (SPN 112)
            ]

        # SPN 105, Range -40..+210
        # (Offset -40)
        receiverTemperature = 30
        data[2] = receiverTemperature + 40

        self.send_message(6, pgn.value, data)

        # returning true keeps the timer event active
        return True

    def get_whitelist(self):
        print("Collecting signals, generating CAN ID whitelist")
        wl = []
        for entry in self.mapper.map():
            canid=self.get_canid_for_signal(entry[0])
            if canid != None and canid not in wl:
                wl.append(canid)
        return wl

    def get_canid_for_signal(self, sig_to_find):
        for msg in self.db.messages:
            for signal in msg.signals:
                if signal.name == sig_to_find:
                    id = msg.frame_id
                    print("Found signal {} in CAN frame id 0x{:02x}".format(signal.name, id))
                    return id
        print("Signal {} not found in DBC file".format(sig_to_find))
        return None

    def start_listening(self):
        print("Open CAN device {}".format(self.cfg['can.port']))
        # create the ElectronicControlUnit (one ECU can hold multiple ControllerApplications)
        ecu = j1939.ElectronicControlUnit()
        # Connect to the CAN bus
        ecu.connect(bustype='socketcan', channel=self.cfg['can.port'])
        # add CA to the ECU
        ecu.add_ca(controller_application=self)
        self.start()
        
    def on_message(self, pgn, data):
        pgn_hex = hex(pgn)[2:] # only hex(pgn) without '0x' prefix
        for message in self.db.messages:
            message_hex = hex(message.frame_id)[-6:-2] # only hex(pgn) without '0x' prefix, priority
            if pgn_hex == message_hex:
                signals = message._signals
                for signal in signals:
                    name = signal._name
                    start_byte = int((signal._start / 8) + 1) # start from 1
                    num_of_bytes = signal._length / 8 # most likely 1 or 2
                    byte_order = signal._byte_order # 'little_endian' or 'big_endian'
                    scale = signal._scale
                    offset = signal._offset
                    val = self.decode_signal(start_byte-1, num_of_bytes, byte_order, scale, offset, data)
                    #print("Signal: " + signal._name + ", Value: " + str(val))
                    if name in self.mapper:
                        rxTime=time.time()
                        if self.mapper.minUpdateTimeElapsed(name, rxTime):
                            self.queue.put((name, val))
                break

    def decode_signal(self, start_byte, num_of_bytes, byte_order, scale, offset, data):
        val = 0
        if num_of_bytes == 1:
            start_data = data[start_byte]
            val = offset + start_data * scale
        else:
            val = self.decode_2bytes(start_byte, byte_order, scale, offset, data)
        return val

    def decode_2bytes(self, start_byte, byte_order, scale, offset, data):
        start_data = data[start_byte]
        end_data = data[start_byte + 1]
        start_data_hex = hex(start_data)[2:] # without '0x' prefix
        end_data_hex = hex(end_data)[2:] # without '0x' prefix
        lit_end_hex_str = ""
        # Little Endian - Intel, AMD
        if byte_order == 'little_endian':    
            lit_end_hex_str = "0x" + end_data_hex + start_data_hex
        # Big Endian (a.k.a Endianness) - Motorola, IBM 
        else:
            lit_end_hex_str = "0x" + start_data_hex + end_data_hex
        raw_Value = int(lit_end_hex_str, base=16)
        val = offset + raw_Value * scale
        return val
