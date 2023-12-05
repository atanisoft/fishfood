#
# SPDX-FileCopyrightText: 2023 Mike Dunston (atanisoft)
#
# SPDX-License-Identifier: MIT
#
# This script will reconfigure OpenPnP for use with the Opulo Lumen PnP machine.
#

import time
from org.openpnp.model import Configuration, Location, Length, LengthUnit
from org.openpnp.machine.reference import ReferenceActuator, ReferenceActuatorProfiles, ReferenceNozzle, ReferenceNozzleTip
from org.openpnp.machine.reference.axis import ReferenceControllerAxis, ReferenceMappedAxis, ReferenceVirtualAxis
from org.openpnp.machine.reference.camera import OpenPnpCaptureCamera, OpenCvCamera
from org.openpnp.machine.reference.driver import GcodeDriver, SerialPortCommunications
from org.openpnp.spi import Actuator, Axis, Camera, Driver
from org.openpnp.model import LengthUnit, Solutions

####### START OF USER MODIFYABLE SETTINGS #######

# CONTROL_BOARD_TYPE controls the configuration settings used for gcode drivers
# and splitting of the axis control between a main board and secondary board.
#
# supported values:
# Opulo       - Single control board mounted under the staging plate that
#               controls all functionality of the PnP machine.
# Winterbloom - Two control boards, one mounted under the staging plate that
#               only controls X and Y axes, vacuum pumps and valves, and bottom
#               lights. The second control board is mounted to the head and
#               controls Z, A, B axes and top light.
CONTROL_BOARD_TYPE = 'Winterbloom'

# CLEANUP_EXISTING_FEEDERS controls the removal of existing feeders from the
# configuration as part of the reconfiguration process. When set to True all
# existing feeders will be removed.
CLEANUP_EXISTING_FEEDERS = True

# WIDE_BODY_MOD controls the X axis limits, in the default case the limits are
# based on the 600mm extrusion used in the default Lumen configuration. When
# the machine has been modified with the Wide Body mod the X extrusion is
# increased to 800mm providing access for both the left and right nozzles to
# reach the full width of the staging plate(s) and feeders on front and rear
# rails.
WIDE_BODY_MOD = True

# DUAL_NOZZLE controls the number of nozzles to be created on the default head.
# Most Lumen kits were single nozzle but newer v3 machines are dual nozzle.
DUAL_NOZZLE = True

# USE_OPENCV_CAMERAS switches the camera capture type from OpenPnPCaptureCamera
# to OpenCVCamera.
USE_OPENCV_CAMERAS = False

# USE_PHOTON_FEEDERS should be enabled if you intend to use Opulo Feeders with
# your OpenPnP configuration
USE_PHOTON_FEEDERS = True

# When USE_LINEAR_RAILS is set to True the CONNECT_COMMAND gcode will be
# modified to increase movement speeds.
USE_LINEAR_RAILS = False

# X_HOMING_SENSITIVITY and Y_HOMING_SENSITIVITY configure the sensitivity of
# sensorless homing.
X_HOMING_SENSITIVITY = 50
Y_HOMING_SENSITIVITY = 30

# TOP_CAMERA_OPENCV_INDEX and BOTTOM_CAMERA_OPENCV_INDEX are the v4l2-ctl
# device numbers to use when USE_OPENCV_CAMERAS is set to True
TOP_CAMERA_OPENCV_INDEX = 0
BOTTOM_CAMERA_OPENCV_INDEX = 2

######## END OF USER MODIFYABLE SETTINGS ########

