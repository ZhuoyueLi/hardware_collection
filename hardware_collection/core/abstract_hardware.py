import abc
from typing import Optional
import pyzlc


class AbstractHardware:
    """Abstract base class for hardware components using ZeroLanCom Publisher."""

    _pyzlc_initialized = False

    def __init__(self, publish_topic: str, node_name: str = None, node_ip: str = None):
        """Initialize with pyzlc Publisher.

        Args:
            publish_topic (str): Topic name to publish data via ZeroLanCom.
            node_name (str): Node name for pyzlc.init. Only initializes pyzlc on first instantiation.
            node_ip (str): Node IP for pyzlc.init.
        """
        # Initialize pyzlc once on first AbstractHardware instantiation
        if node_name and node_ip and not AbstractHardware._pyzlc_initialized:
            pyzlc.init(node_name, node_ip)
            AbstractHardware._pyzlc_initialized = True
        
        self.publish_topic = publish_topic
        self.publisher: Optional[pyzlc.Publisher] = None
        
        try:
            self.publisher = pyzlc.Publisher(publish_topic)
        except Exception as e:
            print(f"Warning: Failed to create publisher for topic '{publish_topic}': {e}")

    def close_sockets(self) -> None:
        """Close any allocated ZeroLanCom publishers."""
        self.publisher = None

    @abc.abstractmethod
    def initialize(self) -> None:
        """Initialize the hardware component."""
        raise NotImplementedError("Subclasses must implement initialize method.")

