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

# X_AXIS_LIMIT controls the X axis limits, in the default case the limits are
# based on the 600mm extrusion used in the default Lumen configuration. When
# the machine has been modified with the Wide Body mod the X extrusion is
# increased to 800mm providing access for both the left and right nozzles to
# reach the full width of the staging plate(s) and feeders on front and rear
# rails.
#
# For Wide Body this should be 715, for normal this should be 433.
X_AXIS_LIMIT = 715

# Y_AXIS_LIMIT controls the Y axis limits, in the default case the limits are
# based on the 600mm extrusion used in the default Lumen configuration.
Y_AXIS_LIMIT = 487

# Z_AXIS_LIMIT controls the Z axis limits, in the default case the limits are
# based on the 100mm linear rail used in the default Lumen configuration.
#
# Since the Z axis is configured as inverted for Left / Right the limit is
# reduced to 62 with ~31mm total motion for left and right each.
Z_AXIS_LIMIT = 62

# USE_OPENCV_CAMERAS switches the camera capture type from OpenPnPCaptureCamera
# to OpenCVCamera.
USE_OPENCV_CAMERAS = False

# X_HOMING_SENSITIVITY and Y_HOMING_SENSITIVITY configure the sensitivity of
# sensorless homing.
X_HOMING_SENSITIVITY = 100
Y_HOMING_SENSITIVITY = 150

# TOP_CAMERA_OPENCV_INDEX and BOTTOM_CAMERA_OPENCV_INDEX are the v4l2-ctl
# device numbers to use when USE_OPENCV_CAMERAS is set to True
TOP_CAMERA_OPENCV_INDEX = 0
BOTTOM_CAMERA_OPENCV_INDEX = 2

######## END OF USER MODIFYABLE SETTINGS ########

