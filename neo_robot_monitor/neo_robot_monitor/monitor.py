#!/usr/bin/env python3
"""Read-only Qt window showing live robot state.

Shows, for the Neobotix MPO-700 with a UR arm and Robotiq 2F-140 gripper:
  * where the base is, on the map and according to odometry
  * how fast the base is moving, measured and commanded
  * where the gripper tool point is, relative to the base and on the map
  * how far the gripper is open, in millimetres
  * every arm joint: angle and speed

Every figure is labelled with what it means and the unit it is in - a bare
"x = 0.049" says nothing about which frame, which direction, or what units.

There is deliberately no effort column. joint_state_broadcaster in this workspace is
configured with interfaces: [position, velocity], and 'effort' cannot be added to it:
finger_joint has no effort state interface (only the six ur10* joints do), so the
broadcaster refuses to activate with
    Can't activate controller 'joint_state_broadcaster':
    State interface with key 'finger_joint/effort' does not exist
which leaves the whole system without /joint_states. Efforts would require giving
finger_joint an effort interface in the gripper's ros2_control block first.

ROS spins in a background thread; Qt owns the main thread and a QTimer polls the latest
snapshot. Data is handed over under a lock, so no ROS callback ever touches a widget.
"""

import math
import signal
import sys
import threading

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

from sensor_msgs.msg import JointState
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from control_msgs.msg import DynamicJointState

import tf2_ros

from python_qt_binding.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QProgressBar, QFrame, QSizePolicy, QScrollArea)
from python_qt_binding.QtCore import QTimer, Qt
from python_qt_binding.QtGui import QFont, QColor


NA = 'no data'

# finger_joint runs 0.0 (fully open) .. 0.7 (closed); the 2F-140 has a 140 mm stroke.
GRIPPER_CLOSED_RAD = 0.7
GRIPPER_STROKE_MM = 140.0

# Raw joint names say nothing about what the joint physically does.
JOINT_INFO = {
    'ur10shoulder_pan_joint':  ('Base rotation',  'swings the whole arm left / right'),
    'ur10shoulder_lift_joint': ('Shoulder',       'raises / lowers the upper arm'),
    'ur10elbow_joint':         ('Elbow',          'bends the forearm'),
    'ur10wrist_1_joint':       ('Wrist 1',        'tilts the wrist up / down'),
    'ur10wrist_2_joint':       ('Wrist 2',        'turns the wrist left / right'),
    'ur10wrist_3_joint':       ('Wrist 3',        'rolls the tool about its own axis'),
    'finger_joint':            ('Gripper finger', '0 rad = fully open, 0.7 rad = closed'),
}
JOINT_ORDER = list(JOINT_INFO)



def clean(value):
    """None for anything not a usable number.

    joint_state_broadcaster fills the fixed-width JointState arrays with NaN for
    interfaces a joint does not expose, so a raw read yields 'nan' rather than an
    honest 'no value'.
    """
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) or math.isinf(v) else v


def quat_to_rpy(x, y, z, w):
    """Quaternion -> (roll, pitch, yaw) in radians, ZYX convention."""
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    sinp = 2.0 * (w * y - z * x)
    # outside [-1, 1] means gimbal lock, where asin would raise
    pitch = math.copysign(math.pi / 2.0, sinp) if abs(sinp) >= 1.0 else math.asin(sinp)

    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    return roll, pitch, yaw


