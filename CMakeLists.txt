cmake_minimum_required(VERSION 3.21)

project(LightBlue
    VERSION 0.1.0
    DESCRIPTION "Silnik szachowy rozwijany w ramach SKNF Bozon"
    LANGUAGES CXX)

if(PROJECT_IS_TOP_LEVEL AND NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Debug CACHE STRING "Typ budowy" FORCE)
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Opcje
option(ENGINE_INFO       "Wlacz makro INFO (logowanie)" ON)
set(ENGINE_LOG_LEVEL 1 CACHE STRING "Poziom szczegolowosci INFO (0-3)")
set_property(CACHE ENGINE_LOG_LEVEL PROPERTY STRINGS 0 1 2 3)
option(ENGINE_SANITIZERS "Buduj z AddressSanitizer + UBSan" OFF)
option(ENGINE_FAST_MATH  "W buildzie Release: -O3 -ffast-math (odpowiednik -Ofast)" ON)
option(ENGINE_TESTS      "Buduj testy (doctest + ctest)" ${PROJECT_IS_TOP_LEVEL})

if(NOT ENGINE_LOG_LEVEL MATCHES "^[0-3]$")
    message(FATAL_ERROR "ENGINE_LOG_LEVEL musi byc liczba 0-3, jest: ${ENGINE_LOG_LEVEL}")
endif()

# LTO wlaczane przez CMAKE_INTERPROCEDURAL_OPTIMIZATION=ON
if(CMAKE_INTERPROCEDURAL_OPTIMIZATION)
    include(CheckIPOSupported)
    check_ipo_supported(RESULT _ipo_ok OUTPUT _ipo_msg)
    if(NOT _ipo_ok)
        message(WARNING "LTO nie jest wspierane przez kompilator: ${_ipo_msg}")
        set(CMAKE_INTERPROCEDURAL_OPTIMIZATION OFF)
    endif()
endif()

# Wspolne ustawienia kompilacji dla wszystkich modulow
add_library(engine_options INTERFACE)
add_library(engine::options ALIAS engine_options)

target_compile_definitions(engine_options INTERFACE
    ENGINE_INFO=$<BOOL:${ENGINE_INFO}>
    ENGINE_LOG_LEVEL=${ENGINE_LOG_LEVEL})

if(MSVC)
    target_compile_options(engine_options INTERFACE /W4 /permissive-)
else()
    target_compile_options(engine_options INTERFACE -Wall -Wextra -Wpedantic -Wshadow -Wconversion)
endif()

# -Ofast jest przestarzale w GCC 14+ i Clang 18+ (ostrzezenie przy kazdym pliku),
# dlatego uzywamy rownowaznego -O3 -ffast-math. Silnik liczy glownie na
# liczbach calkowitych, wiec fast-math praktycznie nie zmienia wynikow.
if(ENGINE_FAST_MATH)
    if(MSVC)
        target_compile_options(engine_options INTERFACE $<$<CONFIG:Release>:/fp:fast>)
    else()
        target_compile_options(engine_options INTERFACE $<$<CONFIG:Release>:-ffast-math>)
        target_link_options(engine_options INTERFACE $<$<CONFIG:Release>:-ffast-math>)
    endif()
endif()

if(ENGINE_SANITIZERS)
    if(MSVC)
        # ASan w MSVC nie dziala razem z /RTC1 (domyslnie w Debug)
        string(REGEX REPLACE "/RTC[1csu]*" "" CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG}")
        target_compile_options(engine_options INTERFACE /fsanitize=address)
    else()
        target_compile_options(engine_options INTERFACE
            -fsanitize=address,undefined -fno-omit-frame-pointer)
        target_link_options(engine_options INTERFACE -fsanitize=address,undefined)
    endif()
endif()

include(cmake/LightBlueModule.cmake)

# Moduly (kolejnosc = kierunek zaleznosci)
add_subdirectory(src/core)
add_subdirectory(src/attacks)
add_subdirectory(src/board)
add_subdirectory(src/movegen)
add_subdirectory(src/eval)
add_subdirectory(src/search)
add_subdirectory(src/uci)
add_subdirectory(src/app)

# Formatowanie (clang-format, styl w .clang-format)
find_program(CLANG_FORMAT_EXE NAMES clang-format)
if(CLANG_FORMAT_EXE)
    file(GLOB_RECURSE _format_files CONFIGURE_DEPENDS
        "${PROJECT_SOURCE_DIR}/src/*.cpp" "${PROJECT_SOURCE_DIR}/src/*.hpp"
        "${PROJECT_SOURCE_DIR}/tests/*.cpp" "${PROJECT_SOURCE_DIR}/tests/*.hpp")
    add_custom_target(format
        COMMAND ${CLANG_FORMAT_EXE} -i ${_format_files}
        COMMENT "clang-format: formatowanie zrodel" VERBATIM)
    add_custom_target(format-check
        COMMAND ${CLANG_FORMAT_EXE} --dry-run --Werror ${_format_files}
        COMMENT "clang-format: sprawdzanie formatowania" VERBATIM)
endif()

# Testy (doctest + ctest), zobacz tests/CMakeLists.txt
if(ENGINE_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

message(STATUS "LightBlue: typ=${CMAKE_BUILD_TYPE} INFO=${ENGINE_INFO} "
               "LOG_LEVEL=${ENGINE_LOG_LEVEL} sanitizery=${ENGINE_SANITIZERS} "
               "LTO=${CMAKE_INTERPROCEDURAL_OPTIMIZATION} fast-math=${ENGINE_FAST_MATH} "
               "testy=${ENGINE_TESTS} unity=${CMAKE_UNITY_BUILD}")