if CONTROL_BOARD_TYPE.lower() == 'opulo':
    BASE_GCODE_DRIVER_NAME = 'Lumen'
    HEAD_GCODE_DRIVER_NAME = 'Lumen'

    LEFT_NOZZLE_PUMP_GCODE = '{True:M106 P2 S255}{False:M107 P2}'
    LEFT_NOZZLE_SOLENOID_GCODE = '{True:M106 P3 S255}{False:M107 P3}'
    LEFT_NOZZLE_VAC_READ_GCODE =
    [
        'M260 A112 B1 S1 ; Select vac1 through multiplexer',
        'M260 A109 B6 S1 ; Selects MSB register',
        'M261 A109 B1 S2 ; Request one byte back via decimal'
    ]

    RIGHT_NOZZLE_PUMP_GCODE = '{True:M106 P0 S255}{False:M107 P0}'
    RIGHT_NOZZLE_SOLENOID_GCODE = '{True:M106 P1 S255}{False:M107 P1}'
    RIGHT_NOZZLE_VAC_READ_GCODE =
    [
        'M260 A112 B2 S1 ; Select vac1 through multiplexer',
        'M260 A109 B6 S1 ; Selects MSB register',
        'M261 A109 B2 S2 ; Request one byte back via decimal'
    ]

    VAC_SENSE_REGEX = '.*data:(?<Value>.*)'

    READ_ACTUATOR_TEXT = 'M485 {value}'

    BOTTOM_LED_GCODE = 'M150 P{DoubleValue:%.0f} R255 U255 B255 S0'
    TOP_LED_GCODE = 'M150 P{DoubleValue:%.0f} R255 U255 B255 S1'

    MAX_ACCELERATION_RATE = 5000.0

    X_ACCELERATION_RATE = 5000.0
    X_MOTOR_CURRENT = 1200
    X_FEED_RATE = 1000.0
    X_JERK_RATE = 10000.0

    Y_ACCELERATION_RATE = 3500.0
    Y_MOTOR_CURRENT = 1200
    Y_FEED_RATE = 1000.0
    Y_JERK_RATE = 10000.0

    NOZZLE_MOTOR_CURRENT = 200
    NOZZLE_ACCELERATION_RATE = 500.0
    NOZZLE_FEED_RATE = 50000.0
    NOZZLE_JERK_RATE = 2000.0

    GCODE_DRIVERS =
    [
        # Main Board
        {
            'name' : BASE_GCODE_DRIVER_NAME,
            'gcode': [
                # COMMAND_CONFIRM_REGEX
                {
                    'type': GcodeDriver.CommandType.COMMAND_CONFIRM_REGEX,
                    'value': '^ok.*'
                },
                # COMMAND_ERROR_REGEX
                {
                    'type': GcodeDriver.CommandType.COMMAND_ERROR_REGEX,
                    'value': '^\!\>.*'
                },
                # CONNECT_COMMAND
                {
                    'type': GcodeDriver.CommandType.CONNECT_COMMAND,
                    'value':
                    [
                        'G90 ; Set absolute positioning mode',
                        'M260 A112 B1 S1 ; Selecting VAC1 through the I2C multiplexer',
                        'M260 A109 ; Starts Command to VAC sensor at address 109',
                        'M260 B48 ; Address Byte 48 selects CMD register',
                        'M260 B27 ; Sends byte to select 62.5 sleep time, SCO, sleep mode conversion (0001 1 011)',
                        'M260 S1 ; Sends data',
                        'M260 A112 B2 S1 ; Selecting VAC2 through the I2C multiplexer',
                        'M260 A109 ; Starts Command to VAC sensor at address 109',
                        'M260 B48 ; Address Byte 48 selects CMD register',
                        'M260 B27 ; Sends byte to select 62.5 sleep time, SCO, sleep mode conversion (0001 1 011)',
                        'M260 S1 ; Sends data',
                        'M569 S0 X Y ; Switch from stealthChop to spreadCycle',
                    ]
                },
                # ENABLE_COMMAND
                {
                    'type': GcodeDriver.CommandType.ENABLE_COMMAND,
                    'value': 'M17'
                },
                # DISABLE_COMMAND
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
                # HOME_COMMAND
                {
                    'type': GcodeDriver.CommandType.HOME_COMMAND,
                    'value':
                    [
                        'M204 T2000 ; Sets acceleration for homing',
                        f'M914 X{X_HOMING_SENSITIVITY} Y{Y_HOMING_SENSITIVITY} ; Set Homing sensitivity',
                        'G28 ; Home all axes'
                    ]
                },
                # SET_GLOBAL_OFFSETS_COMMAND
                {
                    'type': GcodeDriver.CommandType.SET_GLOBAL_OFFSETS_COMMAND,
                    'value': 'G92 {X:X%.4f} {Y:Y%.4f} {Z:Z%.4f} {A:A%.4f} {B:B%.4f} ; reset coordinates'
                },
                # GET_POSITION_COMMAND
                {
                    'type': GcodeDriver.CommandType.GET_POSITION_COMMAND,
                    'value': 'M114 ; get position'
                },
                # MOVE_TO_COMMAND
                {
                    'type': GcodeDriver.CommandType.MOVE_TO_COMMAND,
                    'value':
                    [
                        '{Acceleration:M204 S%.2f ; Initialize acceleration}',
                        'G0 {X:X%.4f} {Y:Y%.4f} {Z:Z%.4f} {A:A%.4f} {B:B%.4f} F{FeedRate:%.0f} ; Send standard Gcode move',
                    ]
                },
                # MOVE_TO_COMPLETE_COMMAND
                {
                    'type': GcodeDriver.CommandType.MOVE_TO_COMPLETE_COMMAND,
                    'value': 'M400 ; Wait for moves to complete before returning'
                },
                # POSITION_REPORT_REGEX
                {
                    'type': GcodeDriver.CommandType.POSITION_REPORT_REGEX,
                    'value': '^.*X:(?<X>-?\d+\.\d+) Y:(?<Y>-?\d+\.\d+) Z:(?<Z>-?\d+\.\d+) A:(?<A>-?\d+\.\d+) B:(?<B>-?\d+\.\d+).*'
                },
            ]
        },
    ]

