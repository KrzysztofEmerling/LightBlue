// Przyklad: jak pisac testy w LightBlue (doctest).
//
// Budowa i uruchomienie:
//   cmake --preset debug && cmake --build --preset debug
//   ctest --preset debug                         # wszystkie testy bez "slow"
//   ctest --preset debug -R example              # tylko ten plik
//   ./build/debug/tests/test_example -s          # bezposrednio, z detalami
//   ./build/debug/tests/test_example -tc="*popcount*"   # wybrane TEST_CASE
//
// Prawdziwe testy modulu leza w tests/<modul>/*.cpp i zalaczaja publiczne
// naglowki modulu, np.:
//   #include <engine/core/bitops.hpp>
// Nowy plik .cpp w tests/<modul>/ zostanie wykryty automatycznie
// (cmake/LightBlueTests.cmake) - nie trzeba edytowac CMakeLists.txt.
//
// Tutaj, zeby przyklad byl samodzielny, testowane funkcje sa zdefiniowane
// w tym pliku. W TDD najpierw powstaja testy (czerwone), dopiero potem
// implementacja w src/<modul>/.

#include <doctest/doctest.h>

#include <bit>
#include <cstdint>
#include <fstream>
#include <stdexcept>
#include <string>

namespace {

// ---- "kod produkcyjny" (normalnie w src/<modul>/) --------------------------

using Bitboard = std::uint64_t;

constexpr int popcount(Bitboard b) {
    int n = 0;
    while (b) {
        b &= b - 1;
        ++n;
    }
    return n;
}

// Zwraca indeks najmlodszego bitu i go zeruje. Wymaga b != 0.
constexpr int popLsb(Bitboard& b) {
    int idx = 0;
    while (((b >> idx) & 1u) == 0) ++idx;
    b &= b - 1;
    return idx;
}

// "e4" -> 28 (a1 = 0, h8 = 63). Rzuca std::invalid_argument dla zlych danych.
int parseSquare(const std::string& s) {
    if (s.size() != 2 || s[0] < 'a' || s[0] > 'h' || s[1] < '1' || s[1] > '8')
        throw std::invalid_argument("zle pole: " + s);
    return 8 * (s[1] - '1') + (s[0] - 'a');
}

}  // namespace

// ---- testy -----------------------------------------------------------------

// TEST_SUITE grupuje przypadki; mozna je potem filtrowac: -ts="example/bitops"
TEST_SUITE("example/bitops") {
    // 1. Najprostszy test: CHECK sprawdza warunek i kontynuuje mimo bledu.
    TEST_CASE("popcount liczy ustawione bity") {
        CHECK(popcount(0) == 0);
        CHECK(popcount(1) == 1);
        CHECK(popcount(0xFFULL) == 8);
        CHECK(popcount(~0ULL) == 64);
    }

    // 2. Testy w czasie kompilacji - dla funkcji constexpr wystarczy static_assert.
    static_assert(popcount(0b1011) == 3);

    // 3. SUBCASE: wspolny "setup" na poczatku, kazdy SUBCASE uruchamia sie
    //    osobno od zera (setup wykonuje sie ponownie dla kazdego z nich).
    TEST_CASE("popLsb zwraca i usuwa najmlodszy bit") {
        Bitboard b = (1ULL << 3) | (1ULL << 40);

        SUBCASE("pierwsze wywolanie") {
            CHECK(popLsb(b) == 3);
            CHECK(b == (1ULL << 40));
        }
        SUBCASE("dwa wywolania oprozniaja bitboard") {
            popLsb(b);
            CHECK(popLsb(b) == 40);
            CHECK(b == 0);
        }
    }

    // 4. REQUIRE przerywa test przy bledzie - uzywaj, gdy dalsze sprawdzenia
    //    nie maja sensu (np. przed dereferencja albo petla po wyniku).
    TEST_CASE("popLsb na wszystkich polach") {
        for (int sq = 0; sq < 64; ++sq) {
            Bitboard b = 1ULL << sq;
            CAPTURE(sq);                 // przy bledzie wypisze wartosc sq
            REQUIRE(popLsb(b) == sq);
            CHECK(b == 0);
        }
    }

}  // TEST_SUITE("example/bitops")

// 5. Wyjatki i wartosci falszywe.
TEST_CASE("parseSquare") {
    CHECK(parseSquare("a1") == 0);
    CHECK(parseSquare("h1") == 7);
    CHECK(parseSquare("e4") == 28);
    CHECK(parseSquare("h8") == 63);

    CHECK_THROWS_AS(parseSquare("i1"), std::invalid_argument);
    CHECK_THROWS_AS(parseSquare("a9"), std::invalid_argument);
    CHECK_THROWS(parseSquare(""));
    CHECK_FALSE(parseSquare("b1") == 0);
}

// 6. Test sterowany danymi z pliku w tests/data/ (np. pozycje FEN, perft).
//    LIGHTBLUE_TEST_DATA_DIR ustawia CMake.
//    Format pliku: "<liczba_hex> <oczekiwany_popcount>", '#' = komentarz.
TEST_CASE("popcount - dane z pliku") {
    std::ifstream in(LIGHTBLUE_TEST_DATA_DIR "/example_popcount.txt");
    REQUIRE(in.is_open());

    int cases = 0;
    std::string line;
    while (std::getline(in, line)) {
        if (line.empty() || line[0] == '#') continue;
        const auto space = line.find(' ');
        const Bitboard b = std::stoull(line.substr(0, space), nullptr, 16);
        const int expected = std::stoi(line.substr(space + 1));
        INFO("linia: ", line);       // kontekst wypisywany przy bledzie
        CHECK(popcount(b) == expected);
        ++cases;
    }
    CHECK(cases > 0);
}

// 7. Testy wolne (np. gleboki perft) oznaczamy test_suite("slow").
//    `ctest --preset debug` je pomija, uruchamia je `ctest --preset release`.
TEST_CASE("popcount na milionach wartosci" * doctest::test_suite("slow")) {
    std::uint64_t x = 0x9E3779B97F4A7C15ULL;
    for (int i = 0; i < 5'000'000; ++i) {
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        REQUIRE(popcount(x) == std::popcount(x));
    }
}