if CONTROL_BOARD_TYPE.lower() == 'opulo':
    BASE_GCODE_DRIVER_NAME = 'Lumen'
    HEAD_GCODE_DRIVER_NAME = 'Lumen'
    CONNECT_COMMAND_GCODE =
    [
        'G21 ; Set millimeters mode',
        'G90 ; Set absolute positioning mode',
        'M82 ; Set absolute mode for extruder',
    ]

    if USE_LINEAR_RAILS:
        CONNECT_COMMAND_GCODE.append(
        [
            'M569 S0 X Y ; Switch from stealthChop to spreadCycle',
            'M204 T5000 ; Set max travel acceleration',
            'M201 Y3500 ; Set max Y acceleration',
            'M906 Y1200 ; Set Y motor current',
            'M201 X5000 ; Set max X acceleration',
            'M203 X1000 Y1000 ; Set max feedrate in mm/min',
            'M906 A200 ; Set L motor current',
            'M906 B200 ; Set R motor current',
        ])

    GCODE_DRIVERS = [
        {
            'name' : BASE_GCODE_DRIVER_NAME,
            'gcode': [
                {
                    'type': GcodeDriver.CommandType.COMMAND_CONFIRM_REGEX,
                    'value': '^ok.*'
                },
                {
                    'type': GcodeDriver.CommandType.COMMAND_ERROR_REGEX,
                    'value': '^\!\>.*'
                },
                {
                    'type': GcodeDriver.CommandType.CONNECT_COMMAND,
                    'value': CONNECT_COMMAND_GCODE
                },
                {
                    'type': GcodeDriver.CommandType.ENABLE_COMMAND,
                    'value': 'M17'
                },
                {
                    'type': GcodeDriver.CommandType.DISABLE_COMMAND,
                    'value':
                    [
                        'M18',
                        'M107 P0',
                        'M107 P1',
                        'M107 P2',
                        'M107 P3',
                    ]
                },
                {
                    'type': GcodeDriver.CommandType.HOME_COMMAND,
                    'value':
                    [
                        '{Acceleration:M204 S%.2f ; Initialize acceleration}',
                        f'M914 X{X_HOMING_SENSITIVITY} Y{Y_HOMING_SENSITIVITY} ; Set Homing sensitivity',
                        'G28 ; Home all axes'
                    ]
                },
                {
                    'type': GcodeDriver.CommandType.SET_GLOBAL_OFFSETS_COMMAND,
                    'value': 'G92 {X:X%.4f} {Y:Y%.4f} ; reset coordinates'
                },
                {
                    'type': GcodeDriver.CommandType.GET_POSITION_COMMAND,
                    'value': 'M114 ; get position'
                },
                {
                    'type': GcodeDriver.CommandType.MOVE_TO_COMMAND,
                    'value':
                    [
                        '{Acceleration:M204 S%.2f ; Initialize acceleration}',
                        'G1 {X:X%.4f} {Y:Y%.4f} {Z:Z%.4f} {A:A%.4f} {B:B%.4f} {FeedRate:F%.2f} ; move to target'
                    ]
                },
                {
                    'type': GcodeDriver.CommandType.MOVE_TO_COMPLETE_COMMAND,
                    'value': 'M400 ; Wait for moves to complete before returning'
                },
                {
                    'type': GcodeDriver.CommandType.POSITION_REPORT_REGEX,
                    'value': '^.*.*'
                },
            ]
        },
    ]
elif CONTROL_BOARD_TYPE.lower() == 'winterbloom':
    BASE_GCODE_DRIVER_NAME = 'Starfish'
    HEAD_GCODE_DRIVER_NAME = 'Jellyfish'
    GCODE_DRIVERS = [
        {
            'name' : BASE_GCODE_DRIVER_NAME,
            'gcode': [
                {
                    'type': GcodeDriver.CommandType.COMMAND_CONFIRM_REGEX,
                    'value': '^ok.*'
                },
                {
                    'type': GcodeDriver.CommandType.COMMAND_ERROR_REGEX,
                    'value': '^\!\>.*'
                },
                {
                    'type': GcodeDriver.CommandType.CONNECT_COMMAND,
                    'value': [
                        'G21 ; Set millimeters mode'
                        'G90',
                    ]
                },
                {
                    'type': GcodeDriver.CommandType.ENABLE_COMMAND,
                    'value': 'M17'
                },
                {
                    'type': GcodeDriver.CommandType.DISABLE_COMMAND,
                    'value': 'M18'
                },
                {
                    'type': GcodeDriver.CommandType.HOME_COMMAND,
                    'value': [
                        '{Acceleration:M204 S%.2f ; Initialize acceleration}',
                        'G28 ; Home all axes'
                    ]
                },
                {
                    'type': GcodeDriver.CommandType.SET_GLOBAL_OFFSETS_COMMAND,
                    'value': 'G92 {X:X%.4f} {Y:Y%.4f} ; reset coordinates'
                },
                {
                    'type': GcodeDriver.CommandType.GET_POSITION_COMMAND,
                    'value': 'M114 ; get position'
                },
                {
                    'type': GcodeDriver.CommandType.MOVE_TO_COMMAND,
                    'value': [
                        '{Acceleration:M204 S%.2f ; Initialize acceleration}',
                        'G1 {X:X%.4f} {Y:Y%.4f} {FeedRate:F%.2f}; move to target'
                    ]
                },
                {
                    'type': GcodeDriver.CommandType.MOVE_TO_COMPLETE_COMMAND,
                    'value': 'M400 ; Wait for moves to complete before returning'
                },
                {
                    'type': GcodeDriver.CommandType.POSITION_REPORT_REGEX,
                    'value': '^.*.*'
                },
            ]
        },
        {
            'name' : HEAD_GCODE_DRIVER_NAME,
            'gcode': [
                {
                    'type': GcodeDriver.CommandType.COMMAND_CONFIRM_REGEX,
                    'value': '^ok.*'
                },
                {
                    'type': GcodeDriver.CommandType.COMMAND_ERROR_REGEX,
                    'value': '^\!\>.*'
                },
                {
                    'type': GcodeDriver.CommandType.CONNECT_COMMAND,
                    'value': [
                        'G21 ; Set millimeters mode'
                        'G90',
                    ]
                },
                {
                    'type': GcodeDriver.CommandType.ENABLE_COMMAND,
                    'value': 'M17'
                },
                {
                    'type': GcodeDriver.CommandType.DISABLE_COMMAND,
                    'value': 'M18'
                },
                {
                    'type': GcodeDriver.CommandType.HOME_COMMAND,
                    'value': [
                        '{Acceleration:M204 S%.2f ; Initialize acceleration}',
                        'G28 ; Home all axes'
                    ]
                },
                {
                    'type': GcodeDriver.CommandType.SET_GLOBAL_OFFSETS_COMMAND,
                    'value': 'G92 {Z:Z%.4f} {A:A%.4f} {B:B%.4f} ; reset coordinates'
                },
                {
                    'type': GcodeDriver.CommandType.GET_POSITION_COMMAND,
                    'value': 'M114 ; get position'
                },
                {
                    'type': GcodeDriver.CommandType.MOVE_TO_COMMAND,
                    'value': [
                        '{Acceleration:M204 S%.2f ; Initialize acceleration}',
                        'G1 {Z:Z%.4f} {A:A%.4f} {B:B%.4f} {FeedRate:F%.2f} ; move to target'
                    ]
                },
                {
                    'type': GcodeDriver.CommandType.MOVE_TO_COMPLETE_COMMAND,
                    'value': 'M400 ; Wait for moves to complete before returning'
                },
                {
                    'type': GcodeDriver.CommandType.POSITION_REPORT_REGEX,
                    'value': '^.*.*'
                },
            ]
        },
    ]
