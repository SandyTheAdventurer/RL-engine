cmake_minimum_required(VERSION 3.20)
project(rlengine VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

include(FetchContent)

set(SDL_SHARED        OFF CACHE BOOL "" FORCE)
set(SDL_STATIC        ON  CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)

function(rlengine_fetch name repo tag)
    find_package(${name} QUIET)
    if(NOT ${name}_FOUND)
        message(STATUS "${name} not found locally - fetching ${tag} from source")
        FetchContent_Declare(${name}
            GIT_REPOSITORY ${repo}
            GIT_TAG        ${tag}
            GIT_SHALLOW    TRUE
        )
        FetchContent_MakeAvailable(${name})
    endif()
endfunction()

set(SDL_VERSION_TAG "release-3.4.12")

rlengine_fetch(SDL3       https://github.com/libsdl-org/SDL.git       ${SDL_VERSION_TAG})
rlengine_fetch(SDL3_image https://github.com/libsdl-org/SDL_image.git ${SDL_VERSION_TAG})
rlengine_fetch(SDL3_ttf   https://github.com/libsdl-org/SDL_ttf.git   ${SDL_VERSION_TAG})

set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

add_library(rlengine STATIC
    src/Engine.cpp
    src/Visuals.cpp
    src/Player.cpp
    src/Bullet.cpp
    src/Collision.cpp
    src/Input.cpp
    src/Events.cpp
    src/Structures.cpp
)
target_include_directories(rlengine PUBLIC src)
target_link_libraries(rlengine PUBLIC
    SDL3::SDL3
    SDL3_image::SDL3_image
    SDL3_ttf::SDL3_ttf
)

pybind11_add_module(Game src/bindings.cpp)
target_link_libraries(Game PRIVATE rlengine)