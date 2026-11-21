# doctest: najpierw szukamy w systemie, w przeciwnym razie pobieramy naglowek
# (tylko pliki zrodlowe - bez budowania projektu doctest).
find_package(doctest 2.4 CONFIG QUIET)
if(NOT doctest_FOUND)
    include(FetchContent)
    FetchContent_Declare(doctest
        URL https://github.com/doctest/doctest/archive/refs/tags/v2.4.12.tar.gz
        URL_HASH SHA256=73381c7aa4dee704bd935609668cf41880ea7f19fa0504a200e13b74999c2d70
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
        SOURCE_SUBDIR do-not-add-subdirectory)
    FetchContent_MakeAvailable(doctest)
    add_library(doctest_headers INTERFACE)
    # SYSTEM: ostrzezenia z naglowka doctest nie mieszaja sie z naszymi
    target_include_directories(doctest_headers SYSTEM INTERFACE "${doctest_SOURCE_DIR}")
    add_library(doctest::doctest ALIAS doctest_headers)
endif()

# Wspolny main() dla wszystkich plikow testow
add_library(lightblue_test_main OBJECT main.cpp)
target_link_libraries(lightblue_test_main PUBLIC doctest::doctest engine::options)
target_compile_definitions(lightblue_test_main PUBLIC
    LIGHTBLUE_TEST_DATA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/data")

include(${PROJECT_SOURCE_DIR}/cmake/LightBlueTests.cmake)

# Testy per modul: tests/<modul>/*.cpp -> test_<modul>
lightblue_add_tests(core    DEPS core)
lightblue_add_tests(attacks DEPS attacks)
lightblue_add_tests(board   DEPS board)
lightblue_add_tests(movegen DEPS movegen)
lightblue_add_tests(eval    DEPS eval)
lightblue_add_tests(search  DEPS search)
lightblue_add_tests(uci     DEPS uci)

# Przyklad pokazujacy jak pisac testy (nie zalezy od zadnego modulu)
lightblue_add_tests(example)
