cmake_minimum_required(VERSION 3.8)
project(neo_link_attacher)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(gazebo_ros REQUIRED)
find_package(gazebo_dev REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "srv/Attach.srv"
  "srv/SetCollideBitmask.srv"
)
rosidl_get_typesupport_target(cpp_typesupport_target ${PROJECT_NAME} rosidl_typesupport_cpp)

add_library(${PROJECT_NAME}_plugin SHARED src/link_attacher.cpp)
target_include_directories(${PROJECT_NAME}_plugin PUBLIC ${GAZEBO_INCLUDE_DIRS})
target_link_libraries(${PROJECT_NAME}_plugin ${GAZEBO_LIBRARIES} "${cpp_typesupport_target}")
ament_target_dependencies(${PROJECT_NAME}_plugin rclcpp gazebo_ros gazebo_dev)

install(TARGETS ${PROJECT_NAME}_plugin
  LIBRARY DESTINATION lib
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
