# hardware_collection

Python package for hardware collection utilities.

## Install
### Build conda env
```bash
conda create -n hardware_collection python=3.10 -y
conda activate hardware_collection
```
### Install basic dependencies
```bash
pip install pyzlc pyserial numpy opencv-python cython tyro
pip install depthai
```
### Install cam dependencies
- ZED
    - sdk: https://www.stereolabs.com/developers
    - `pip install pyzed`
- depthai (OAK)
    - `pip install depthai`

### Insatll the project
`pip install -e .`

## Gello 
### Get offset (run everytime open gello)
```
python hardware_collection\gello\scripts\gello_get_offset.py --start-joints 0 0 0 -2.15 0 2.15 0 --joint-signs 1 -1 1 1 1 1 1 --port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FT94EVRT-if00-port0
```