else:
    print('Unrecognized machine type: {}'.format(CONTROL_BOARD_TYPE))
    return

if WIDE_BODY_MOD:
    X_AXIS_LIMIT = 715
else:
    X_AXIS_LIMIT = 515

AXES = [
    {
        'name': 'x',
        'className': 'Controller',
        'type': Axis.Type.X,
        'gcodeDriver': BASE_GCODE_DRIVER_NAME,
        'softLimits': [ 0, X_AXIS_LIMIT ],
        'feedRate' : 250.0,
        'accelleration': 3000.0,
        'jerk': 10000.0
    },
    {
        'name': 'y',
        'className': 'Controller',
        'type': Axis.Type.Y,
        'gcodeDriver': BASE_GCODE_DRIVER_NAME,
        'softLimits': [ 0, 480 ],
        'feedRate' : 200.0,
        'accelleration': 3000.0,
        'jerk': 10000.0
    },
    {
        'name': 'z',
        'className': 'Controller',
        'type': Axis.Type.Z,
        'gcodeDriver': HEAD_GCODE_DRIVER_NAME,
        'softLimits': [ 0, 62 ],
        'safeZone': [ 30.5, 30.5 ],
        'feedRate' : 500.0,
        'accelleration': 300.0,
        'jerk': 0.0
    },
    {
        'name': 'a',
        'className': 'Controller',
        'type': Axis.Type.Rotation,
        'gcodeDriver': HEAD_GCODE_DRIVER_NAME,
        'softLimits': [ -180, 180 ],
        'feedRate' : 50000.0,
        'accelleration': 500.0,
        'jerk': 2000.0
    },
    {
        'name': 'b',
        'className': 'Controller',
        'type': Axis.Type.Rotation,
        'gcodeDriver': HEAD_GCODE_DRIVER_NAME,
        'softLimits': [ -180, 180 ],
        'feedRate' : 50000.0,
        'accelleration': 500.0,
        'jerk': 2000.0
    },
    {
        'name': 'Left Z',
        'className': 'Mapped',
        'type': Axis.Type.Z,
        'inputAxis': 'z',
        'mapping' : [30.5, 0, 31.5, 1]
    },
    {
        'name': 'Right Z',
        'className': 'Mapped',
        'type': Axis.Type.Z,
        'inputAxis': 'z',
        'mapping' : [30.5, 0, 29.5, 1]
    },
    {
        'name': 'Camera Z',
        'className': 'Virtual',
        'type': Axis.Type.Z,
    },
    {
        'name': 'Camera Rotation',
        'className': 'Virtual',
        'type': Axis.Type.Rotation,
    }
]

CAMERAS = [
    {
        'name' : 'Top Camera',
        'dir' : Camera.Looking.Down,
        'lightActuator': 'Top LED',
        'settleTime' : 300,
        'settleTimeout' : 120,
        'previewFPS' : 10,
        'deviceIndex' : TOP_CAMERA_OPENCV_INDEX
    },
    {
        'name' : 'Bottom Camera',
        'dir' : Camera.Looking.Up,
        'lightActuator': 'Bottom LED',
        'settleTime' : 80,
        'settleTimeout' : 120,
        'previewFPS' : 10,
        'deviceIndex' : BOTTOM_CAMERA_OPENCV_INDEX
    },
]

BOTTOM_LED_GCODE = 'M150 P{DoubleValue:%.0f} R255 U255 B255'
TOP_LED_GCODE = 'M150 P{DoubleValue:%.0f} R255 U255 B255'

if CONTROL_BOARD_TYPE.lower() == 'opulo':
    BOTTOM_LED_GCODE = 'M150 P{DoubleValue:%.0f} R255 U255 B255 S0'
    TOP_LED_GCODE = 'M150 P{DoubleValue:%.0f} R255 U255 B255 S1'

