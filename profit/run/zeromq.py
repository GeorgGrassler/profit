""" zeromq Interface

Ideas & Help from the 0MQ Guide (zguide.zeromq.org, examples are licensed with MIT)
"""

import zmq
import numpy as np
import json
from time import sleep
from logging import Logger
import os

from .interface import RunnerInterface, WorkerInterface


# === ZeroMQ Interface === #


class ZeroMQRunnerInterface(RunnerInterface, label="zeromq"):
    """Runner-Worker Interface using the lightweight message queue `ZeroMQ <https://zeromq.org/>`_

    - can use different transport systems, most commonly tcp
    - can be used efficiently on a cluster (tested)
    - expected to be inefficient for a large number of small, locally run simulations where communication overhead is
      a concern (unverified, could be mitigated by using a different transport system)
    - known issue: some workers were unable to establish a connection with three tries, reason unknown

    Parameters:
        transport: ZeroMQ transport protocol
        address: ip address of the Runner Interface
        port: port of the Runner Interface
        connection: override for the ZeroMQ connection spec (Worker side)
        bind: override for the ZeroMQ bind spec (Runner side)
        timeout: connection timeout when waiting for an answer in seconds (Runner & Worker)
        retries: number of tries to establish a connection (Worker)
        retry_sleep: sleep time in seconds between each retry (Worker)

    Attributes:
        socket (zmq.Socket): ZeroMQ backend
        logger (logging.Logger): Logger
    """

    def __init__(
        self,
        size,
        input_config,
        output_config,
        *,
        transport="tcp",
        address="localhost",
        port=9000,
        connection=None,
        bind=None,
        timeout=2.5,
        retries=3,
        retry_sleep=10,
        logger_parent: Logger = None,
    ):
        if "FLAGS" not in [var[0] for var in self.internal_vars]:
            self.internal_vars += [("FLAGS", np.byte.__name__)]
        super().__init__(size, input_config, output_config, logger_parent=logger_parent)
        self.transport = transport
        self.address = address
        self.port = port
        self.connection = connection
        self._bind = bind
        self.timeout = timeout
        self.retries = retries
        self.retry_sleep = retry_sleep

        self.socket = zmq.Context.instance().socket(zmq.ROUTER)
        self.socket.bind(self.bind)
        self.logger.info(f"connected to {self.bind}")

    @property
    def bind(self):
        if self._bind is None:
            return f"{self.transport}://*:{self.port}"
        else:
            return self._bind

    @bind.setter
    def bind(self, value):
        self._bind = value

    @property
    def config(self):
        config = {
            "transport": self.transport,
            "address": self.address,
            "port": self.port,
            "connection": self.connection,
            "bind": self._bind,
            "timeout": self.timeout,
            "retries": self.retries,
            "retry_sleep": self.retry_sleep,
        }
        return super().config | config

    def poll(self):
        self.logger.debug("polling: checking for messages")
        while self.socket.poll(timeout=int(1e3 * self.timeout), flags=zmq.POLLIN):
            msg = self.socket.recv_multipart()
            # ToDo: Heartbeats
            self.handle_msg(msg[0], msg[2:])

    def handle_msg(self, address: bytes, msg: list):
        if address[:4] == b"req_":  # req_123
            run_id = int(address[4:])
            self.logger.debug(f"received {msg[0]} from run {run_id}")
            if msg[0] == b"READY":
                input_descr = json.dumps(self.input_vars).encode()
                output_descr = json.dumps(self.output_vars).encode()
                self.logger.debug(
                    f"send input {input_descr} + {self.input[run_id]} + output {output_descr}"
                )
                self.socket.send_multipart(
                    [address, b"", input_descr, self.input[run_id], output_descr]
                )
                self.internal["FLAGS"][run_id] |= 0x02
            elif msg[0] == b"DATA":
                self.output[run_id] = np.frombuffer(msg[1], dtype=self.output_vars)
                self.logger.debug(
                    f"received output {np.frombuffer(msg[1], dtype=self.output_vars)}"
                )
                self.internal["DONE"][run_id] = True
                self.internal["FLAGS"][run_id] |= 0x08
                self.logger.debug("acknowledge DATA")
                self.socket.send_multipart([address, b"", b"ACK"])  # acknowledge
            elif msg[0] == b"TIME":
                self.internal["TIME"][run_id] = np.frombuffer(msg[1], dtype=np.uint)
                self.logger.debug("acknowledge TIME")
                self.socket.send_multipart([address, b"", b"ACK"])  # acknowledge
            elif msg[0] == b"DIE":
                self.internal["FLAGS"][run_id] |= 0x04
                self.logger.debug("acknowledge DIE")
                self.socket.send_multipart([address, b"", b"ACK"])  # acknowledge
            else:
                self.logger.warning(f"received unknown message {address}: {msg}")
        else:
            self.logger.warning(
                f"received message from unknown client {address}: {msg}"
            )

    def clean(self):
        self.logger.debug("cleaning: closing socket")
        self.socket.close(0)


