import zmq
import abc


class AbstractHardware:
    """Abstract base class for hardware components using ZeroMQ for communication."""

    def __init__(self, address: str):
        """Initialize the hardware component with a ZeroMQ context and socket.

        Args:
            address (str): The address to connect the ZeroMQ socket to.
        """
        self.pub_socket = zmq.Context().socket(zmq.REQ)
        self.pub_socket.bind(address)

    @abc.abstractmethod
    def initialize(self) -> None:
        """Initialize the hardware component."""
        raise NotImplementedError("Subclasses must implement initialize method.")