ACTUATORS = [
    {
        'name' : 'Bottom LED',
        'type' : Actuator.ActuatorValueType.Double,
        'defaults': [255.0, 0],
        'headMounted': False,
        'gcodeDriver' : BASE_GCODE_DRIVER_NAME,
        'enabled' : ReferenceActuator.MachineStateActuation.ActuateOff,
        'disabled' : ReferenceActuator.MachineStateActuation.ActuateOff,
        'homed' : ReferenceActuator.MachineStateActuation.ActuateOff,
        'gcode': [
            {
                'type': GcodeDriver.CommandType.ACTUATE_DOUBLE_COMMAND,
                'value': BOTTOM_LED_GCODE
            },
        ]
    },
    {
        'name' : 'Top LED',
        'type' : Actuator.ActuatorValueType.Double,
        'defaults': [255.0, 0],
        'headMounted': True,
        'gcodeDriver' : HEAD_GCODE_DRIVER_NAME,
        'enabled' : ReferenceActuator.MachineStateActuation.ActuateOff,
        'disabled' : ReferenceActuator.MachineStateActuation.ActuateOff,
        'homed' : ReferenceActuator.MachineStateActuation.ActuateOff,
        'gcode': [
            {
                'type': GcodeDriver.CommandType.ACTUATE_DOUBLE_COMMAND,
                'value': TOP_LED_GCODE
            },
        ]
    },
    {
        'name' : 'Left Nozzle Pump',
        'type' : Actuator.ActuatorValueType.Boolean,
        'defaults': [255.0, 0],
        'headMounted': False,
        'gcodeDriver' : BASE_GCODE_DRIVER_NAME,
        'enabled' : ReferenceActuator.MachineStateActuation.ActuateOff,
        'disabled' : ReferenceActuator.MachineStateActuation.ActuateOff,
        'homed' : ReferenceActuator.MachineStateActuation.ActuateOff,
        'gcode': [
            {
                'type': GcodeDriver.CommandType.ACTUATE_BOOLEAN_COMMAND,
                'value': 'M42 P0 S{True:1}{False:0} T1'
            },
        ]
    },
    {
        'name' : 'Left Nozzle Valve',
        'type' : Actuator.ActuatorValueType.Boolean,
        'defaults': [255.0, 0],
        'headMounted': True,
        'gcodeDriver' : BASE_GCODE_DRIVER_NAME,
        'enabled' : ReferenceActuator.MachineStateActuation.ActuateOff,
        'disabled' : ReferenceActuator.MachineStateActuation.ActuateOff,
        'homed' : ReferenceActuator.MachineStateActuation.ActuateOff,
        'gcode': [
            {
                'type': GcodeDriver.CommandType.ACTUATE_BOOLEAN_COMMAND,
                'value': 'M42 P2 S{True:1}{False:0} T1'
            },
        ]
    },
    {
        'name' : 'Left Nozzle Pump and Valve',
        'type' : Actuator.ActuatorValueType.Profile,
        'headMounted': True,
        'actuators': ['Left Nozzle Pump', 'Left Nozzle Valve'],
        'profiles' : [
            {
                'name': 'ON',
                'default': True,
                
            },
            {
                'name': 'OFF',
                'default': False,
            },
        ],
        'enabled' : ReferenceActuator.MachineStateActuation.ActuateOff,
        'disabled' : ReferenceActuator.MachineStateActuation.ActuateOff,
        'homed' : ReferenceActuator.MachineStateActuation.ActuateOff,
    },
    {
        'name' : 'Left Nozzle Vacuum Sense',
        'type' : Actuator.ActuatorValueType.Double,
        'defaults': [0, 0],
        'headMounted': True,
        'gcodeDriver' : BASE_GCODE_DRIVER_NAME,
        'enabled' : ReferenceActuator.MachineStateActuation.AssumeUnknown,
        'disabled' : ReferenceActuator.MachineStateActuation.LeaveAsIs,
        'homed' : ReferenceActuator.MachineStateActuation.LeaveAsIs,
        'gcode': [
            {
                'type': GcodeDriver.CommandType.ACTUATOR_READ_COMMAND,
                'value': 'M263 P0'
            },
            {
                'type': GcodeDriver.CommandType.ACTUATOR_READ_REGEX,
                'value': 'pressure:(?<Value>\d+)'
            },
        ]
    },
]

NOZZLES = [
    {
        'name' : 'Left Nozzle',
        'vacuumActuator' : 'Left Nozzle Pump and Valve',
        'vacuumSenseActuator' : 'Left Nozzle Vacuum Sense',
        'x' : 'x',
        'y' : 'y',
        'z' : 'Left Z',
        'rotation' : 'a'
    },
]

if USE_PHOTON_FEEDERS:
    READ_ACTUATOR_TEXT = 'M485 {value}'
    if CONTROL_BOARD_TYPE.lower() == 'winterbloom':
        READ_ACTUATOR_TEXT = 'M485 "{value}"'
    ACTUATORS.append(
    {
        'name' : 'PhotonFeederData',
        'type' : Actuator.ActuatorValueType.String,
        'headMounted': False,
        'gcodeDriver' : BASE_GCODE_DRIVER_NAME,
        'enabled' : ReferenceActuator.MachineStateActuation.LeaveAsIs,
        'disabled' : ReferenceActuator.MachineStateActuation.LeaveAsIs,
        'homed' : ReferenceActuator.MachineStateActuation.LeaveAsIs,
        'gcode': [
            {
                'type': GcodeDriver.CommandType.ACTUATOR_READ_COMMAND,
                'value': READ_ACTUATOR_TEXT
            },
            {
                'type': GcodeDriver.CommandType.ACTUATOR_READ_REGEX,
                'value': 'rs485-reply: (?<Value>.*)'
            },
        ]
    })

