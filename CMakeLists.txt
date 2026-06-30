cmake_minimum_required(VERSION 3.20)
project(RL-engine VERSION 0.1 LANGUAGES CXX)

set(SDL3_DIR /usr/lib/cmake/SDL3)
find_package(SDL3 REQUIRED)
find_package(SDL3_image REQUIRED)
find_package(SDL3_ttf REQUIRED)
find_package(IXWebSocket REQUIRED)
find_package(nlohmann_json REQUIRED)
find_package(spdlog REQUIRED)
find_package(ZLIB REQUIRED)
find_package(fmt REQUIRED)

add_executable(RL-engine main.cpp src/Player.cpp src/Bullet.cpp src/Input.cpp src/Events.cpp src/Collision.cpp src/Updates.cpp src/Structures.cpp src/SocketClient.cpp)
target_include_directories(RL-engine PRIVATE src)

target_link_libraries(RL-engine PRIVATE SDL3::SDL3 SDL3_image::SDL3_image SDL3_ttf::SDL3_ttf ixwebsocket nlohmann_json ZLIB::ZLIB spdlog::spdlog fmt::fmt)
