# LightBlue - plan projektu i struktura repozytorium

> Dokument dla członków zespołu. Opisuje strukturę repozytorium, granice modułów,
> konwencje, testy i kolejność prac.
> Język: C++20 (`<bit>`, `concept`, `if constexpr`).

**Cel nadrzędny:** szybko dojść do silnika, który gra legalne szachy w GUI przez UCI (jedyny kamień milowy: **działający silnik**),
dopiero potem pracować nad siłą gry.

---

## 0. Załorzenia projektowe

LightBlue to projekt mający na celu zaznajomienie się z dizłaniem silników porzez napisanie jednego implementacji. Dodatkowo ma na celu zapoznanie się z podejściem TDD - test driven developement.

- Wiedzę czerpiemy przede wszystkim z [Chessprogramming Wiki](https://www.chessprogramming.org/),
  dokumentacji i kodu innych silników (czytamy, nie kopiujemy).
- Każda nietrywialna decyzja trafia do ADR w `docs/adr/`. Dzięki temu po projekcie zostaje
  zapis tego, czego się nauczyliśmy.

---

## 1. Struktura repozytorium

```
LightBlue/
├── CMakeLists.txt              # root: opcje, wspólne flagi, add_subdirectory modułów
├── CMakePresets.json           # debug, release, dist, dist-small
├── cmake/
│   └── LightBlueModule.cmake   # funkcja lightblue_add_module()
├── README.md
├── PLAN_PROJEKTU.md            # ten plik
├── CONTRIBUTING.md             # zasady PR, Definition of Done, styl
├── .clang-format / .clang-tidy # styl kodu i analiza statyczna
├── docs/
│   ├── adr/                    # Architecture Decision Records: 0001-reprezentacja-ruchu.md, ...
│   └── assets/                 # logo LightBlue, logo SKNF Bozon
├── src/
│   ├── core/                   # typy, operacje bitowe, stałe, logowanie (INFO)
│   │   ├── include/engine/core/   # publiczne nagłówki: types.hpp, bitops.hpp, ...
│   │   ├── src/                   # implementacja (.cpp)
│   │   └── CMakeLists.txt
│   ├── attacks/                # tablice ataków, magic bitboardy, between / line
│   ├── board/                  # Board, FEN, Zobrist, make/unmake, reguły remisu
│   ├── movegen/                # generator pseudolegalny, legalny, perft
│   ├── eval/                   #ewaluacja statyczna
│   ├── search/                 #przeszukiwanie
│   ├── uci/                    # parser komend, controller, I/O
│   └── app/main.cpp            # punkt wejścia, plik wykonywalny `lightblue`
├── tests/
│   ├── core/  attacks/  board/  movegen/  eval/  search/  uci/
│   └── data/
│       ├── fen_positions.txt   # pozycje do testów round-trip i właściwości
│       ├── perft.epd           # pozycje + oczekiwane liczby węzłów
│       └── wac.epd             #pozycje taktyczne
└── scripts/                    # np. generator liczb magicznych, uruchamianie SPRT
```

Każdy moduł w `src/<moduł>/` ma ten sam układ (`include/engine/<moduł>/`, `src/`,
`CMakeLists.txt`) i jest budowany jako biblioteka `engine_<moduł>` (alias `engine::<moduł>`).
Moduł bez plików `.cpp` jest biblioteką nagłówkową (INTERFACE). Po dodaniu pierwszego `.cpp`
CMake sam zrobi z niego bibliotekę statyczną.

Nowy plik `.cpp` wystarczy wrzucić do `src/<moduł>/src/`, bez edytowania CMake.

---

## 2. Architektura - kierunek zależności

Zależności idą **wyłącznie w dół**. Moduł nie może dołączać nagłówków modułu wyżej.

```
core  (types, bitops, log)
  ↓
attacks
  ↓
board
  ↓          ↘
movegen      eval
  ↓          ↓
  search  (zależy od eval i movegen przez szablony/koncepty)
  ↓
uci
  ↓
app (main)
```

Zasady:

- Zależność = argument `DEPS` w `lightblue_add_module()` w `src/<moduł>/CMakeLists.txt`.
  Potrzeba zależności „w górę” oznacza zły podział - zgłosić jako issue / ADR.
- **Gorące ścieżki** (movegen, make/unmake, eval, search): polimorfizm statyczny (szablony + `concept`, `if constexpr`). Bez `virtual`.
- Polimorfizm dynamiczny dozwolony poza gorącymi ścieżkami (UCI, opcje, logowanie).
- Board przyjmuje wyłącznie typ `Move`. Zamiana tekstu (`"e7e8q"`) na `Move` odbywa się w UCI z użyciem generatora ruchów.

---

## 3. Numeracja pól i bitboardy

Przyjmujemy naturalną numerację pól (Little-Endian Rank-File):

```
  8 | 56 57 58 59 60 61 62 63
  7 | 48 49 50 51 52 53 54 55
  6 | 40 41 42 43 44 45 46 47
  5 | 32 33 34 35 36 37 38 39
  4 | 24 25 26 27 28 29 30 31
  3 | 16 17 18 19 20 21 22 23
  2 |  8  9 10 11 12 13 14 15
  1 |  0  1  2  3  4  5  6  7
    +------------------------
       a  b  c  d  e  f  g  h
```

- `a1 = 0`, `b1 = 1`, …, `h1 = 7`, `a2 = 8`, …, `h8 = 63`.
- `square = 8 * rank + file`, gdzie `file` (a-h) i `rank` (1-8) liczone od 0.
- Bit `i` bitboardu (`uint64_t`) odpowiada polu `i`: `1ULL << sq`.
- Przesunięcia: `<< 8` to ruch w górę o jedną linię (w stronę czarnych), `<< 1` to ruch w prawo
  (uwaga na zawijanie przez kolumnę a/h).

Do podglądu i układania bitboardów używamy wizualizatora:
**<https://bitboard-editor.vercel.app/>**

---

## 4. Moduły - odpowiedzialność i API

### core

- Silne typy: `Square`, `Piece`, `PieceType`, `Color`, `Bitboard` (`uint64_t`), `Move`.
- `Square` zgodny z numeracją z sekcji 3 (`A1 = 0` … `H8 = 63`).
- `Move`: 16 bitów - from (6), to (6), flagi (4: promocja, roszada, en passant, bicie).
- `bitops.hpp`: `popcount`, `lsb` (`std::countr_zero`), `msb` (`std::countl_zero`), `pop_lsb`. Wyłącznie przez `<bit>`, bez `__builtin_*`.
- `log.hpp`: makro `INFO(level, ...)`; poziom ustalany w czasie kompilacji (`ENGINE_LOG_LEVEL`), przy `ENGINE_INFO=0` znika całkowicie.
- Stałe: tablice LUT, maski plików/linii, `MAX_MOVES`, `MAX_PLY` itp.

### attacks

- Ataki figur skaczących: skoczek, król, pionki (tablice LUT).
- Ataki figur liniowych: magic bitboardy (gońce, wieże; hetman = suma).
- Tablice `between(a, b)` i `line(a, b)` - pola między dwoma polami i cała linia przez nie (piny, blokowanie szacha).
- Wspólny interfejs `attacks<PieceType>(Square, Bitboard occupancy)` oraz ataki wszystkich pionów z bitboardu.
- Moduł zna tylko pola i zajętość planszy - funkcje wymagające położenia figur (np. `attackersTo`) są w board.

### board

- Bitboardy per figura i kolor + `Piece mailbox[64]`.
- Stan: strona na ruchu, prawa roszady, pole en passant, licznik 50 ruchów, numer ruchu, hash Zobrist.
- `checkers` i `pinned` (Bitboard) przeliczane w `make()`.
- Stos stanów do `unmake()` (prawa roszady, en passant, licznik 50 ruchów, zbita figura, hash).
- Historia hashy do wykrywania trzykrotnego powtórzenia.
- API:
  - `void setFen(std::string_view)`, `std::string toFen() const`
  - `void make(Move)`, `void unmake(Move)`
  - `Color sideToMove() const`
  - `bool inCheck() const`, `bool isKingInCheck(Color) const`
  - `Bitboard attackersTo(Square s, Bitboard occupancy) const` - używane przez board i movegen
  - `bool isDrawByRule() const` - 50 ruchów, powtórzenia, niewystarczający materiał
  - `uint64_t hash() const`
  - `bool isConsistent() const` - tylko debug: bitboardy == mailbox, hash == przeliczony od zera
- Klucze Zobrist losowane deterministycznie (stały seed).

### movegen

- Szablon `generate<GenType>(const Board&, MoveList&)`, `GenType` ∈ {`CAPTURES`, `QUIETS`, `EVASIONS`, `PSEUDO`, `LEGAL`}.
- Generator pseudolegalny i generator legalny (piny, szachy, uniki) za wspólnym konceptem:
  ```cpp
  template<typename G>
  concept MoveGenerator = requires(const Board& b, MoveList& l) {
      G::generate(b, l);
      { G::needsLegalityCheck } -> std::convertible_to<bool>;
  };
  ```
- `uint64_t perft(Board&, int depth)` oraz `perftDivide`.
- Wykrywanie mata i pata (wymaga generatora - dlatego nie w board).

### uci

Trzy warstwy:

1. **Parser** - czysta funkcja `std::string_view -> Command` (`std::variant`).
2. **Controller** - maszyna stanów (`uci`, `isready`, `ucinewgame`, `position`, `go`, `stop`, `setoption`, `quit`), działa na `std::istream&` / `std::ostream&` (testowalny przez `std::stringstream`).
3. **I/O** - wątek czytający stdin, search w osobnym wątku, `std::atomic<bool> stop`.

Komendy niestandardowe (debug): `d` (wypisz planszę i FEN), `perft N`, `bench`.

### search

- Jeden moduł sparametryzowany generatorem - **nie** dwa osobne searche:
  ```cpp
  template<MoveGenerator Gen>
  int search(Board& b, int alpha, int beta, int depth, int ply) {
      MoveList moves; Gen::generate(b, moves);
      int legal = 0;
      const Color us = b.sideToMove();
      for (Move m : moves) {
          b.make(m);
          if constexpr (Gen::needsLegalityCheck)
              if (b.isKingInCheck(us)) { b.unmake(m); continue; }  // ruch pseudolegalny odsłonił króla
          ++legal;
          int score = -search<Gen>(b, -beta, -alpha, depth - 1, ply + 1);
          b.unmake(m);
          // alpha/beta; LMR/LMP liczone po `legal`
      }
      if (legal == 0) return b.inCheck() ? -MATE + ply : 0;
      // ...
  }
  ```
- Alfa-beta + iterative deepening, transposition table, kolejność ruchów, zarządzanie czasem.

### eval

- Start: materiał + tablice pozycyjne (PST). Decyzja klasyczna ewaluacja vs NNUE - osobny ADR.

---

## 5. Build system

Opcje CMake:

| Opcja                                | Wartości                     | Znaczenie                                                       |
| ------------------------------------ | ---------------------------- | --------------------------------------------------------------- |
| `CMAKE_BUILD_TYPE`                   | Debug / Release / MinSizeRel | `-O0 -g` / `-O3` / `-Os`                                        |
| `ENGINE_FAST_MATH`                   | ON / OFF                     | w Release `-ffast-math` (razem z `-O3` = `-Ofast`)              |
| `ENGINE_TESTS`                       | ON / OFF                     | budowa testów (doctest + ctest)                                 |
| `ENGINE_INFO`                        | ON / OFF                     | makro `INFO` aktywne lub usunięte (definicja `ENGINE_INFO=1/0`) |
| `ENGINE_LOG_LEVEL`                   | 0-3                          | poziom szczegółowości `INFO` (definicja `ENGINE_LOG_LEVEL=n`)   |
| `ENGINE_SANITIZERS`                  | ON / OFF                     | ASan + UBSan                                                    |
| `CMAKE_INTERPROCEDURAL_OPTIMIZATION` | ON / OFF                     | LTO                                                             |
| `CMAKE_UNITY_BUILD`                  | ON / OFF                     | alternatywa dla LTO (bez presetu, ręcznie `-D`)                 |

Presety (`CMakePresets.json`):

| Preset       | Typ                         | INFO          | Sanitizery | LTO | Testy |
| ------------ | --------------------------- | ------------- | ---------- | --- | ----- |
| `debug`      | Debug                       | ON (poziom 3) | ON         | OFF | ON    |
| `release`    | Release (`-O3 -ffast-math`) | ON            | OFF        | ON  | ON    |
| `dist`       | Release (`-O3 -ffast-math`) | OFF           | OFF        | ON  | OFF   |
| `dist-small` | MinSizeRel (`-Os`)          | OFF           | OFF        | ON  | OFF   |

`-O3 -ffast-math`. Sanitizery w `debug` można wyłączyć: `cmake --preset debug -DENGINE_SANITIZERS=OFF`.

```bash
cmake --preset debug             # konfiguracja do build/debug/
cmake --build --preset debug     # budowa
./build/debug/src/app/lightblue
```

Wspólne flagi (ostrzeżenia, sanitizery, definicje) są w bibliotece `engine::options`,
którą każdy moduł linkuje prywatnie.

W buildzie debug po każdym `make()` wykonywane jest `assert(board.isConsistent())`.

---

## 6. Testy (TDD)

Framework: **doctest** (`ctest` uruchamia pliki testów każdego modułu).

Workflow dla każdego zadania:

1. Kryteria akceptacji z issue -> lista `TEST_CASE`.
2. Najpierw commit z testami, które nie przechodzą (czerwone).
3. Implementacja aż testy przejdą, potem refaktor.
4. Merge dopiero gdy wszystkie testy przechodzą.

Poziomy testów:

| Poziom      | Co                                          | Przykłady                                                                                   |
| ----------- | ------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Jednostkowe | małe, deterministyczne funkcje              | `pop_lsb`, kodowanie `Move`, parser UCI                                                     |
| Właściwości | niezmienniki na wielu pozycjach             | make+unmake przywraca stan; hash inkrementalny == od zera; FEN round-trip; `isConsistent()` |
| Różnicowe   | dwa niezależne algorytmy dają ten sam wynik | `generate<LEGAL>` == `generate<PSEUDO>` bez ruchów zostawiających króla w szachu      |
| Perft       | znane liczby węzłów                         | pozycja startowa, Kiwipete, pozycje 3-6 z Chessprogramming Wiki                             |
| UCI         | skrypty komend na `stringstream`            | `uci` -> `uciok`, `isready` -> `readyok`, `go` -> legalny `bestmove`                        |
| Siła gry    | nie da się w testach jednostkowych          | EPD (WAC), sygnatura `bench`, SPRT (fastchess / cutechess-cli)                              |

Przykłady:

```cpp
TEST_CASE("make + unmake przywraca identyczny stan") {
    for (auto fen : testPositions) {
        Board b; b.setFen(fen);
        const Board before = b;
        MoveList moves; generate<LEGAL>(b, moves);
        for (Move m : moves) {
            b.make(m);
            CHECK(b.hash() == computeHashFromScratch(b));
            CHECK(b.isConsistent());
            b.unmake(m);
            CHECK(b == before);
        }
    }
}

TEST_CASE("FEN round-trip") {
    for (auto fen : testPositions) {
        Board b; b.setFen(fen);
        CHECK(b.toFen() == fen);
    }
}

TEST_CASE("perft kiwipete" * doctest::test_suite("slow")) {
    Board b; b.setFen(KIWIPETE);
    CHECK(perft(b, 4) == 4085603);
}
```

- Testy oznaczone `test_suite("slow")` (głęboki perft) uruchamiane w buildzie release, poza codziennym cyklem
  (`ctest --preset debug` je pomija, `ctest --preset release` uruchamia wszystko).
- Pliki `tests/<moduł>/*.cpp` są wykrywane automatycznie (`cmake/LightBlueTests.cmake`), wspólny `main()` jest w `tests/main.cpp`.
- Przykład z omówieniem makr doctest: `tests/example/example_test.cpp`.
- Dane testowe tylko w `tests/data/`, nie zaszyte w kodzie (poza małymi przypadkami).

---

## 7. Postęp prac

Jedynym kamieniem milowym jest **działający silnik** (gra legalne szachy w GUI przez UCI).
Mniejszych etapów nie stosujemy - pracę dzielą moduły. Każde zadanie = jedno issue (1-3 dni pracy)
z nazwą modułu w tytule: `[<moduł>] Opis zadania` (np. `[core] Operacje bitowe`).

<!-- progress:start -->
| Moduł | Postęp | % | Zamknięte / wszystkie |
| ----- | ------ | - | --------------------- |
| [`core`](https://github.com/KrzysztofEmerling/LightBlue/issues?q=is%3Aissue+%22%5Bcore%5D%22+in%3Atitle) | `░░░░░░░░░░░░░░░░░░░░` | 0% | 0 / 5 |
| [`attacks`](https://github.com/KrzysztofEmerling/LightBlue/issues?q=is%3Aissue+%22%5Battacks%5D%22+in%3Atitle) | `░░░░░░░░░░░░░░░░░░░░` | 0% | 0 / 4 |
| [`board`](https://github.com/KrzysztofEmerling/LightBlue/issues?q=is%3Aissue+%22%5Bboard%5D%22+in%3Atitle) | `░░░░░░░░░░░░░░░░░░░░` | 0% | 0 / 8 |
| [`movegen`](https://github.com/KrzysztofEmerling/LightBlue/issues?q=is%3Aissue+%22%5Bmovegen%5D%22+in%3Atitle) | `░░░░░░░░░░░░░░░░░░░░` | - | 0 / 0 |
| [`eval`](https://github.com/KrzysztofEmerling/LightBlue/issues?q=is%3Aissue+%22%5Beval%5D%22+in%3Atitle) | `░░░░░░░░░░░░░░░░░░░░` | - | 0 / 0 |
| [`search`](https://github.com/KrzysztofEmerling/LightBlue/issues?q=is%3Aissue+%22%5Bsearch%5D%22+in%3Atitle) | `░░░░░░░░░░░░░░░░░░░░` | - | 0 / 0 |
| [`uci`](https://github.com/KrzysztofEmerling/LightBlue/issues?q=is%3Aissue+%22%5Buci%5D%22+in%3Atitle) | `░░░░░░░░░░░░░░░░░░░░` | - | 0 / 0 |
| [`app`](https://github.com/KrzysztofEmerling/LightBlue/issues?q=is%3Aissue+%22%5Bapp%5D%22+in%3Atitle) | `░░░░░░░░░░░░░░░░░░░░` | - | 0 / 0 |
| [`infra`](https://github.com/KrzysztofEmerling/LightBlue/issues?q=is%3Aissue+%22%5Binfra%5D%22+in%3Atitle) | `░░░░░░░░░░░░░░░░░░░░` | 0% | 0 / 1 |
| **Działający silnik** | `░░░░░░░░░░░░░░░░░░░░` | 0% | 0 / 18 |
<!-- progress:end -->

Tabelę aktualizuje automatycznie workflow `.github/workflows/progress.yml` po każdej zmianie issues
(otwarcie, zamknięcie, zmiana etykiet). Liczone są issues z prefiksem `[<moduł>]` w tytule
lub etykietą `module:<nazwa>`, bez pull requestów i bez issues z etykietą `epic`. Ręczne przeliczenie: *Actions -> Postęp modułów -> Run workflow*.

---

## 8. Organizacja pracy (GitHub Project)

- Hierarchia: **Milestone** `Działający silnik` -> **moduł** (prefiks `[<moduł>]` w tytule) -> **Task** (1-3 dni).
- Etykiety: `module:<nazwa>`, `type:feature|bug|test|infra`, `good-first-issue`.
- Każde issue ma sekcję **Kryteria akceptacji** (= lista testów).
- **Definition of Done:** testy przechodzą, kod sformatowany `clang-format`, review innej osoby,
  autor potrafi wyjaśnić każdą linijkę swojego kodu.
- Decyzje architektoniczne zapisywane jako ADR w `docs/adr/`.

---

## 9. Zasady pracy w repo

1. Nie łam kierunku zależności z sekcji 2. Nowa zależność między modułami wymaga ADR.
2. Zacznij od testów odpowiadających kryteriom akceptacji zadania; potem implementacja, najlepiej nie pisać implementacji modułu do której pisało się testy.
3. Nie używaj `virtual` ani alokacji na stercie w gorących ścieżkach (movegen, make/unmake, eval, search).
4. Operacje bitowe tylko przez `engine/core/bitops.hpp`.
5. Pola numerujemy zgodnie z sekcją 3. Nowe maski i tablice sprawdzaj w wizualizatorze.
6. Po wprowadzeniu zmian przeprowadzaj odpowiednie testy.
7. Nie zmieniaj oczekiwanych liczb perft ani danych w `tests/data/` bez wyraźnego powodu w opisie PR.