if DUAL_NOZZLE:
    ACTUATORS.append(
        {
            'name' : 'Right Nozzle Pump',
            'type' : Actuator.ActuatorValueType.Boolean,
            'defaults': [255.0, 0],
            'headMounted': True,
            'gcodeDriver' : BASE_GCODE_DRIVER_NAME,
            'enabled' : ReferenceActuator.MachineStateActuation.ActuateOff,
            'disabled' : ReferenceActuator.MachineStateActuation.ActuateOff,
            'homed' : ReferenceActuator.MachineStateActuation.ActuateOff,
            'gcode': [
                {
                    'type': GcodeDriver.CommandType.ACTUATE_BOOLEAN_COMMAND,
                    'value': 'M42 P1 S{True:1}{False:0} T1'
                },
            ]
        },
        {
            'name' : 'Right Nozzle Valve',
            'type' : Actuator.ActuatorValueType.Boolean,
            'defaults': [255.0, 0],
            'headMounted': True,
            'gcodeDriver' : BASE_GCODE_DRIVER_NAME,
            'enabled' : ReferenceActuator.MachineStateActuation.ActuateOff,
            'disabled' : ReferenceActuator.MachineStateActuation.ActuateOff,
            'homed' : ReferenceActuator.MachineStateActuation.ActuateOff,
            'gcode': [
                {
                    'type': GcodeDriver.CommandType.ACTUATE_BOOLEAN_COMMAND,
                    'value': 'M42 P3 S{True:1}{False:0} T1'
                },
            ]
        },
        {
            'name' : 'Right Nozzle Pump and Valve',
            'type' : Actuator.ActuatorValueType.Profile,
            'headMounted': True,
            'actuators': ['Right Nozzle Pump', 'Right Nozzle Valve'],
            'profiles' : [
                {
                    'name': 'ON',
                    'default': True,
                    
                },
                {
                    'name': 'OFF',
                    'default': False,
                }
            ],
            'enabled' : ReferenceActuator.MachineStateActuation.ActuateOff,
            'disabled' : ReferenceActuator.MachineStateActuation.ActuateOff,
            'homed' : ReferenceActuator.MachineStateActuation.ActuateOff,
        },
        {
            'name' : 'Right Nozzle Vacuum Sense',
            'type' : Actuator.ActuatorValueType.Double,
            'defaults': [0, 0],
            'headMounted': True,
            'gcodeDriver' : BASE_GCODE_DRIVER_NAME,
            'enabled' : ReferenceActuator.MachineStateActuation.AssumeUnknown,
            'disabled' : ReferenceActuator.MachineStateActuation.LeaveAsIs,
            'homed' : ReferenceActuator.MachineStateActuation.LeaveAsIs,
            'gcode': [
                {
                    'type': GcodeDriver.CommandType.ACTUATOR_READ_COMMAND,
                    'value': 'M263 P1'
                },
                {
                    'type': GcodeDriver.CommandType.ACTUATOR_READ_REGEX,
                    'value': 'pressure:(?<Value>\d+)'
                },
            ]
        }
    )
    NOZZLES.append(
        {
            'name' : 'Right Nozzle',
            'vacuumActuator' : 'Right Nozzle Pump and Valve',
            'vacuumSenseActuator' : 'Right Nozzle Vacuum Sense',
            'x' : 'x',
            'y' : 'y',
            'z' : 'Right Z',
            'rotation' : 'b'
        }
    )

NOZZLE_TIPS = [ 'N045', 'N08', 'N14', 'N24', 'N48', 'N75' ]

def find_or_create_camera(metadata):
    cam = find_camera_by_name(metadata['name'])
    if cam:
        return cam
    if USE_OPENCV_CAMERAS:
        cam = OpenCvCamera()
        cam.setDeviceIndex(metadata['deviceIndex'])
        for prop in cam.getProperties():
            if prop.property == OpenCvCamera.OpenCvCaptureProperty.CAP_PROP_FOURCC:
                prop.value = 1.196444237E9
    else:
        cam = OpenPnpCaptureCamera()
    cam.setName(metadata['name'])
    cam.setLooking(metadata['dir'])
    cam.setSettleTimeMs(metadata['settleTime'])
    cam.setSettleTimeoutMs(metadata['settleTimeout'])
    cam.setPreviewFps(metadata['previewFPS'])
    if metadata['dir'] == Camera.Looking.Down:
        cam.setAxisX(find_axis_by_name('x'))
        cam.setAxisY(find_axis_by_name('y'))
        cam.setAxisZ(find_axis_by_name('Camera Z'))
        cam.setAxisRotation(find_axis_by_name('Camera Rotation'))
        cam.setLightActuator(find_actuator_by_name(metadata['lightActuator'], machine.getDefaultHead()))
        machine.getDefaultHead().addCamera(cam)
    else:
        cam.setLightActuator(find_actuator_by_name(metadata['lightActuator']))
        machine.addCamera(cam)
    gui.getCameraViews().addCamera(cam)

