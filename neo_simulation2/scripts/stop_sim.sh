#!/usr/bin/env bash
# Shutdown of the Neobotix Gazebo Classic simulation stack.
#
# Stage 1 - launch: SIGINT to every "ros2 launch" process (matched as bin/ros2
# launch, so a shell that merely mentions the command is not caught), exactly as
# Ctrl-C does. ros2 launch then tears its children down in order and gzserver
# reports "process has finished cleanly", releasing port 11345 properly.
#
# Stage 2 - launch tree: the process tree of every launch is recorded before the
# SIGINT. Whatever of it is still running after LAUNCH_TIMEOUT is stopped with
# SIGINT, SIGTERM and finally SIGKILL, and so is a launch process that is still up.
# Following the tree instead of a list of names catches every node, whatever it is
# called. Before, only a fixed list was cleaned up: when a launch hung, map_server,
# localization and the Nav2 servers kept running, and the next start had two of
# every Nav2 node. A node that ignores both SIGINT and SIGTERM ends with SIGKILL.
#
# Stage 3 - orphans: nodes whose launch had already died (closed terminal, crashed
# launch) have no tree to follow. They are found by executable path or exact name.
#
# Signalling gzserver directly does NOT work: when it is not the foreground process
# of a terminal it ignores both SIGINT and SIGTERM (verified - it survived 20s of
# each), so anything other than the launch-level shutdown ends in SIGKILL. A killed
# gzserver leaves port 11345 in TIME_WAIT and the next launch fails with
#   [Err] Unable to start server[bind: Address already in use].
# Stage 4 waits for the port.
#
# Processes are matched by exact name (pgrep -x) or by the program they run: the
# executable path, or the script path for Python programs (see _program). A shell or
# tool whose command line merely mentions a pattern is never matched. Linux truncates
# the process name (comm) to 15 chars, so longer names must be matched by path. The
# processes this script runs in (its caller chain) are never signalled either.
#
# Exit status: 0 everything stopped and port 11345 free; 1 everything stopped but
# the port is still in TIME_WAIT; 2 processes could not be stopped.

LAUNCH_TIMEOUT=${LAUNCH_TIMEOUT:-25}
STAGE_TIMEOUT=${STAGE_TIMEOUT:-8}

_protected() {
    local p=$$
    while [ -n "$p" ] && [ "$p" -gt 1 ] 2>/dev/null; do
        printf '%s ' "$p"
        p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')
    done
}
PROTECTED=" $(_protected) "

# What a process runs: its executable, or for "python3 <script> <args>" the script
# and its arguments. A shell or tool that merely mentions a pattern in its command
# line (bash -c "...", grep ..., python3 -c "...") therefore never matches.
_program() {
    local -a argv
    mapfile -d '' -t argv < "/proc/$1/cmdline" 2>/dev/null
    case "${argv[0]##*/}" in
        python*) [ "${argv[1]}" != "-c" ] && printf '%s' "${argv[*]:1}" ;;
        *)       printf '%s' "${argv[0]}" ;;
    esac
}

_pids() {   # _pids <x|f> <pattern>
    local mode=$1 pat=$2 pid out
    if [ "$mode" = x ]; then out=$(pgrep -x "$pat" 2>/dev/null)
    else                     out=$(pgrep -f "$pat" 2>/dev/null); fi
    for pid in $out; do
        case "$PROTECTED" in *" $pid "*) continue ;; esac
        if [ "$mode" = f ]; then [[ "$(_program "$pid")" =~ $pat ]] || continue; fi
        printf '%s ' "$pid"
    done
}

# Start time of a process (field 22 of /proc/<pid>/stat), empty once it is gone.
# Stored with the pid, it tells a recorded process from a new one reusing its pid.
# A zombie (state Z: exited, not yet collected by a hung parent) counts as gone.
_start() { sed -E 's/^.*\) //' "/proc/$1/stat" 2>/dev/null | awk '$1 != "Z" {print $20}'; }

