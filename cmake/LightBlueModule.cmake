# lightblue_add_module(<nazwa> [DEPS <modul>...])
#
# Tworzy biblioteke engine_<nazwa> (alias engine::<nazwa>) z katalogu
# src/<nazwa>/:
#   include/engine/<nazwa>/*.hpp  - publiczne naglowki
#   src/*.cpp                     - implementacja
#
# Dopoki modul nie ma plikow .cpp, jest biblioteka INTERFACE (same naglowki).
# Po dodaniu pierwszego .cpp staje sie biblioteka statyczna - wystarczy
# ponownie uruchomic konfiguracje (CONFIGURE_DEPENDS robi to automatycznie).
function(lightblue_add_module name)
    cmake_parse_arguments(ARG "" "" "DEPS" ${ARGN})

    set(target engine_${name})
    file(GLOB_RECURSE sources CONFIGURE_DEPENDS
        "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp")

    set(deps "")
    foreach(dep IN LISTS ARG_DEPS)
        list(APPEND deps engine::${dep})
    endforeach()

    if(sources)
        add_library(${target} STATIC ${sources})
        target_include_directories(${target} PUBLIC
            "${CMAKE_CURRENT_SOURCE_DIR}/include")
        target_link_libraries(${target}
            PUBLIC  ${deps}
            PRIVATE engine::options)
    else()
        add_library(${target} INTERFACE)
        target_include_directories(${target} INTERFACE
            "${CMAKE_CURRENT_SOURCE_DIR}/include")
        target_link_libraries(${target} INTERFACE ${deps})
    endif()

    add_library(engine::${name} ALIAS ${target})
endfunction()