class MonitorNode(Node):
    """Collects state. Never touches Qt - the GUI pulls snapshots via snapshot()."""

    def __init__(self):
        super().__init__('neo_robot_monitor')

        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('tcp_frame', 'ur10tool0')

        self.map_frame = self.get_parameter('map_frame').value
        self.odom_frame = self.get_parameter('odom_frame').value
        self.base_frame = self.get_parameter('base_frame').value
        self.tcp_frame = self.get_parameter('tcp_frame').value

        self._lock = threading.Lock()
        self._joints = {}
        self._odom_twist = None
        self._cmd_vel = None

        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                         history=HistoryPolicy.KEEP_LAST)
        self.create_subscription(JointState, '/joint_states', self._on_joint_states, qos)
        self.create_subscription(DynamicJointState, '/dynamic_joint_states',
                                 self._on_dynamic_joint_states, qos)
        self.create_subscription(Odometry, '/odom', self._on_odom, qos)
        self.create_subscription(Twist, '/cmd_vel', self._on_cmd_vel, qos)

        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self)

    def _on_joint_states(self, msg):
        with self._lock:
            for i, name in enumerate(msg.name):
                e = self._joints.setdefault(name, {})
                for field, arr in (('position', msg.position),
                                   ('velocity', msg.velocity)):
                    if i < len(arr):
                        v = clean(arr[i])
                        if v is not None or field not in e:
                            e[field] = v

    def _on_dynamic_joint_states(self, msg):
        # Mimic joints appear here as "<joint>_mimic"; they are gazebo_ros2_control
        # bookkeeping, not real URDF joints, so they are not shown.
        with self._lock:
            for name, iv in zip(msg.joint_names, msg.interface_values):
                if name.endswith('_mimic'):
                    continue
                e = self._joints.setdefault(name, {})
                for iface, value in zip(iv.interface_names, iv.values):
                    if iface in ('position', 'velocity'):
                        v = clean(value)
                        if v is not None or iface not in e:
                            e[iface] = v

    def _on_odom(self, msg):
        t = msg.twist.twist
        with self._lock:
            self._odom_twist = (t.linear.x, t.linear.y, t.angular.z)

    def _on_cmd_vel(self, msg):
        with self._lock:
            self._cmd_vel = (msg.linear.x, msg.linear.y, msg.angular.z)

    def _lookup(self, target, source):
        try:
            tr = self._tf_buffer.lookup_transform(target, source, rclpy.time.Time())
        except Exception:
            return None
        t, q = tr.transform.translation, tr.transform.rotation
        roll, pitch, yaw = quat_to_rpy(q.x, q.y, q.z, q.w)
        return {'x': t.x, 'y': t.y, 'z': t.z,
                'roll': roll, 'pitch': pitch, 'yaw': yaw}

    def snapshot(self):
        with self._lock:
            joints = {k: dict(v) for k, v in self._joints.items()}
            odom_twist, cmd_vel = self._odom_twist, self._cmd_vel
        return {
            'joints': joints,
            'odom_twist': odom_twist,
            'cmd_vel': cmd_vel,
            'base_in_map': self._lookup(self.map_frame, self.base_frame),
            'base_in_odom': self._lookup(self.odom_frame, self.base_frame),
            'tcp_in_base': self._lookup(self.base_frame, self.tcp_frame),
            'tcp_in_map': self._lookup(self.map_frame, self.tcp_frame),
        }


# ---------------------------------------------------------------- appearance
# Light theme. All text meets WCAG AA against the surface it sits on:
#   TEXT  #1f2328 on #ffffff -> 15.3:1      MUTED #6b7280 on #ffffff -> 5.0:1
#   TEXT  #1f2328 on #f4f5f7 -> 14.2:1      MUTED #6b7280 on #fafbfc -> 4.9:1
BG = '#f4f5f7'
CARD = '#ffffff'
BORDER = '#dde1e6'
TEXT = '#1f2328'
MUTED = '#6b7280'
ACCENT = '#2563eb'
# Tint of ACCENT used for the progress chunk. The bar's text sits over the chunk at
# high fill and over the groove at low fill, so it must be legible on both: dark text
# on the full accent is only 3.06:1 (AA needs 4.5), while white text on the groove is
# 1.09:1. Against this tint dark text is 11.1:1, and 14.5:1 on the groove.
ACCENT_SOFT = '#bfdbfe'
ALT_ROW = '#fafbfc'
OK_BG, OK_BORDER, OK_FG = '#e7f4ec', '#b5ddc4', '#12693a'
WARN_BG, WARN_BORDER, WARN_FG = '#fdf4e3', '#efd7a4', '#8a5a00'

# Sizes in pt so they follow display DPI. Nothing below 10 pt anywhere.
VALUE_PT = 14      # live values - the most prominent text on screen
HEADER_PT = 13     # card headers
STATUS_PT = 12     # status banner
LABEL_PT = 11      # row labels and column headers
CAPTION_PT = 10    # captions, units, "what it does", the rad column