class ZeroMQWorkerInterface(WorkerInterface, label="zeromq"):
    """Runner-Worker Interface using the lightweight message queue `ZeroMQ <https://zeromq.org/>`_

    counterpart to :py:class:`ZeroMQRunnerInterface`
    """

    def __init__(
        self,
        run_id: int,
        *,
        transport="tcp",
        address="localhost",
        port=9000,
        connection=None,
        bind=None,
        timeout=2.5,
        retries=3,
        retry_sleep=10,
        logger_parent: Logger = None,
    ):
        super().__init__(run_id, logger_parent=logger_parent)
        self.transport = transport
        self.address = address
        self.port = port
        self._connection = connection
        self.bind = bind
        self.timeout = timeout
        self.retries = retries
        self.retry_sleep = retry_sleep

        self._connected = False

    @property
    def connection(self):
        if self._connection is None:
            address = os.environ.get("PROFIT_RUNNER_ADDRESS") or "localhost"
            return f"{self.transport}://{self.address}:{self.port}"
        else:
            return self._connection

    @connection.setter
    def connection(self, value):
        self._connection = value

    @property
    def config(self):
        config = {
            "transport": self.transport,
            "address": self.address,
            "port": self.port,
            "connection": self._connection,
            "bind": self._bind,
            "timeout": self.timeout,
            "retries": self.retries,
            "retry_sleep": self.retry_sleep,
        }
        return super().config | config

    def retrieve(self):
        self.connect()
        self.request("READY")
        self.disconnect()

    def transmit(self):
        self.connect()
        self.request("TIME")
        self.request("DATA")
        self.disconnect()

    def clean(self):
        if self._connected:
            self.disconnect()

    def connect(self):
        self.socket = zmq.Context.instance().socket(zmq.REQ)
        self.socket.setsockopt(zmq.IDENTITY, f"req_{self.run_id}".encode())
        self.socket.connect(self.connection)
        self.logger.info(f"connected to {self.connection}")
        self._connected = True

    def disconnect(self):
        self.socket.close(linger=0)
        self._connected = False

    def request(self, request):
        """0MQ - Lazy Pirate Pattern"""
        if not self._connected:
            self.logger.info("no connection")
            self.connect()
        if request not in ["READY", "DATA", "TIME"]:
            raise ValueError(f'unknown request "{request}"')
        tries = 0
        while True:
            msg = [request.encode()]
            if request == "DATA":
                msg.append(self.output)
            elif request == "TIME":
                msg.append(np.uint(self.time))
            self.socket.send_multipart(msg)
            self.logger.debug(f"send message {msg}")
            if self.socket.poll(timeout=int(1e3 * self.timeout), flags=zmq.POLLIN):
                response = None
                try:
                    response = self.socket.recv_multipart()
                    if request == "READY":
                        input_descr, input_data, output_descr = response
                        input_descr = [
                            tuple(column) for column in json.loads(input_descr.decode())
                        ]
                        output_descr = [
                            tuple(column[:2] + [tuple(column[2])])
                            for column in json.loads(output_descr.decode())
                        ]
                        self.input = np.frombuffer(input_data, dtype=input_descr)[0]
                        self.output = np.zeros(1, dtype=output_descr)[0]
                        self.logger.info("READY: received input data")
                        self.logger.debug(
                            f"received: {np.frombuffer(input_data, dtype=input_descr)}"
                        )
                        return
                    else:
                        assert response[0] == b"ACK"
                        self.logger.debug(f"{request}: message acknowledged")
                        return
                except (ValueError, AssertionError):
                    self.logger.debug(f"{request}: received {response}")
                    self.logger.error(f"{request}: malformed reply")
            else:
                self.logger.warning(f"{request}: no response")
                tries += 1
                sleep(self.retry_sleep)

            if tries >= self.retries + 1:
                self.logger.error(
                    f"{request}: {tries} requests unsuccessful, abandoning"
                )
                self.disconnect()
                raise ConnectionError("could not connect to RunnerInterface")

            # close and reopen the socket
            self.disconnect()
            self.connect()
