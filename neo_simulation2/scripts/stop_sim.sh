#!/usr/bin/env bash
# Graceful shutdown of the Neobotix Gazebo Classic simulation stack.
#
# The graceful path is to SIGINT the "ros2 launch" process (matched as bin/ros2
# launch, so a shell that merely mentions the command is not caught), exactly as Ctrl-C does.
# ros2 launch then tears its children down in order and gzserver reports
# "process has finished cleanly", releasing port 11345 properly.
#
# Signalling gzserver directly does NOT work: when it is not the foreground process
# of a terminal it ignores both SIGINT and SIGTERM (verified - it survived 20s of
# each), so anything other than the launch-level shutdown ends in SIGKILL. A killed
# gzserver leaves port 11345 in TIME_WAIT and the next launch fails with
#   [Err] Unable to start server[bind: Address already in use].
# Orphans left behind by an already-dead launch are cleaned up as a fallback.
#
# Processes are matched by exact name (pgrep -x) where possible: matching on the full
# command line (-f) would also match any shell mentioning "gzserver" - including this
# script's own caller.

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

_pids() {   # _pids <x|f> <pattern>
    local mode=$1 pat=$2 pid out
    if [ "$mode" = x ]; then out=$(pgrep -x "$pat" 2>/dev/null)
    else                     out=$(pgrep -f "$pat" 2>/dev/null); fi
    for pid in $out; do
        case "$PROTECTED" in *" $pid "*) continue ;; esac
        printf '%s ' "$pid"
    done
}

# ---------------------------------------------------------------- stage 1: launch
launch_pids=$(_pids f "bin/ros2 launch")
if [ -n "$launch_pids" ]; then
    echo "Sending SIGINT to ros2 launch (same as Ctrl-C):"
    for p in $launch_pids; do
        printf '  pid %-7s %s\n' "$p" "$(ps -o args= -p "$p" 2>/dev/null | cut -c1-70)"
    done
    # shellcheck disable=SC2086
    kill -INT $launch_pids 2>/dev/null || true
    waited=0
    while [ "$waited" -lt "$LAUNCH_TIMEOUT" ]; do
        [ -z "$(_pids f 'bin/ros2 launch')" ] && break
        sleep 1; waited=$((waited + 1))
    done
    [ -z "$(_pids f 'bin/ros2 launch')" ] \
        && echo "  launch exited cleanly after ${waited}s" \
        || echo "  launch still up after ${LAUNCH_TIMEOUT}s - cleaning up children"
else
    echo "No 'ros2 launch' process found - cleaning up orphans directly."
fi

# ------------------------------------------------- stage 2: orphans (fallback only)
stop() {    # stop <x|f> <pattern> <label>
    local mode=$1 pat=$2 label=$3 sig pids waited
    pids=$(_pids "$mode" "$pat")
    [ -z "$pids" ] && { printf '  %-24s clean\n' "$label"; return 0; }
    for sig in INT TERM KILL; do
        # shellcheck disable=SC2086
        kill -"$sig" $pids 2>/dev/null || true
        waited=0
        while :; do
            pids=$(_pids "$mode" "$pat")
            [ -z "$pids" ] && { printf '  %-24s stopped (SIG%s)\n' "$label" "$sig"; return 0; }
            sleep 1; waited=$((waited + 1))
            [ "$sig" = KILL ] && [ "$waited" -ge 3 ] && break
            [ "$sig" != KILL ] && [ "$waited" -ge "$STAGE_TIMEOUT" ] && break
        done
    done
    printf '  %-24s STILL RUNNING (%s)\n' "$label" "$pids"; return 1
}

echo "Checking for leftovers..."
stop f "controller_manager/spawner" "controller spawners"
stop f "teleop_twist_keyboard"      "teleop"
stop x "move_group"                 "move_group"
stop x "rviz2"                      "rviz2"
# Linux truncates the process name (comm) to 15 chars, so "robot_state_publisher"
# appears as "robot_state_pub" and pgrep -x never matches it. Match the binary and
# the "ros2 run" wrapper by path instead - specific enough not to catch a shell.
stop f "lib/robot_state_publisher/robot_state_publisher" "robot_state_publisher"
stop f "ros2 run robot_state_publisher"                  "rsp (ros2 run)"
# Simulation stand-ins for real-robot nodes (neo_simulation2/scripts). Matched by
# installed path - specific enough not to catch a shell.
stop f "lib/neo_simulation2/sim_scan_filter.py"      "sim_scan_filter"
stop f "lib/neo_simulation2/gripper_action_relay.py" "gripper_action_relay"
stop x "gzclient"                   "gzclient"
stop x "gzserver"                   "gzserver"

# ------------------------------------------------------------------ stage 3: port
echo "Waiting for gazebo master port 11345..."
for _ in $(seq 60); do
    ss -tan 2>/dev/null | grep -q ':11345' || { echo "  port 11345 free - safe to relaunch"; exit 0; }
    sleep 1
done
echo "  WARNING: port 11345 still held (TIME_WAIT). Wait ~30s before relaunching."
exit 1
