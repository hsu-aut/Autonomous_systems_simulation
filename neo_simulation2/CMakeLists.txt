cmake_minimum_required(VERSION 3.5)
project(neo_simulation2)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch
  configs
  maps
  worlds
  robots
  rviz
  components
  models
  DESTINATION share/${PROJECT_NAME})

# Stand-ins for nodes the real robot runs on hardware (see each script).
install(PROGRAMS
  scripts/sim_scan_filter.py
  scripts/gripper_action_relay.py
  scripts/stop_sim.sh
  DESTINATION lib/${PROJECT_NAME})

ament_package()
