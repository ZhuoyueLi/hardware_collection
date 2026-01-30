from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pyzlc
import tyro
#need to install gello in the environment
from gello.agents.gello_agent import GelloAgent

from ..core.abstract_hardware import AbstractHardware


@dataclass
class Args:
    node_name: str = "gello"
    ip: str = "127.0.0.2"
    hardware_port: str = "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FT94EVRT-if00-port0" #check the actual config
    state_pub_rate_hz: int = 1000
    publish_state: bool = True


class ZlcGelloNode(AbstractHardware):
   
    def __init__(self, name: str, agent: GelloAgent, state_pub_rate_hz: int = 50,
                 publish_state: bool = True, node_ip: str = "127.0.0.2"):
        super().__init__(f"{name}/gello_state", node_name=name, node_ip=node_ip)
        self._name = name
        self._agent = agent
        self._publish_state = publish_state
        self._state_dt_ms = int(1000 / max(1, state_pub_rate_hz))
        self._stop_event = threading.Event()
        self._state_thread: threading.Thread | None = None

        self._arm_state_pub = pyzlc.Publisher(f"{name}/gello_arm_state")
        self._gripper_state_pub = pyzlc.Publisher(f"{name}/gello_gripper_state")
        self.initialize()
        if self._publish_state:
            self._state_thread = threading.Thread(target=self._state_publish_loop,
                                                  daemon=True)
            self._state_thread.start()

    def _build_arm_state(self) -> Dict[str, List[float]]:
        joints_arr = np.asarray(self._agent._robot.get_joint_state()[:-1], dtype=float).reshape(-1)
        return {"joint_state": joints_arr.tolist()}

    def _build_gripper_state(self) -> Dict[str, float | int]:
        gripper = float(np.asarray(self._agent._robot.get_joint_state()[-1], dtype=float))
        return {"gripper": gripper}

    def initialize(self) -> None:
        """Initialize the Gello hardware component."""
        pyzlc.info(f"[GelloNode] Initializing hardware on port {self._agent}")


    def _state_publish_loop(self):
        pyzlc.info(f"[GelloNode] State publish thread started ({1000 // self._state_dt_ms} Hz)")
        while not self._stop_event.is_set():
            arm_state = self._build_arm_state()
            gripper_state = self._build_gripper_state()
            self._arm_state_pub.publish(arm_state)
            self._gripper_state_pub.publish(gripper_state)
            pyzlc.sleep(self._state_dt_ms)
        pyzlc.info("[GelloNode] State publish thread stopped")

    def stop(self):
        self._stop_event.set()
        if self._state_thread and self._state_thread.is_alive():
            self._state_thread.join()
        self.close_sockets()


def main():
    args = tyro.cli(Args)
    agent = GelloAgent(port=args.hardware_port)
    node = ZlcGelloNode(args.node_name, agent,
                        state_pub_rate_hz=args.state_pub_rate_hz,
                        publish_state=args.publish_state,
                        node_ip=args.ip)
    try:
        pyzlc.info(f"[GelloNode] ZeroLanCom node '{args.node_name}' started on {args.ip}")
        pyzlc.spin()
    except KeyboardInterrupt:
        pyzlc.info("[GelloNode] Shutting down...")
    finally:
        node.stop()


if __name__ == "__main__":
    main()