# Both verified present via `fc-list : family`. Ubuntu Mono is deliberately not
# used: its glyphs are noticeably smaller at the same point size.
LABEL_FAMILY = 'Ubuntu'
MONO_FAMILY = 'DejaVu Sans Mono'

VALUE_MIN_W = 104  # keeps numeric columns aligned across cards


def _font(family, pt, weight, hint):
    """QFont with a style hint, so a missing family still falls back sensibly."""
    f = QFont(family, pt)
    f.setStyleHint(hint)
    f.setWeight(weight)
    return f


QSS = """
QWidget#root { background: %(BG)s; }
QScrollArea#scroll, QScrollArea#scroll > QWidget > QWidget { background: %(BG)s; }

QLabel, QTableWidget, QProgressBar, QFrame {
    font-family: "%(LABEL_FAMILY)s", "DejaVu Sans", sans-serif;
    color: %(TEXT)s;
}

QFrame#card {
    background: %(CARD)s;
    border: 1px solid %(BORDER)s;
    border-radius: 6px;
}
QWidget#cardBody { background: %(CARD)s; border: none; }

QLabel#cardHeader {
    font-size: %(HEADER_PT)dpt;
    font-weight: 600;
    color: %(TEXT)s;
    background: %(CARD)s;
    border-bottom: 1px solid %(BORDER)s;
    border-left: 3px solid %(ACCENT)s;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 9px 14px 9px 11px;
}

QLabel#rowTitle   { font-size: %(LABEL_PT)dpt; font-weight: 600; color: %(TEXT)s; }
QLabel#colHeader  { font-size: %(LABEL_PT)dpt; font-weight: 400; color: %(MUTED)s; }
QLabel#caption    { font-size: %(CAPTION_PT)dpt; font-weight: 400; color: %(MUTED)s; }

QLabel#value {
    font-family: "%(MONO_FAMILY)s", monospace;
    font-size: %(VALUE_PT)dpt;
    font-weight: 500;
    color: %(TEXT)s;
    padding: 2px 0px;
}
QLabel#value[state="nodata"] {
    font-style: italic;
    font-weight: 400;
    color: %(MUTED)s;
}

QLabel#gripState {
    font-size: %(VALUE_PT)dpt;
    font-weight: 600;
    color: %(TEXT)s;
}
QLabel#gripState[state="nodata"] {
    font-style: italic; font-weight: 400; color: %(MUTED)s;
}

QFrame#statusBanner { border: 1px solid %(BORDER)s; border-radius: 6px; }
QFrame#statusBanner[state="ok"]   { background: %(OK_BG)s;   border-color: %(OK_BORDER)s; }
QFrame#statusBanner[state="warn"] { background: %(WARN_BG)s; border-color: %(WARN_BORDER)s; }
QLabel#statusText { font-size: %(STATUS_PT)dpt; font-weight: 400; background: transparent; }
QLabel#statusDot  { font-size: %(STATUS_PT)dpt; background: transparent; }
QLabel#statusDot[state="ok"]   { color: %(OK_FG)s; }
QLabel#statusDot[state="warn"] { color: %(WARN_FG)s; }

QProgressBar#gripBar {
    font-family: "%(MONO_FAMILY)s", monospace;
    font-size: %(LABEL_PT)dpt;
    font-weight: 500;
    color: %(TEXT)s;
    background: %(BG)s;
    border: 1px solid %(BORDER)s;
    border-radius: 4px;
    text-align: center;
    min-height: 26px;
}
QProgressBar#gripBar::chunk { background: %(ACCENT_SOFT)s; border-radius: 3px; }

QTableWidget#jointTable {
    background: %(CARD)s;
    alternate-background-color: %(ALT_ROW)s;
    gridline-color: transparent;
    border: none;
    font-size: %(LABEL_PT)dpt;
    outline: 0;
}
QTableWidget#jointTable::item { padding: 4px 10px; border: none; }
QTableWidget#jointTable::item:selected { background: transparent; color: %(TEXT)s; }
QHeaderView::section {
    background: %(CARD)s;
    color: %(MUTED)s;
    font-size: %(LABEL_PT)dpt;
    font-weight: 600;
    border: none;
    border-bottom: 1px solid %(BORDER)s;
    padding: 7px 10px;
}
QToolTip {
    background: %(TEXT)s; color: %(CARD)s;
    border: none; padding: 5px;
    font-size: %(CAPTION_PT)dpt;
}
""" % {
    'BG': BG, 'CARD': CARD, 'BORDER': BORDER, 'TEXT': TEXT, 'MUTED': MUTED,
    'ACCENT': ACCENT, 'ACCENT_SOFT': ACCENT_SOFT, 'ALT_ROW': ALT_ROW,
    'OK_BG': OK_BG, 'OK_BORDER': OK_BORDER, 'OK_FG': OK_FG,
    'WARN_BG': WARN_BG, 'WARN_BORDER': WARN_BORDER, 'WARN_FG': WARN_FG,
    'LABEL_FAMILY': LABEL_FAMILY, 'MONO_FAMILY': MONO_FAMILY,
    'VALUE_PT': VALUE_PT, 'HEADER_PT': HEADER_PT, 'STATUS_PT': STATUS_PT,
    'LABEL_PT': LABEL_PT, 'CAPTION_PT': CAPTION_PT,
}