def find_camera_by_name(name):
    for cam in machine.getCameras():
        if cam.getName().lower() == name.lower():
            return cam
    return None

def find_or_create_axis(metadata):
    axis = find_axis_by_name(metadata['name'])
    if axis:
        return axis
    if metadata['className'] == 'Controller':
        print('Creating Axis \'{}\' as \'ReferenceControllerAxis\''.format(metadata['name']))
        axis = ReferenceControllerAxis()
        axis.setDriver(find_gcode_driver(metadata['gcodeDriver']))
        if metadata['type'] == Axis.Type.Rotation:
            axis.setLimitRotation(True)
            axis.setWrapAroundRotation(True)
        if metadata.has_key('safeZone'):
            print('Setting Safe Zone limits: {} -> {}'.format(metadata['safeZone'][0], metadata['safeZone'][1]))
            axis.setSafeZoneLow(Length(metadata['safeZone'][0], LengthUnit.Millimeters))
            axis.setSafeZoneLowEnabled(True)
            axis.setSafeZoneHigh(Length(metadata['safeZone'][1], LengthUnit.Millimeters))
            axis.setSafeZoneHighEnabled(True)
        if metadata.has_key('softLimits'):
            print('Setting Soft limits: {} -> {}'.format(metadata['softLimits'][0], metadata['softLimits'][1]))
            axis.setSoftLimitLow(Length(metadata['softLimits'][0], LengthUnit.Millimeters))
            axis.setSoftLimitLowEnabled(True)
            axis.setSoftLimitHigh(Length(metadata['softLimits'][1], LengthUnit.Millimeters))
            axis.setSoftLimitHighEnabled(True)
        axis.setFeedratePerSecond(Length(metadata['feedRate'], LengthUnit.Millimeters))
        axis.setAccelerationPerSecond2(Length(metadata['accelleration'], LengthUnit.Millimeters))
        axis.setJerkPerSecond3(Length(metadata['jerk'], LengthUnit.Millimeters))
        print('Setting Controller Axis Letter to {}'.format(metadata['name'].upper()))
        axis.setLetter(metadata['name'].upper())
    elif metadata['className'] == 'Virtual':
        print('Creating Axis \'{}\' as \'ReferenceVirtualAxis\''.format(metadata['name']))
        axis = ReferenceVirtualAxis()
    elif metadata['className'] == 'Mapped':
        print('Creating Axis \'{}\' as \'ReferenceMappedAxis\''.format(metadata['name']))
        axis = ReferenceMappedAxis()
        axisTarget = find_axis_by_name(metadata['inputAxis'])
        print('Mapping to Axis {}'.format(axisTarget))
        print('Mapping parameters: {}:{} -> {}:{}'.format(metadata['mapping'][0], metadata['mapping'][1], metadata['mapping'][2], metadata['mapping'][3]))
        axis.setInputAxis(axisTarget)
        axis.setMapInput0(Length(metadata['mapping'][0], LengthUnit.Millimeters))
        axis.setMapInput1(Length(metadata['mapping'][1], LengthUnit.Millimeters))
        axis.setMapOutput0(Length(metadata['mapping'][2], LengthUnit.Millimeters))
        axis.setMapOutput1(Length(metadata['mapping'][3], LengthUnit.Millimeters))
    axis.setName(metadata['name'])
    axis.setType(metadata['type'])
    machine.addAxis(axis)
    return axis

def find_axis_by_name(name):
    for ax in machine.getAxes():
        if ax.getName().lower() == name.lower():
            return ax
    return None

def find_or_create_nozzle(name, head):
    nozzle = head.getNozzleByName(name)
    if nozzle:
        print('Found Nozzle \'{}\' on head \'{}\''.format(nozzle.getName(), head.getName()))
        return nozzle
    print('Creating Nozzle \'{}\' on head \'{}\''.format(name, head.getName()))
    nozzle = ReferenceNozzle()
    nozzle.setName(name)
    nozzle.setAligningRotationMode(True)
    head.addNozzle(nozzle)
    return nozzle

def find_or_create_nozzle_tip(name):
    nozzleTip = machine.getNozzleTipByName(name)
    if nozzleTip:
        return nozzleTip
    print('Creating NozzleTip \'{}\''.format(name))
    nozzleTip = ReferenceNozzleTip()
    nozzleTip.setName(name)
    machine.addNozzleTip(nozzleTip)
    return nozzleTip

def find_actuator_by_name(name, head = None):
    if head:
        for act in head.getActuators():
            if act.getName().lower() == name.lower():
                return act
    else:
        for act in machine.getActuators():
            if act.getName().lower() == name.lower():
                return act
    return None

def find_or_create_gcode_driver(driver_name):
    driver = find_gcode_driver(driver_name)
    if driver:
        return driver
    print('Creating GCode driver \'{}\''.format(driver_name))
    driver = GcodeDriver()
    driver.setName(driver_name)
    driver.setTimeoutMilliseconds(30000)
    driver.setFlowControl(SerialPortCommunications.FlowControl.RtsCts)
    driver.setMotionControlType(Driver.MotionControlType.Full3rdOrderControl)
    driver.setMaxFeedRate(0)
    machine.addDriver(driver)
    return driver

