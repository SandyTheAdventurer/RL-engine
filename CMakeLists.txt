cmake_minimum_required(VERSION 3.20)
project(rlengine VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Multi-config generators (MSVC) ignore CMAKE_BUILD_TYPE and default to Debug,
# which makes the simulation 10-50x slower; restrict to optimized configs.
if(CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_CONFIGURATION_TYPES "Release;RelWithDebInfo" CACHE STRING "" FORCE)
endif()

if(NOT DEFINED SDL3_DIR AND EXISTS "/usr/lib/cmake/SDL3")
    set(SDL3_DIR /usr/lib/cmake/SDL3)
endif()

find_package(SDL3 REQUIRED)
find_package(SDL3_image REQUIRED)
find_package(SDL3_ttf REQUIRED)
find_package(SDL3_mixer REQUIRED)
set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)
# No OpenMP: PyTorch bundles its own OpenMP runtime, and loading a second one
# (libomp on macOS, vcomp on Windows/MSVC) into the same process segfaults.
# MultiEngine parallelizes with std::thread (src/ParallelFor.h) instead.
find_package(Threads REQUIRED)

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
# MSVC hides M_PI behind this define
target_compile_definitions(rlengine PUBLIC _USE_MATH_DEFINES)
target_link_libraries(rlengine PUBLIC
    SDL3::SDL3
    SDL3_image::SDL3_image
    SDL3_ttf::SDL3_ttf
    SDL3_mixer::SDL3_mixer
    Threads::Threads
)

pybind11_add_module(Game src/bindings.cpp src/MultiEngine.cpp)
target_link_libraries(Game PRIVATE rlengine)