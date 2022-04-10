import argparse
import asyncio
import random
import sys
import time
import prometheus_client
import sml.asyncio

sensor_info = prometheus_client.Info('sensor_address', 'Sensor Address')

total_usage_gauge = prometheus_client.Gauge('total_usage', 'Total usage in kwh')
actual_usage_gauge = prometheus_client.Gauge('actual_usage', 'Actual usage in wh')


class SmlMessageExtractor:

    def __init__(self):
        self._vendor: str = ''
        self._serial: str = ''
        self._act_usage: float = 0.0
        self._total_usage: float = 0.0
        self._act_usage_details: list[float] = [0.0, 0.0, 0.0]
        self._total_usage_details: list[float] = [0.0, 0.0, 0.0]

    @property
    def is_initialized(self) -> bool:
        return self.vendor != '' and self.device != ''

    @property
    def vendor(self):
        return self._vendor

    @property
    def device(self):
        return self._serial.split(' ')[-1]

    @property
    def act_usage(self) -> float:
        if self.is_initialized:
            return self._act_usage
        return 0

    @property
    def act_usage_details(self):
        return self._act_usage_details

    @property
    def total_usage(self) -> float:
        if self.is_initialized:
            return self._total_usage / 1000
        return 0

    def listen_for_sml_message(self, message_body: sml.SmlSequence):
        values = message_body.get("valList", [])
        for val in values:
            obj_name = val.get("objName")

            if obj_name == '129-129:199.130.3*255':
                self._vendor = val.get("value")
                continue

            if obj_name == '1-0:0.0.9*255':
                self._serial = val.get("value")
                continue

        sensor_info.info({'Vendor': self.vendor, 'Device': self.device})

        if self.is_initialized:
            self._act_usage = self._parse_data(values, "1-0:16.7.0*255")
            self._act_usage_details = [
                self._parse_data(values, "1-0:36.7.0*255"),
                self._parse_data(values, "1-0:56.7.0*255"),
                self._parse_data(values, "1-0:76.7.0*255"),
            ]
            self._total_usage = self._parse_data(values, "1-0:1.8.0*255")

    @staticmethod
    def _parse_data(values: list[dict], key: str):
        found_value = [v.get("value") for v in values if v.get("objName") == key]
        if found_value:
            return float(found_value[0])

        return 0


sml_message_handler = SmlMessageExtractor()


async def process_request(sml_connector):
    await sml_connector.connect()
    while True:
        if sml_message_handler.is_initialized:
            total_usage_gauge.set_function(lambda: sml_message_handler.total_usage)
            actual_usage_gauge.set_function(lambda: sml_message_handler.act_usage)
        await asyncio.sleep(10)


def parse_args(args):
    parser = argparse.ArgumentParser(description='Parameters for addressing power consumption sensors')
    parser.add_argument('-s', dest='sensor_address', type=str, default='/dev/tty0',
                        help='an integer for the accumulator')
    parser.add_argument('-p', dest='port', type=int, default=8010,
                        help='Port for the prometheus server to fetch information')
    args = parser.parse_args(args=args)

    return args.sensor_address, args.port


if __name__ == '__main__':
    sensor_address, port = parse_args(sys.argv[1:])

    sml_connector = sml.asyncio.SmlProtocol(sensor_address)
    sml_connector.add_listener(sml_message_handler.listen_for_sml_message, ["SmlGetListResponse"])

    prometheus_client.start_http_server(port)
    sensor_info.info({'address': sensor_address})
    asyncio.run(process_request(sml_connector))
