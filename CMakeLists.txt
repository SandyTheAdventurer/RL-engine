cmake_minimum_required(VERSION 3.20)
project(RL-engine VERSION 0.1 LANGUAGES CXX)

find_package(SDL3 REQUIRED)

add_executable(RL-engine main.cpp Player.cpp)

target_link_libraries(RL-engine PRIVATE SDL3::SDL3)