elif CONTROL_BOARD_TYPE.lower() == 'winterbloom':
    BASE_GCODE_DRIVER_NAME = 'Starfish'
    HEAD_GCODE_DRIVER_NAME = 'Jellyfish'

    LEFT_NOZZLE_PUMP_GCODE = 'M42 P0 S{True:1}{False:0} T1'
    LEFT_NOZZLE_SOLENOID_GCODE = 'M42 P2 S{True:1}{False:0} T1'
    LEFT_NOZZLE_VAC_READ_GCODE = 'M263 P0'

    RIGHT_NOZZLE_PUMP_GCODE = 'M42 P1 S{True:1}{False:0} T1'
    RIGHT_NOZZLE_SOLENOID_GCODE = 'M42 P3 S{True:1}{False:0} T1'
    RIGHT_NOZZLE_VAC_READ_GCODE = 'M263 P1'

    VAC_SENSE_REGEX = '.*pressure:(?<Value>\d+).*'

    READ_ACTUATOR_TEXT = 'M485 "{value}"'

    BOTTOM_LED_GCODE = 'M150 P{DoubleValue:%.0f} R255 U255 B255'
    TOP_LED_GCODE = 'M150 P{DoubleValue:%.0f} R255 U255 B255'

    MAX_ACCELERATION_RATE = 5000.0

    X_ACCELERATION_RATE = 2000.0
    X_MOTOR_CURRENT = 1000
    X_FEED_RATE = 1000.0
    X_JERK_RATE = 10000.0

    Y_ACCELERATION_RATE = 2000.0
    Y_MOTOR_CURRENT = 1000
    Y_FEED_RATE = 1000.0
    Y_JERK_RATE = 10000.0

    NOZZLE_MOTOR_CURRENT = 200
    NOZZLE_ACCELERATION_RATE = 500.0
    NOZZLE_FEED_RATE = 50000.0
    NOZZLE_JERK_RATE = 2000.0

    GCODE_DRIVERS =
    [
        # Starfish
        {
            'name' : BASE_GCODE_DRIVER_NAME,
            'gcode':
            [
                # COMMAND_CONFIRM_REGEX
                {
                    'type': GcodeDriver.CommandType.COMMAND_CONFIRM_REGEX,
                    'value': '^ok.*'
                },
                # COMMAND_ERROR_REGEX
                {
                    'type': GcodeDriver.CommandType.COMMAND_ERROR_REGEX,
                    'value': '^\!\>.*'
                },
                # CONNECT_COMMAND
                {
                    'type': GcodeDriver.CommandType.CONNECT_COMMAND,
                    'value': [
                        f'M914 X{X_HOMING_SENSITIVITY} Y{Y_HOMING_SENSITIVITY} ; Set Homing sensitivity',
                        'G90',
                    ]
                },
                # ENABLE_COMMAND
                {
                    'type': GcodeDriver.CommandType.ENABLE_COMMAND,
                    'value': 'M17'
                },
                # DISABLE_COMMAND
                {
                    'type': GcodeDriver.CommandType.DISABLE_COMMAND,
                    'value': 'M18'
                },
                # HOME_COMMAND
                {
                    'type': GcodeDriver.CommandType.HOME_COMMAND,
                    'value': [
                        #'{Acceleration:M204 S%.2f ; Initialize acceleration}',
                        #f'M914 X{X_HOMING_SENSITIVITY} Y{Y_HOMING_SENSITIVITY} ; Set Homing sensitivity',
                        'G28 X Y ; Home all axes'
                    ]
                },
                # SET_GLOBAL_OFFSETS_COMMAND
                {
                    'type': GcodeDriver.CommandType.SET_GLOBAL_OFFSETS_COMMAND,
                    'value': 'G92 {X:X%.4f} {Y:Y%.4f} ; reset coordinates'
                },
                # GET_POSITION_COMMAND
                {
                    'type': GcodeDriver.CommandType.GET_POSITION_COMMAND,
                    'value': 'M114 ; get position'
                },
                # MOVE_TO_COMMAND
                {
                    'type': GcodeDriver.CommandType.MOVE_TO_COMMAND,
                    'value': [
                        '{Acceleration:M204 S%.2f ; Initialize acceleration}',
                        'G1 {X:X%.4f} {Y:Y%.4f} {FeedRate:F%.2f}; move to target'
                    ]
                },
                # MOVE_TO_COMPLETE_COMMAND
                {
                    'type': GcodeDriver.CommandType.MOVE_TO_COMPLETE_COMMAND,
                    'value': 'M400 ; Wait for moves to complete before returning'
                },
                # POSITION_REPORT_REGEX
                {
                    'type': GcodeDriver.CommandType.POSITION_REPORT_REGEX,
                    'value': '^.*X:(?<X>-?\d+\.\d+) Y:(?<Y>-?\d+\.\d+).*'
                },
            ]
        },
        # Jellyfish
        {
            'name' : HEAD_GCODE_DRIVER_NAME,
            'gcode':
            [
                # COMMAND_CONFIRM_REGEX
                {
                    'type': GcodeDriver.CommandType.COMMAND_CONFIRM_REGEX,
                    'value': '^ok.*'
                },
                # COMMAND_ERROR_REGEX
                {
                    'type': GcodeDriver.CommandType.COMMAND_ERROR_REGEX,
                    'value': '^\!\>.*'
                },
                # CONNECT_COMMAND
                {
                    'type': GcodeDriver.CommandType.CONNECT_COMMAND,
                    'value':
                    [
                        'G90',
                    ]
                },
                # ENABLE_COMMAND
                {
                    'type': GcodeDriver.CommandType.ENABLE_COMMAND,
                    'value': 'M17'
                },
                # DISABLE_COMMAND
                {
                    'type': GcodeDriver.CommandType.DISABLE_COMMAND,
                    'value': 'M18'
                },
                # HOME_COMMAND
                {
                    'type': GcodeDriver.CommandType.HOME_COMMAND,
                    'value': [
                        '{Acceleration:M204 S%.2f ; Initialize acceleration}',
                        'G28 Z A B ; Home all axes'
                    ]
                },
                # SET_GLOBAL_OFFSETS_COMMAND
                {
                    'type': GcodeDriver.CommandType.SET_GLOBAL_OFFSETS_COMMAND,
                    'value': 'G92 {Z:Z%.4f} {A:A%.4f} {B:B%.4f} ; reset coordinates'
                },
                # GET_POSITION_COMMAND
                {
                    'type': GcodeDriver.CommandType.GET_POSITION_COMMAND,
                    'value': 'M114 ; get position'
                },
                # MOVE_TO_COMMAND
                {
                    'type': GcodeDriver.CommandType.MOVE_TO_COMMAND,
                    'value':
                    [
                        '{Acceleration:M204 S%.2f ; Initialize acceleration}',
                        'G1 {Z:Z%.4f} {A:A%.4f} {B:B%.4f} {FeedRate:F%.2f} ; move to target'
                    ]
                },
                # MOVE_TO_COMPLETE_COMMAND
                {
                    'type': GcodeDriver.CommandType.MOVE_TO_COMPLETE_COMMAND,
                    'value': 'M400 ; Wait for moves to complete before returning'
                },
                # POSITION_REPORT_REGEX
                {
                    'type': GcodeDriver.CommandType.POSITION_REPORT_REGEX,
                    'value': '^.*Z:(?<Z>-?\d+\.\d+) A:(?<A>-?\d+\.\d+) B:(?<B>-?\d+\.\d+).*'
                },
            ]
        },
    ]