_descendants() {    # _descendants <pid>... - all descendants, recursively
    local frontier="$*" next all=""
    while [ -n "$frontier" ]; do
        next=$(ps -o pid= --ppid "$(echo $frontier | tr ' ' ',')" 2>/dev/null | tr -s ' \n' ' ')
        all="$all $next"
        frontier=$(echo $next)
    done
    echo $all
}

_track() {          # _track <pid>... - prints "pid:start" entries
    local p s
    for p in "$@"; do
        case "$PROTECTED" in *" $p "*) continue ;; esac
        s=$(_start "$p"); [ -z "$s" ] && continue
        printf '%s:%s ' "$p" "$s"
    done
}

declare -A NAME
_names() {          # _names <pid:start>... - remembers process names for the report
    local e p n     # (not in _track: that runs in a $(...) subshell)
    for e in "$@"; do
        p=${e%%:*}; n=$(_program "$p"); n=${n%% *}; n=${n##*/}
        [ -z "$n" ] && n=$(ps -o comm= -p "$p" 2>/dev/null)
        NAME[$p]=$n
    done
}

_alive() {          # _alive "<pid:start>..." - pids of those still running
    local e
    for e in $1; do
        [ "$(_start "${e%%:*}")" = "${e#*:}" ] && printf '%s ' "${e%%:*}"
    done
}

escalate() {        # escalate "<pid:start>..." - SIGINT, SIGTERM, SIGKILL; reports each
    local tracked=$1 alive left sig p waited
    alive=$(_alive "$tracked")
    for sig in INT TERM KILL; do
        [ -z "$alive" ] && return 0
        # shellcheck disable=SC2086
        kill -"$sig" $alive 2>/dev/null || true
        waited=0
        while :; do
            sleep 1; waited=$((waited + 1))
            left=$(_alive "$tracked")
            [ -z "$left" ] && break
            [ "$sig" = KILL ] && [ "$waited" -ge 3 ] && break
            [ "$sig" != KILL ] && [ "$waited" -ge "$STAGE_TIMEOUT" ] && break
        done
        for p in $alive; do
            case " $left " in *" $p "*) ;; *) printf '  %-28s stopped (SIG%s)\n' "${NAME[$p]} ($p)" "$sig" ;; esac
        done
        alive=$left
    done
    for p in $alive; do printf '  %-28s STILL RUNNING\n' "${NAME[$p]} ($p)"; done
    [ -z "$alive" ]
}

failed=0

# ---------------------------------------------------------------- stage 1: launch
launch_pids=$(_pids f "bin/ros2 launch")
if [ -n "$launch_pids" ]; then
    # shellcheck disable=SC2086
    launches=$(_track $launch_pids)
    # shellcheck disable=SC2086
    tree=$(_track $(_descendants $launch_pids))
    # shellcheck disable=SC2086
    _names $launches $tree
    echo "Sending SIGINT to ros2 launch (same as Ctrl-C):"
    for p in $launch_pids; do
        printf '  pid %-7s %s\n' "$p" "$(ps -o args= -p "$p" 2>/dev/null | cut -c1-70)"
    done
    # shellcheck disable=SC2086
    kill -INT $launch_pids 2>/dev/null || true
    waited=0
    while [ "$waited" -lt "$LAUNCH_TIMEOUT" ]; do
        [ -z "$(_alive "$launches $tree")" ] && break
        sleep 1; waited=$((waited + 1))
    done
    if [ -z "$(_alive "$launches $tree")" ]; then
        echo "  launch and all its nodes exited cleanly after ${waited}s"
    else
        # ------------------------------------------------- stage 2: launch tree
        echo "  still running after ${LAUNCH_TIMEOUT}s - stopping the remaining nodes:"
        escalate "$tree" || failed=1
        # ros2 launch exits once its children are gone; stop it if it does not.
        for _ in $(seq 5); do [ -z "$(_alive "$launches")" ] && break; sleep 1; done
        escalate "$launches" || failed=1
    fi
else
    echo "No 'ros2 launch' process found - cleaning up orphans directly."
fi