def fmt_signed(value, digits=3):
    """Signed fixed-width string, with negative zero normalised.

    Display only: a value of -0.0001 rounds to the string "-0.000", which reads as
    a negative reading when it is really zero. This is the one formatting helper
    added; it does not change any computed value.
    """
    v = clean(value)
    if v is None:
        return NA
    s = '%+.*f' % (digits, v)
    if s[0] == '-' and float(s) == 0.0:
        s = '+' + s[1:]
    return s


class MonitorWindow(QWidget):

    def __init__(self, node):
        super().__init__()
        self.node = node
        self.setWindowTitle('Neobotix Robot Monitor')
        self.setObjectName('root')
        self.setStyleSheet(QSS)

        # QSS cannot target individual QTableWidgetItems (they are not widgets), so
        # the numeric columns need real QFont objects. They mirror the QSS scale.
        self.mono = _font(MONO_FAMILY, VALUE_PT, QFont.Medium, QFont.TypeWriter)
        self.mono_small = _font(MONO_FAMILY, CAPTION_PT, QFont.Normal, QFont.TypeWriter)

        # Everything lives inside a scroll area. The content's natural height is
        # ~970 px, which is more than a 1080p screen leaves once the panel and the
        # title bar are taken off; without scrolling the window manager clamps the
        # window and the lower cards - the gripper pose first among them - are
        # simply cut off with nothing to say so. Scrolling makes every card
        # reachable on any screen, and the window opens at whatever fits.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setObjectName('scroll')
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        outer.addWidget(scroll)

        self.content = QWidget()
        self.content.setObjectName('root')
        scroll.setWidget(self.content)

        root = QVBoxLayout(self.content)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        root.addWidget(self._build_status())

        # The two 3-column cards sit side by side; stacking every card in one column
        # overflows a 1080p screen once the values are at 14 pt.
        pair = QHBoxLayout()
        pair.setSpacing(10)
        pair.addWidget(self._build_where(), 1)
        pair.addWidget(self._build_speed(), 1)
        row = QWidget()
        row.setLayout(pair)
        root.addWidget(row)

        root.addWidget(self._build_gripper_pose())
        root.addWidget(self._build_gripper_opening())
        root.addWidget(self._build_joints(), 1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(100)

    # ----------------------------------------------------------------- helpers
    def _card(self, title):
        """A card frame with an accented header. Returns (frame, body_layout)."""
        card = QFrame()
        card.setObjectName('card')
        outer = QVBoxLayout(card)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        head = QLabel(title)
        head.setObjectName('cardHeader')
        outer.addWidget(head)

        body = QWidget()
        body.setObjectName('cardBody')
        inner = QGridLayout(body)
        inner.setContentsMargins(14, 10, 14, 12)
        inner.setHorizontalSpacing(14)
        inner.setVerticalSpacing(8)
        outer.addWidget(body)
        return card, inner

    @staticmethod
    def _no_vertical_squeeze(label):
        """Stop a single-line label being compressed below its sizeHint.

        QLabel's default vertical policy is Preferred, which may shrink. That makes
        the window report a minimumSizeHint smaller than the text actually needs, so
        at the minimum size the rows are squeezed and glyphs are clipped.
        """
        label.setSizePolicy(label.sizePolicy().horizontalPolicy(), QSizePolicy.Fixed)
        return label

    def _caption(self, text):
        lab = QLabel(text)
        lab.setObjectName('caption')
        self._no_vertical_squeeze(lab)
        # Deliberately NOT word-wrapped: a wrapping QLabel reports a one-line
        # sizeHint, so layouts under-allocate its height and clip the text - which
        # is exactly what cut off the two TCP captions before. Fixed single lines
        # make the geometry deterministic and the width requirement honest.
        lab.setWordWrap(False)
        return lab

    def _column_header(self, text, tip=''):
        lab = QLabel(text)
        lab.setObjectName('colHeader')
        self._no_vertical_squeeze(lab)
        if tip:
            lab.setToolTip(tip)
        return lab

    def _value(self):
        lab = QLabel(NA)
        lab.setObjectName('value')
        self._no_vertical_squeeze(lab)
        lab.setProperty('state', 'nodata')
        lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lab.setMinimumWidth(VALUE_MIN_W)
        return lab

    def _row_label(self, title, subtitle, tip=''):
        """Title over caption. No fixed heights - the caption wraps and the layout
        grows, which is why the old build clipped the two-line TCP captions."""
        w = QWidget()
        box = QVBoxLayout(w)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)
        t = QLabel(title)
        t.setObjectName('rowTitle')
        self._no_vertical_squeeze(t)
        box.addWidget(t)
        box.addWidget(self._caption(subtitle))
        # The wrapper itself must also resist vertical compression, otherwise the
        # grid shrinks it and squeezes the two labels inside regardless of their
        # own policies.
        w.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        if tip:
            w.setToolTip(tip)
        return w

    def _pose_card(self, title, heads, rows, store, ncols):
        card, grid = self._card(title)
        grid.setColumnStretch(0, 1)
        for c, (h, tip) in enumerate(heads, start=1):
            grid.addWidget(self._column_header(h, tip), 0, c, Qt.AlignRight)
            grid.setColumnStretch(c, 0)
        for r, (key, rtitle, sub, tip) in enumerate(rows, start=1):
            grid.addWidget(self._row_label(rtitle, sub, tip), r, 0)
            store[key] = [self._value() for _ in range(ncols)]
            for c, lab in enumerate(store[key], start=1):
                grid.addWidget(lab, r, c)
        return card

    # ------------------------------------------------------------------ status
    def _build_status(self):
        frame = QFrame()
        frame.setObjectName('statusBanner')
        frame.setProperty('state', 'warn')
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(10)
        self.status_dot = QLabel('●')
        self.status_dot.setObjectName('statusDot')
        self.status_dot.setProperty('state', 'warn')
        self.status_text = QLabel('starting...')
        self.status_text.setObjectName('statusText')
        self._no_vertical_squeeze(self.status_text)
        self.status_text.setWordWrap(False)
        lay.addWidget(self.status_dot)
        lay.addWidget(self.status_text, 1)
        self._status_banner = frame
        return frame

    # ------------------------------------------------------------ where it is
    def _build_where(self):
        self.pose_rows = {}
        heads = [('X - forward [m]', 'Distance along the frame X axis'),
                 ('Y - left [m]', 'Distance along the frame Y axis'),
                 ('Heading [deg]', 'Rotation about the vertical axis. 0 = facing +X')]
        rows = [
            ('base_in_map', 'Position on the map',
             '%s -> %s   the absolute position navigation uses'
             % (self.node.map_frame, self.node.base_frame),
             'Comes from localisation. Needs a map; correct it with a 2D Pose '
             'Estimate in RViz if it drifts.'),
            ('base_in_odom', 'Travelled since start-up',
             '%s -> %s   wheel odometry, drifts slowly'
             % (self.node.odom_frame, self.node.base_frame),
             'Always available and smooth, but accumulates error. Starts at zero '
             'wherever the robot was when the simulation started.'),
        ]
        return self._pose_card('Where the robot is', heads, rows, self.pose_rows, 3)

    # --------------------------------------------------------------- how fast
    def _build_speed(self):
        self.speed_rows = {}
        heads = [('Forward [m/s]', 'Positive = forward, negative = reverse'),
                 ('Sideways [m/s]', 'Positive = left. Non-zero only because the '
                                    'MPO-700 can drive sideways'),
                 ('Turning [deg/s]', 'Positive = counter-clockwise seen from above')]
        rows = [
            ('odom_twist', 'Actually moving', '/odom   measured by the simulator',
             'What the robot is really doing right now.'),
            ('cmd_vel', 'Being told to move',
             '/cmd_vel   sent by teleop or navigation',
             'Shows "no data" when nothing is publishing, i.e. teleop is not running '
             'and navigation is idle. That is normal, not a fault.'),
        ]
        return self._pose_card('How fast the base is moving', heads, rows,
                               self.speed_rows, 3)

    # ----------------------------------------------------------- gripper pose
    def _build_gripper_pose(self):
        self.tcp_rows = {}
        heads = [('X [m]', 'Forward'), ('Y [m]', 'Left'),
                 ('Z [m]', 'Height above the frame origin'),
                 ('Roll [deg]', 'Rotation about X'),
                 ('Pitch [deg]', 'Rotation about Y'),
                 ('Yaw [deg]', 'Rotation about Z')]
        rows = [
            ('tcp_in_base', 'Relative to the robot',
             'measured from base_link   changes only when the arm moves',
             'Where the tool sits with respect to the robot itself. Unchanged when '
             'the base drives around.'),
            ('tcp_in_map', 'Absolute on the map',
             'measured from map   changes when the base drives too',
             'Where the tool is in the world. This is the one to use for reaching a '
             'fixed object.'),
        ]
        return self._pose_card(
            'Where the gripper is   (frame: %s)' % self.node.tcp_frame,
            heads, rows, self.tcp_rows, 6)

    # -------------------------------------------------------- gripper opening
    def _build_gripper_opening(self):
        card, grid = self._card('Gripper')
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)

        left = QWidget()
        box = QVBoxLayout(left)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)
        self.grip_state = QLabel(NA)
        self.grip_state.setObjectName('gripState')
        self._no_vertical_squeeze(self.grip_state)
        self.grip_state.setProperty('state', 'nodata')
        box.addWidget(self.grip_state)
        box.addWidget(self._caption(
            'Robotiq 2F-140   %.0f mm stroke   finger_joint 0 rad = open, '
            '%.1f rad = closed' % (GRIPPER_STROKE_MM, GRIPPER_CLOSED_RAD)))
        grid.addWidget(left, 0, 0)

        self.grip_bar = QProgressBar()
        self.grip_bar.setObjectName('gripBar')
        self.grip_bar.setRange(0, 100)
        self.grip_bar.setValue(0)
        self.grip_bar.setMinimumWidth(300)
        self.grip_bar.setTextVisible(True)
        self.grip_bar.setToolTip(
            'Full bar = fingers wide open, empty bar = fully closed')
        grid.addWidget(self.grip_bar, 0, 1)
        return card

    # ------------------------------------------------------------------ joints
    def _build_joints(self):
        card, grid = self._card('Arm joints')
        grid.setColumnStretch(0, 1)
        grid.addWidget(self._caption(
            'Angle of each joint. Degrees and radians are the same value in different '
            'units. Speed is how fast that joint is turning right now.'), 0, 0)

        self.table = QTableWidget(0, 5)
        self.table.setObjectName('jointTable')
        self.table.setHorizontalHeaderLabels(
            ['Joint', 'What it does', 'Angle [deg]', 'Angle [rad]', 'Speed [deg/s]'])
        self.table.verticalHeader().setVisible(False)

        # Read-only: no edit triggers, no selection highlight, no focus rectangle.
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)

        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.setFrameShape(QFrame.NoFrame)
        # Hard requirement: no scrolling anywhere.
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        for c in (2, 3, 4):
            hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        hh.setHighlightSections(False)

        # Rows are always the 7 known joints; fix the height to header + 7 rows so
        # the table can never grow a scrollbar.
        fm_h = self.fontMetrics().height()
        row_h = int(fm_h * 1.9)
        vh = self.table.verticalHeader()
        vh.setDefaultSectionSize(row_h)
        vh.setSectionResizeMode(QHeaderView.Fixed)
        self.table.setRowCount(len(JOINT_ORDER))
        # Final height is set in showEvent, not here: QSS ::item padding is applied
        # at polish time, which grows the rows after this point (37 px here, 39 px
        # once shown). Sizing from build-time metrics leaves the table a few pixels
        # short, and being short by even one pixel grows a scrollbar.

        grid.addWidget(self.table, 1, 0)
        return card

    def showEvent(self, event):
        super().showEvent(event)
        self._fit_table_height()
        if not getattr(self, '_sized_once', False):
            self._sized_once = True
            self._fit_to_screen()

    def _fit_to_screen(self):
        """Open at the content's natural size, capped to the screen it is on.

        The content's sizeHint is only trustworthy after the first show (before
        that the tables report a one-row height), which is why this runs from
        showEvent and not from __init__.
        """
        want = self.content.sizeHint()
        screen = self.screen() if hasattr(self, 'screen') else None
        avail = screen.availableGeometry() if screen else QApplication.desktop().availableGeometry(self)
        margin = 60   # title bar and a little breathing room
        w = min(want.width() + 24, avail.width() - margin)
        h = min(want.height() + 24, avail.height() - margin)
        self.resize(w, h)

    def _fit_table_height(self):
        """Pin the table to header + all rows, measured after polish."""
        hh = self.table.horizontalHeader()
        total = hh.height() + 2 * self.table.frameWidth() + 2
        for r in range(self.table.rowCount()):
            total += self.table.rowHeight(r)
        if self.table.height() != total:
            self.table.setFixedHeight(total)

    # ----------------------------------------------------------------- refresh
    @staticmethod
    def _set_state(widget, state):
        """Swap a dynamic property and re-polish so the QSS rule applies."""
        if widget.property('state') != state:
            widget.setProperty('state', state)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def _set_value(self, label, text):
        label.setText(text)
        self._set_state(label, 'nodata' if text == NA else 'ok')

    def _fill(self, labels, pose, keys, degrees):
        if pose is None:
            for lab in labels:
                self._set_value(lab, NA)
            return
        for lab, key in zip(labels, keys):
            if key in degrees:
                self._set_value(lab, fmt_signed(math.degrees(pose[key]), 1))
            else:
                self._set_value(lab, fmt_signed(pose[key], 3))

    def refresh(self):
        s = self.node.snapshot()
        ang = ('roll', 'pitch', 'yaw')

        self._fill(self.pose_rows['base_in_map'], s['base_in_map'],
                   ['x', 'y', 'yaw'], ang)
        self._fill(self.pose_rows['base_in_odom'], s['base_in_odom'],
                   ['x', 'y', 'yaw'], ang)
        self._fill(self.tcp_rows['tcp_in_base'], s['tcp_in_base'],
                   ['x', 'y', 'z', 'roll', 'pitch', 'yaw'], ang)
        self._fill(self.tcp_rows['tcp_in_map'], s['tcp_in_map'],
                   ['x', 'y', 'z', 'roll', 'pitch', 'yaw'], ang)

        for key in ('odom_twist', 'cmd_vel'):
            vals = s[key]
            for i, lab in enumerate(self.speed_rows[key]):
                if vals is None:
                    self._set_value(lab, NA)
                else:
                    # the third column is angular, shown in deg/s to match "Heading"
                    self._set_value(lab, fmt_signed(math.degrees(vals[i]), 1) if i == 2
                                    else fmt_signed(vals[i], 3))

        joints = s['joints']
        self._refresh_gripper(joints.get('finger_joint', {}))
        self._refresh_joints(joints)
        self._refresh_status(s, joints)

    def _refresh_gripper(self, entry):
        pos = clean(entry.get('position'))
        vel = clean(entry.get('velocity'))
        if pos is None:
            self.grip_state.setText(NA)
            self._set_state(self.grip_state, 'nodata')
            self.grip_bar.setValue(0)
            self.grip_bar.setFormat('no data')
            return

        frac = max(0.0, min(1.0, 1.0 - pos / GRIPPER_CLOSED_RAD))
        pct = frac * 100.0
        mm = frac * GRIPPER_STROKE_MM
        self.grip_bar.setValue(int(round(pct)))
        self.grip_bar.setFormat('%.0f%% open   (%.0f mm)' % (pct, mm))

        if vel is not None and abs(vel) > 0.01:
            word = 'Closing' if vel > 0 else 'Opening'
        elif pct > 95.0:
            word = 'Fully open'
        elif pct < 5.0:
            word = 'Closed'
        else:
            word = 'Partly open'
        self.grip_state.setText('%s - %.0f mm between the fingers' % (word, mm))
        self._set_state(self.grip_state, 'ok')

    def _refresh_joints(self, joints):
        names = [n for n in JOINT_ORDER if n in joints]
        names += sorted(n for n in joints if n not in JOINT_INFO)
        if self.table.rowCount() != len(names):
            self.table.setRowCount(len(names))

        for r, name in enumerate(names):
            e = joints[name]
            pos, vel = clean(e.get('position')), clean(e.get('velocity'))
            friendly, what = JOINT_INFO.get(name, (name, ''))
            cells = [
                friendly,
                what,
                NA if pos is None else fmt_signed(math.degrees(pos), 1),
                NA if pos is None else fmt_signed(pos, 4),
                NA if vel is None else fmt_signed(math.degrees(vel), 1),
            ]
            for c, text in enumerate(cells):
                item = self.table.item(r, c)
                if item is None:
                    item = QTableWidgetItem()
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter if c < 2
                                          else Qt.AlignRight | Qt.AlignVCenter)
                    if c in (2, 4):
                        item.setFont(self.mono)
                    elif c == 3:
                        item.setFont(self.mono_small)
                    self.table.setItem(r, c, item)
                item.setText(text)
                if c == 1 or c == 3:
                    item.setForeground(QColor(MUTED))
                else:
                    item.setForeground(QColor(MUTED if text == NA else TEXT))
                item.setToolTip('%s   (%s)' % (name, what) if what else name)

    def _refresh_status(self, s, joints):
        missing = []
        if not joints:
            missing.append('joint states - is the simulation running?')
        if s['base_in_map'] is None:
            missing.append('map position - no "%s" frame yet, start navigation'
                           % self.node.map_frame)
        if s['tcp_in_base'] is None:
            missing.append('gripper pose - no "%s" frame' % self.node.tcp_frame)

        if missing:
            state = 'warn'
            self.status_text.setText('Waiting for:  ' + ';   '.join(missing))
        else:
            state = 'ok'
            self.status_text.setText(
                'Live - %d joints, base position and gripper pose all reporting.'
                % len(joints))
        self._set_state(self._status_banner, state)
        self._set_state(self.status_dot, state)


def main(args=None):
    rclpy.init(args=args)
    node = MonitorNode()

    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)
    threading.Thread(target=executor.spin, daemon=True).start()

    app = QApplication(sys.argv)
    window = MonitorWindow(node)
    window.show()

    # Qt's event loop does not run Python bytecode while idle, so Python signal
    # handlers never fire and the process ignores SIGINT/SIGTERM. ros2 launch then
    # reports "failed to terminate 10.0 seconds after receiving 'SIGTERM',
    # escalating to 'SIGKILL'" on every shutdown. Handling the signals to quit the
    # app, plus a no-op timer that hands control back to the interpreter often
    # enough for those handlers to run, makes Ctrl-C and launch shutdown immediate.
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: app.quit())
    wakeup = QTimer()
    wakeup.timeout.connect(lambda: None)
    wakeup.start(200)

    try:
        rc = app.exec_()
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(rc)


if __name__ == '__main__':
    main()