else:
    print('Unrecognized machine type: {}'.format(CONTROL_BOARD_TYPE))
    return

AXES =
[
    # X Axis
    {
        'name': Axis.Type.X.getDefaultLetter(),
        'className': 'Controller',
        'type': Axis.Type.X,
        'gcodeDriver': BASE_GCODE_DRIVER_NAME,
        'softLimits': [ 0, X_AXIS_LIMIT ],
        'feedRate' : X_FEED_RATE,
        'accelleration': X_ACCELERATION_RATE,
        'jerk': X_JERK_RATE
    },
    # Y Axis
    {
        'name': Axis.Type.Y.getDefaultLetter(),
        'className': 'Controller',
        'type': Axis.Type.Y,
        'gcodeDriver': BASE_GCODE_DRIVER_NAME,
        'softLimits': [ 0, Y_AXIS_LIMIT ],
        'feedRate' : Y_FEED_RATE,
        'accelleration': Y_ACCELERATION_RATE,
        'jerk': Y_JERK_RATE
    },
    # Z Axis
    {
        'name': Axis.Type.Z.getDefaultLetter(),
        'className': 'Controller',
        'type': Axis.Type.Z,
        'gcodeDriver': HEAD_GCODE_DRIVER_NAME,
        'softLimits': [ 0, Z_AXIS_LIMIT ],
        'safeZone': [ ((Z_AXIS_LIMIT - 1) / 2), ((Z_AXIS_LIMIT - 1) / 2) ],
        'feedRate' : 500.0,
        'accelleration': 300.0,
        'jerk': 0.0
    },
    # Left Nozzle Axis (A)
    {
        'name': 'A',
        'className': 'Controller',
        'type': Axis.Type.Rotation,
        'gcodeDriver': HEAD_GCODE_DRIVER_NAME,
        'softLimits': [ -200, 200 ],
        'feedRate' : NOZZLE_FEED_RATE,
        'accelleration': NOZZLE_ACCELERATION_RATE,
        'jerk': NOZZLE_JERK_RATE
    },
    # Right Nozzle Axis (B)
    {
        'name': 'B',
        'className': 'Controller',
        'type': Axis.Type.Rotation,
        'gcodeDriver': HEAD_GCODE_DRIVER_NAME,
        'softLimits': [ -200, 200 ],
        'feedRate' : NOZZLE_FEED_RATE,
        'accelleration': NOZZLE_ACCELERATION_RATE,
        'jerk': NOZZLE_JERK_RATE
    },
    # Left Nozzle Mapped Axis
    {
        'name': 'Left Z',
        'className': 'Mapped',
        'type': Axis.Type.Z,
        'inputAxis': Axis.Type.Z.getDefaultLetter(),
        'mapping' : [((Z_AXIS_LIMIT - 1) / 2) -1, 0, ((Z_AXIS_LIMIT - 1) / 2), 1]
    },
    # Right Nozzle Mapped Axis
    {
        'name': 'Right Z',
        'className': 'Mapped',
        'type': Axis.Type.Z,
        'inputAxis': Axis.Type.Z.getDefaultLetter(),
        'mapping' : [((Z_AXIS_LIMIT - 1) / 2) - 1, 0, ((Z_AXIS_LIMIT - 1) / 2) - 2, 1]
    },
    # Camera Z axis (Virtual)
    {
        'name': 'Camera Z',
        'className': 'Virtual',
        'type': Axis.Type.Z,
    },
    # Camera Rotation axis (Virtual)
    {
        'name': 'Camera Rotation',
        'className': 'Virtual',
        'type': Axis.Type.Rotation,
    }
]

