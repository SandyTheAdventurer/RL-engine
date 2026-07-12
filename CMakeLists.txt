cmake_minimum_required(VERSION 3.20)
project(rlengine VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if(NOT DEFINED SDL3_DIR AND EXISTS "/usr/lib/cmake/SDL3")
    set(SDL3_DIR /usr/lib/cmake/SDL3)
endif()

find_package(SDL3 REQUIRED)
find_package(SDL3_image REQUIRED)
find_package(SDL3_ttf REQUIRED)
find_package(SDL3_mixer REQUIRED)
set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)
find_package(OpenMP REQUIRED)

add_library(rlengine STATIC
    src/Engine.cpp
    src/Visuals.cpp
    src/Player.cpp
    src/Spell.cpp
    src/Collision.cpp
    src/Input.cpp
    src/Events.cpp
    src/Structures.cpp
    src/Stats.cpp
    src/Stamina.cpp
    src/Equipment.cpp
    src/Economy.cpp
    src/Audio.cpp
)
target_include_directories(rlengine PUBLIC src)
target_link_libraries(rlengine PUBLIC 
    SDL3::SDL3 
    SDL3_image::SDL3_image 
    SDL3_ttf::SDL3_ttf
    SDL3_mixer::SDL3_mixer
    OpenMP::OpenMP_CXX
)

pybind11_add_module(Game src/bindings.cpp src/MultiEngine.cpp)
target_link_libraries(Game PRIVATE rlengine)