def find_gcode_driver(driver_name):
    for driver in machine.getDrivers():
        if driver.getName().lower() == driver_name.lower():
            return driver
    return None

def remove_all_gcode_drivers():
    config = Configuration.get()
    driversToRemove = []
    for driver in machine.getDrivers():
        driversToRemove.append(driver)
    for driver in driversToRemove:
        print('Removing Driver \'{}\''.format(driver.getName()))
        try:
            machine.removeDriver(driver)
        except:
            pass
    config.save()

def remove_all_cameras():
    config = Configuration.get()
    camerasToRemove = []
    for cam in machine.getCameras():
        camerasToRemove.append(cam)
    for cam in camerasToRemove:
        print('Removing Camera \'{}\''.format(cam.getName()))
        try:
            machine.removeCamera(cam)
            gui.getCameraViews().removeCamera(cam)
        except:
            pass
    config.save()

def remove_all_actuators():
    config = Configuration.get()
    actuatorsToRemove = []
    for act in machine.getActuators():
        actuatorsToRemove.append(act)
    for act in actuatorsToRemove:
        print('Removing Actuator \'{}\''.format(act.getName()))
        try:
            machine.removeActuator(act)
        except:
            pass
    config.save()

def remove_all_axes():
    config = Configuration.get()
    axesToRemove = []
    for axis in machine.getAxes():
        axesToRemove.append(axis)
    for axis in axesToRemove:
        print('Removing Axis \'{}\''.format(axis.getName()))
        try:
            machine.removeAxis(axis)
        except:
            pass
    config.save()

def remove_all_nozzle_tips():
    config = Configuration.get()
    nozzleTipsToRemove = []
    for ent in machine.getNozzleTips():
        nozzleTipsToRemove.append(ent)
    for tip in nozzleTipsToRemove:
        print('Removing NozzleTip \'{}\''.format(tip.getName()))
        try:
            machine.removeNozzleTip(tip)
        except:
            pass
    config.save()

def remove_head_mounted_nozzles():
    nozzlesToRemove = []
    for nozzle in machine.getDefaultHead().getNozzles():
        nozzlesToRemove.append(nozzle)
    for nozzle in nozzlesToRemove:
        print('Removing Nozzle \'{}\' from head \'{}\''.format(nozzle.getName(), machine.getDefaultHead().getName()))
        try:
            machine.getDefaultHead().removeNozzle(nozzle)
        except:
            pass

def remove_head_mounted_cameras():
    config = Configuration.get()
    camerasToRemove = []
    for cam in machine.getDefaultHead().getCameras():
        camerasToRemove.append(cam)
    for cam in camerasToRemove:
        print('Removing Camera \'{}\' from head \'{}\''.format(cam.getName(), machine.getDefaultHead().getName()))
        try:
            gui.getCameraViews().removeCamera(cam)
            machine.getDefaultHead().removeCamera(cam)
        except:
            pass
    config.save()

def remove_head_mounted_actuators():
    config = Configuration.get()
    actuatorsToRemove = []
    for act in machine.getDefaultHead().getActuators():
        actuatorsToRemove.append(act)
    for act in actuatorsToRemove:
        print('Removing Actuator \'{}\' from head \'{}\''.format(act.getName(), machine.getDefaultHead().getName()))
        try:
            machine.getDefaultHead().removeActuator(act)
        except:
            pass
    config.save()

def remove_all_feeders():
    config = Configuration.get()
    feedersToRemove = []
    for feeder in machine.getFeeders():
        feedersToRemove.append(feeder)
    for feeder in feedersToRemove:
        print('Removing Feeder \'{}\''.format(feeder.getName()))
        try:
            machine.removeFeeder(feeder)
        except:
            pass
    config.save()

def create_new_gcode_drivers():
    config = Configuration.get()
    for driver in GCODE_DRIVERS:
        find_or_create_gcode_driver(driver['name'])
    config.save()

def configure_gcode_drivers():
    config = Configuration.get()
    for ent in GCODE_DRIVERS:
        driver = find_gcode_driver(ent['name'])
        for gcode in ent['gcode']:
            gcodeValue = ''
            if isinstance(gcode['value'], list):
                gcodeValue = '\n'.join(gcode['value'])
            else:
                gcodeValue = gcode['value']
            driver.setCommand(None, gcode['type'], gcodeValue)
    for ent in ACTUATORS:
        if ent.has_key('gcode'):
            if ent['headMounted']:
                actuator = find_actuator_by_name(ent['name'], machine.getDefaultHead())
            else:
                actuator = find_actuator_by_name(ent['name'])
            driver = find_gcode_driver(ent['gcodeDriver'])
            for gcode in ent['gcode']:
                gcodeValue = ''
                if isinstance(gcode['value'], list):
                    gcodeValue = '\n'.join(gcode['value'])
                else:
                    gcodeValue = gcode['value']
                driver.setCommand(actuator, gcode['type'], gcodeValue)
    config.save()

def create_new_axes():
    config = Configuration.get()
    for axis in AXES:
        find_or_create_axis(axis)
    config.save()