CAMERAS =
[
    # Top Camera
    {
        'name' : 'Top Camera',
        'dir' : Camera.Looking.Down,
        'lightActuator': 'Top LED',
        'settleTime' : 300,
        'settleTimeout' : 120,
        'previewFPS' : 10,
        'deviceIndex' : TOP_CAMERA_OPENCV_INDEX
    },
    # Bottom Camera
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

ACTUATORS =
[
    # Bottom LED
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
    # Top LED
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
    # Left Nozzle Pump
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
                'value': LEFT_NOZZLE_PUMP_GCODE
            },
        ]
    },
    # Left Nozzle Valve
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
                'value': LEFT_NOZZLE_SOLENOID_GCODE
            },
        ]
    },
    # Left Nozzle Pump and Valve
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
    # Left Nozzle Vacuum Sensor
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
                'value': LEFT_NOZZLE_VAC_READ_GCODE
            },
            {
                'type': GcodeDriver.CommandType.ACTUATOR_READ_REGEX,
                'value': VAC_SENSE_REGEX
            },
        ]
    },
    # Right Nozzle Pump
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
                'value': RIGHT_NOZZLE_PUMP_GCODE
            },
        ]
    },
    # Right Nozzle Valve
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
                'value': RIGHT_NOZZLE_VAC_READ_GCODE
            },
        ]
    },
    # Right Nozzle Pump and Valve
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
    # Right Nozzle Vacuum Sensor
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
                'value': RIGHT_NOZZLE_VAC_READ_GCODE
            },
            {
                'type': GcodeDriver.CommandType.ACTUATOR_READ_REGEX,
                'value': VAC_SENSE_REGEX
            },
        ]
    }
    # Photon Feeder Actuator
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
    }
]

NOZZLES =
[
    # Left Nozzle
    {
        'name' : 'Left Nozzle',
        'vacuumActuator' : 'Left Nozzle Pump and Valve',
        'vacuumSenseActuator' : 'Left Nozzle Vacuum Sense',
        Axis.Type.X : Axis.Type.X.getDefaultLetter(),
        Axis.Type.Y : Axis.Type.Y.getDefaultLetter(),
        Axis.Type.Z : 'Left Z',
        Axis.Type.Rotation : 'A'
    },
    # Right Nozzle
    {
        'name' : 'Right Nozzle',
        'vacuumActuator' : 'Right Nozzle Pump and Valve',
        'vacuumSenseActuator' : 'Right Nozzle Vacuum Sense',
        Axis.Type.X : Axis.Type.X.getDefaultLetter(),
        Axis.Type.Y : Axis.Type.Y.getDefaultLetter(),
        Axis.Type.Z : 'Right Z',
        Axis.Type.Rotation : 'B'
    }
]

