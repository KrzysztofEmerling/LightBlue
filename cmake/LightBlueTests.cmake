# lightblue_add_tests(<katalog> [DEPS <modul>...])
#
# Tworzy plik wykonywalny test_<katalog> ze wszystkich tests/<katalog>/*.cpp,
# linkuje go z doctest (wspolny main), engine::options i podanymi modulami,
# a potem rejestruje dwa testy w ctest:
#   <katalog>       - wszystko poza test_suite("slow")   (etykiety: <katalog>)
#   <katalog>.slow  - tylko test_suite("slow")           (etykiety: <katalog>;slow)
#
# Dopoki w katalogu nie ma plikow .cpp, nic nie jest tworzone - wystarczy
# dodac pierwszy plik testow (CONFIGURE_DEPENDS przekonfiguruje projekt).
#
# W kodzie testow dostepne jest makro LIGHTBLUE_TEST_DATA_DIR - sciezka do
# katalogu tests/data/ (napis, bez koncowego '/').
function(lightblue_add_tests name)
    cmake_parse_arguments(ARG "" "" "DEPS" ${ARGN})

    file(GLOB_RECURSE sources CONFIGURE_DEPENDS
        "${CMAKE_CURRENT_SOURCE_DIR}/${name}/*.cpp")
    if(NOT sources)
        return()
    endif()

    set(deps "")
    foreach(dep IN LISTS ARG_DEPS)
        list(APPEND deps engine::${dep})
    endforeach()

    set(target test_${name})
    add_executable(${target} ${sources})
    target_link_libraries(${target} PRIVATE lightblue_test_main ${deps} engine::options)

    add_test(NAME ${name} COMMAND ${target} --test-suite-exclude=slow)
    add_test(NAME ${name}.slow COMMAND ${target} --test-suite=slow)
    set_tests_properties(${name}      PROPERTIES LABELS "${name}")
    set_tests_properties(${name}.slow PROPERTIES LABELS "${name};slow")
endfunction()