# ------------------------------------------------------------- stage 3: orphans
stop() {    # stop <x|f> <pattern> <label>
    local mode=$1 pat=$2 label=$3 sig pids waited
    pids=$(_pids "$mode" "$pat")
    [ -z "$pids" ] && { printf '  %-28s clean\n' "$label"; return 0; }
    for sig in INT TERM KILL; do
        # shellcheck disable=SC2086
        kill -"$sig" $pids 2>/dev/null || true
        waited=0
        while :; do
            pids=$(_pids "$mode" "$pat")
            [ -z "$pids" ] && { printf '  %-28s stopped (SIG%s)\n' "$label" "$sig"; return 0; }
            sleep 1; waited=$((waited + 1))
            [ "$sig" = KILL ] && [ "$waited" -ge 3 ] && break
            [ "$sig" != KILL ] && [ "$waited" -ge "$STAGE_TIMEOUT" ] && break
        done
    done
    printf '  %-28s STILL RUNNING (%s)\n' "$label" "$pids"; return 1
}

echo "Checking for leftovers..."
# Tools and helpers
stop f "controller_manager/spawner"                    "controller spawners"   || failed=1
stop f "gazebo_ros/spawn_entity.py"                    "spawn_entity"          || failed=1
stop f "neo_sim_objects/spawn_objects"                 "spawn_objects"         || failed=1
stop f "teleop_twist_keyboard"                         "teleop"                || failed=1
stop f "joint_state_publisher_gui/joint_state_publisher_gui" "joint_state_publisher_gui" || failed=1
stop f "joint_state_publisher/joint_state_publisher"   "joint_state_publisher" || failed=1
stop f "neo_robot_monitor/monitor"                     "robot monitor"         || failed=1
stop x "rviz2"                                         "rviz2"                 || failed=1
# Arm
stop x "move_group"                                    "move_group"            || failed=1
stop f "controller_manager/ros2_control_node"          "ros2_control_node"     || failed=1
# Navigation, localization and mapping
stop f "nav2_bt_navigator/bt_navigator"                "bt_navigator"          || failed=1
stop f "nav2_waypoint_follower/waypoint_follower"      "waypoint_follower"     || failed=1
stop f "nav2_behaviors/behavior_server"                "behavior_server"       || failed=1
stop f "nav2_controller/controller_server"             "controller_server"     || failed=1
stop f "nav2_planner/planner_server"                   "planner_server"        || failed=1
stop f "nav2_lifecycle_manager/lifecycle_manager"      "lifecycle_manager"     || failed=1
stop f "nav2_map_server/map_server"                    "map_server"            || failed=1
stop f "nav2_amcl/amcl"                                "amcl"                  || failed=1
stop f "neo_localization2/neo_localization_node"       "neo_localization"      || failed=1
stop f "slam_toolbox/sync_slam_toolbox_node"           "slam_toolbox"          || failed=1
# Robot description and simulation stand-ins for real-robot nodes
stop f "lib/robot_state_publisher/robot_state_publisher" "robot_state_publisher" || failed=1
stop f "ros2 run robot_state_publisher"                "rsp (ros2 run)"        || failed=1
stop f "lib/neo_simulation2/sim_scan_filter.py"        "sim_scan_filter"       || failed=1
stop f "lib/neo_simulation2/gripper_action_relay.py"   "gripper_action_relay"  || failed=1
# Gazebo last: the nodes above may still be talking to it
stop x "gzclient"                                      "gzclient"              || failed=1
stop x "gzserver"                                      "gzserver"              || failed=1

if [ "$failed" -ne 0 ]; then
    echo "ERROR: some processes could not be stopped (see STILL RUNNING above)."
    exit 2
fi

# ------------------------------------------------------------------ stage 4: port
echo "Waiting for gazebo master port 11345..."
for _ in $(seq 60); do
    ss -tan 2>/dev/null | grep -q ':11345' || { echo "  port 11345 free - safe to relaunch"; exit 0; }
    sleep 1
done
echo "  WARNING: port 11345 still held (TIME_WAIT). Wait ~30s before relaunching."
exit 1
