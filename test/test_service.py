from collections import namedtuple

import bitstring
import pytest
import sml

import service


class TestSmlMessageExtractor:

    def test_that_init_initializes_object(self):
        sme = service.SmlMessageExtractor()

        assert sme.is_initialized is False


class MockMessage(dict):
    __FIELDS = (
        'transactionId',
        'groupNo',
        'abortOnError',
        'messageBody',
        'crc16',
        'endOfSmlMsg',
    )

    ListItem = namedtuple('ListItem', ['length', 'value'])

    def __init__(self, value):
        super().__init__()
        self.value = MockMessage.ListItem(length=len(value), value=value)


class TestSmeMessageExtractorMessageListener:
    message = sml.SmlMessage(bitstring.ConstBitStream(
        '0x7605087c1292620062007263070177010b090149534b0004386a30070100620affff72'
        '6201650665b91b7777078181c78203ff010101010449534b0177070100000009ff010101010'
        'b090149534b0004386a300177070100010800ff650000018201621e52ff59000000000c3d53'
        '390177070100010801ff0101621e52ff59000000000c3d53390177070100010802ff0101621'
        'e52ff5900000000000000000177070100100700ff0101621b520055000000030177078181c7'
        '8205ff0101010183020d7d982f2312592f658f7f25a3516027d00b03de90fac92cbca0e56b9'
        '102466f219fe9f997d9d5bee2ff5d546d30a96801010163806200'
    ))

    def test_that_message_listener_sets_vendor(self):
        sme = service.SmlMessageExtractor()
        sme.listen_for_sml_message(self.message['messageBody'])

        assert sme.vendor == 'ISK'

    def test_that_message_listener_sets_device_number(self):
        sme = service.SmlMessageExtractor()
        sme.listen_for_sml_message(self.message['messageBody'])

        assert sme.device == '70806064'

    def test_that_is_initialized_after_message(self):
        sme = service.SmlMessageExtractor()
        sme.listen_for_sml_message(self.message['messageBody'])

        assert sme.is_initialized

    def test_that_actual_value_is_set(self):
        sme = service.SmlMessageExtractor()
        sme.listen_for_sml_message(self.message['messageBody'])

        assert sme.act_usage == 3.0

    def test_that_detailed_act_usage_is_set(self):
        sme = service.SmlMessageExtractor()
        sme.listen_for_sml_message(self.message['messageBody'])

        assert all(sme.act_usage_details)

    def test_that_total_usage_is_set(self):
        sme = service.SmlMessageExtractor()
        sme.listen_for_sml_message(self.message['messageBody'])

        assert sme.total_usage == 20534.5593



class TestParseArgs:

    def test_that_it_returns_default_value(self):
        sa, port = service.parse_args([])
        assert sa == '/dev/tty0'
        assert port == 8010

    def test_that_port_is_used(self):
        sa, port = service.parse_args(['-p=8025'])
        assert port == 8025

    @pytest.mark.parametrize('sensor_address', ('tty/test1',))
    def test_that_sensor_address_is_used(self, sensor_address: str):
        sa, port = service.parse_args(['-s=' + sensor_address])
        assert sa == sensor_address