NOZZLE_TIPS =
[
    'N045',
    'N08',
    'N14',
    'N24',
    'N48',
    'N75'
]

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
        cam.setAxisX(find_axis_by_name(Axis.Type.X.getDefaultLetter()))
        cam.setAxisY(find_axis_by_name(Axis.Type.Y.getDefaultLetter()))
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
    driversToRemove = []
    for driver in machine.getDrivers():
        driversToRemove.append(driver)
    for driver in driversToRemove:
        print('Removing Driver \'{}\''.format(driver.getName()))
        try:
            machine.removeDriver(driver)
        except:
            pass

def remove_all_cameras():
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

def remove_all_actuators():
    actuatorsToRemove = []
    for act in machine.getActuators():
        actuatorsToRemove.append(act)
    for act in actuatorsToRemove:
        print('Removing Actuator \'{}\''.format(act.getName()))
        try:
            machine.removeActuator(act)
        except:
            pass

def remove_all_axes():
    axesToRemove = []
    for axis in machine.getAxes():
        axesToRemove.append(axis)
    for axis in axesToRemove:
        print('Removing Axis \'{}\''.format(axis.getName()))
        try:
            machine.removeAxis(axis)
        except:
            pass

def remove_all_nozzle_tips():
    nozzleTipsToRemove = []
    for ent in machine.getNozzleTips():
        nozzleTipsToRemove.append(ent)
    for tip in nozzleTipsToRemove:
        print('Removing NozzleTip \'{}\''.format(tip.getName()))
        try:
            machine.removeNozzleTip(tip)
        except:
            pass

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

def remove_head_mounted_actuators():
    actuatorsToRemove = []
    for act in machine.getDefaultHead().getActuators():
        actuatorsToRemove.append(act)
    for act in actuatorsToRemove:
        print('Removing Actuator \'{}\' from head \'{}\''.format(act.getName(), machine.getDefaultHead().getName()))
        try:
            machine.getDefaultHead().removeActuator(act)
        except:
            pass

def remove_all_feeders():
    feedersToRemove = []
    for feeder in machine.getFeeders():
        feedersToRemove.append(feeder)
    for feeder in feedersToRemove:
        print('Removing Feeder \'{}\''.format(feeder.getName()))
        try:
            machine.removeFeeder(feeder)
        except:
            pass

print('Removing existing configuration settings')

remove_all_cameras()
remove_all_actuators()
remove_all_axes()
remove_all_nozzle_tips()
remove_head_mounted_cameras()
remove_head_mounted_actuators()
remove_all_gcode_drivers()
remove_head_mounted_nozzles()
if CLEANUP_EXISTING_FEEDERS:
    remove_all_feeders()

print('Creating new configuration settings')
# Create gcode driver(s)
for driver in GCODE_DRIVERS:
    find_or_create_gcode_driver(driver['name'])

# Create nozzle tips
for tip in NOZZLE_TIPS:
    find_or_create_nozzle_tip(tip)

# Create actuators
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
        act.setValue1(ent['value'][0])
        act.setValue2(ent['value'][1])
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

# Create axis
for axis in AXES:
    find_or_create_axis(axis)

# Create cameras
for camera in CAMERAS:
    find_or_create_camera(camera)

# Create nozzles
machineHead = machine.getDefaultHead()
for ent in NOZZLES:
    nozzle = find_or_create_nozzle(ent['name'], machineHead)
    for tip in NOZZLE_TIPS:
        nozzle.addCompatibleNozzleTip(find_or_create_nozzle_tip(tip))
    nozzle.setVacuumActuator(find_actuator_by_name(ent['vacuumActuator'], machineHead))
    nozzle.setVacuumSenseActuator(find_actuator_by_name(ent['vacuumSenseActuator'], machineHead))
    nozzle.setAxisX(find_axis_by_name(ent[Axis.Type.X]))
    nozzle.setAxisY(find_axis_by_name(ent[Axis.Type.Y]))
    nozzle.setAxisZ(find_axis_by_name(ent[Axis.Type.Z]))
    nozzle.setAxisRotation(find_axis_by_name(ent[Axis.Type.Rotation]))

# Configure gcode driver(s)
for ent in GCODE_DRIVERS:
    driver = find_gcode_driver(ent['name'])
    for gcode in ent['gcode']:
        gcodeValue = ''
        if isinstance(gcode['value'], list):
            gcodeValue = '\n'.join(gcode['value'])
        else:
            gcodeValue = gcode['value']
        driver.setCommand(None, gcode['type'], gcodeValue)

# Configure actuators
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

# Save the configuration after all updates have been made
Configuration.get().save()

# Try and clear out some of the issues & solutions tab entries
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

print('Configuration complete, please proceed to Issues & Solutions')