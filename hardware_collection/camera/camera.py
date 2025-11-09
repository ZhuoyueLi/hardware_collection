from __future__ import annotations
import abc
import time
import struct
from typing import ClassVar, List
from dataclasses import dataclass, field

from ..core.abstract_hardware import AbstractHardware


@dataclass
class CameraHeader:
    """
    Represents the metadata of a camera frame.
    Uses `struct` to pack data into a compact, fixed-size binary format.

    Binary Layout (little-endian "<"):
        - width (I):     4 bytes, unsigned int
        - height (I):    4 bytes, unsigned int
        - channels (B):  1 byte, unsigned char
        - timestamp (d): 8 bytes, double
        - frame_id (Q):  8 bytes, unsigned long long

    Total: 29 bytes (you can pad to 32 for alignment if needed).
    """

    STRUCT_FORMAT: ClassVar[str] = "<IIBdQ"  # Little-endian layout
    STRUCT_SIZE: ClassVar[int] = struct.calcsize(STRUCT_FORMAT)

    width: int
    height: int
    channels: int
    timestamp: float = field(default_factory=time.time)
    frame_id: int = 0

    def to_bytes(self) -> bytes:
        """
        Serialize the header into a fixed-length byte sequence.

        Returns:
            bytes: Packed binary representation of the header.
        """
        return struct.pack(
            self.STRUCT_FORMAT,
            self.width,
            self.height,
            self.channels,
            self.timestamp,
            self.frame_id
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "CameraHeader":
        """
        Deserialize bytes into a CameraHeader object.

        Args:
            data (bytes): The packed header bytes.

        Returns:
            CameraHeader: The reconstructed header.
        """
        width, height, channels, timestamp, frame_id = struct.unpack(
            cls.STRUCT_FORMAT,
            data[:cls.STRUCT_SIZE]
        )
        return cls(width, height, channels, timestamp, frame_id)

    def __repr__(self) -> str:
        """Return a readable string representation."""
        return (
            f"<CameraHeader "
            f"{self.width}x{self.height}x{self.channels} "
            f"id={self.frame_id} t={self.timestamp:.3f}>"
        )


class CameraFrame:
    def __init__(self, header: CameraHeader, image_bytes: bytes):
        self.header = header
        self.image_bytes = image_bytes

    def to_bytes(self) -> List[bytes]:
        return [self.header.to_bytes(), self.image_bytes]

    @staticmethod
    def from_bytes(data: bytes):
        header_size = struct.calcsize(CameraHeader.STRUCT_FORMAT)
        header = CameraHeader.from_bytes(data[:header_size])
        image_bytes = data[header_size:]
        return CameraFrame(header, image_bytes)


class AbstractCamera(AbstractHardware):
    """Camera hardware component."""

    def __init__(self, address: str):
        """Initialize the camera hardware component.

        Args:
            address (str): The address to connect the ZeroMQ socket to.
        """
        super().__init__(address=address)
        self.width = None
        self.height = None


    @abc.abstractmethod
    def initialize(self) -> None:
        raise NotImplementedError("Subclasses must implement initialize method.")

    def publish_image(self, frame: CameraFrame) -> None:
        """Publish the captured image frame over ZeroMQ.

        Args:
            frame (CameraFrame): The captured image frame.
        """
        frame = self.capture_image()
        self.pub_socket.send_multipart(frame.to_bytes())

    @abc.abstractmethod
    def capture_image(self) -> CameraFrame:
        """Get sensor data from the camera.

        Returns:
            CameraFrame: The sensor data.
        """
        raise NotImplementedError("Subclasses must implement capture_image method.")
    
    