def create_new_cameras():
    config = Configuration.get()
    for camera in CAMERAS:
        find_or_create_camera(camera)
    config.save()

def create_new_actuators():
    config = Configuration.get()
    for ent in ACTUATORS:
        if ent['headMounted']:
            act = find_actuator_by_name(ent['name'], machine.getDefaultHead())
            if act is None:
                act = ReferenceActuator()
                machine.getDefaultHead().addActuator(act)
        else:
            act = find_actuator_by_name(ent['name'])
            if act is None:
                act = ReferenceActuator()
                machine.addActuator(act)
        act.setName(ent['name'])
        act.setValueType(ent['type'])
        if ent['type'] != Actuator.ActuatorValueType.Profile:
            act.setDriver(find_gcode_driver(ent['gcodeDriver']))
        else:
            profiles = act.getActuatorProfiles()
            profiles.setActuator1(find_actuator_by_name(ent['actuators'][0]))
            profiles.setActuator2(find_actuator_by_name(ent['actuators'][1]))
            for profileConfig in ent['profiles']:
                prof = ReferenceActuatorProfiles.Profile()
                prof.setName(profileConfig['name'])
                if profileConfig['default']:
                    prof.setDefaultOn(True)
                    prof.setDefaultOff(False)
                    prof.setValue1(True)
                    prof.setValue2(True)
                else:
                    prof.setDefaultOn(False)
                    prof.setDefaultOff(True)
                profiles.add(prof)
        act.setDisabledActuation(ent['disabled'])
        act.setEnabledActuation(ent['enabled'])
        act.setHomedActuation(ent['homed'])
    config.save()

def create_new_nozzles():
    config = Configuration.get()
    machineHead = machine.getDefaultHead()
    for ent in NOZZLES:
        nozzle = find_or_create_nozzle(ent['name'], machineHead)
        for tip in NOZZLE_TIPS:
            nozzle.addCompatibleNozzleTip(find_or_create_nozzle_tip(tip))
        nozzle.setVacuumActuator(find_actuator_by_name(ent['vacuumActuator'], machineHead))
        nozzle.setVacuumSenseActuator(find_actuator_by_name(ent['vacuumSenseActuator'], machineHead))
        nozzle.setAxisX(find_axis_by_name(ent['x']))
        nozzle.setAxisY(find_axis_by_name(ent['y']))
        nozzle.setAxisZ(find_axis_by_name(ent['z']))
        nozzle.setAxisRotation(find_axis_by_name(ent['rotation']))
    config.save()

def create_nozzle_tips():
    config = Configuration.get()
    for tip in NOZZLE_TIPS:
        find_or_create_nozzle_tip(tip)
    config.save()

print('Removing existing configuration settings')

remove_all_cameras()
remove_all_actuators()
remove_all_axes()
remove_all_nozzle_tips()
remove_head_mounted_cameras()
remove_head_mounted_actuators()
remove_all_gcode_drivers()
if CLEANUP_EXISTING_FEEDERS:
    remove_all_feeders()

# removing nozzles will not save config and must be last entry
remove_head_mounted_nozzles()

print('Creating new configuration settings')
create_new_gcode_drivers()
create_nozzle_tips()
create_new_actuators()
create_new_axes()
create_new_cameras()
create_new_nozzles()
configure_gcode_drivers()

solutions = machine.getSolutions()
limit = 10
while solutions.getIssues().size() == 0 and limit > 0:
    limit = limit - 1
    print('Waiting for Issues & Solutions initial fill')
    solutions.findIssues()
    solutions.publishIssues()
    time.sleep(1)

autoSolveIssueSubjectText = [
   'Milestone Welcome',
   'Milestone Connect',
   'Milestone Basics',
]
autoDismissIssueText = [
    'pump control actuator',
    'MOVE_TO_COMMAND',
    'velocity limited'
]
autoSolveDescriptionText = [
    'Assume a generic G-code'
]
autoExitIssueSubjectText = 'Milestone Kinematics'

print('Cleaning up Issues & Solutions')
keepGoing = True
while keepGoing and solutions.getIssues().size() > 0:
    solutions.findIssues()
    solutions.publishIssues()
    for issue in solutions.getIssues():
        print('Issue: {}'.format(issue.getSubject().getSubjectText()))
        if issue.getSubject().getSubjectText() in autoSolveIssueSubjectText:
            issue.setState(Solutions.State.Solved)
        elif issue.getSubject().getSubjectText() == autoExitIssueSubjectText:
            keepGoing = False
        elif 'ReferenceHead' in issue.getSubject().getSubjectText():
            issue.setState(Solutions.State.Dismissed)
        elif 'GcodeDriver' in issue.getSubject().getSubjectText():
            dismissed = False
            for text in autoDismissIssueText:
                if text in issue.getIssue():
                    issue.setState(Solutions.State.Dismissed)
                    dismissed = True
            if not dismissed:
                for choice in issue.getChoices():
                    for text in autoSolveDescriptionText:
                        if text in choice.getDescription():
                            issue.setChoice(choice.getValue())
                            issue.setState(Solutions.State.Solved)
