<p align="center">
  <img src="docs/assets/LightBlue-logo.png" alt="LightBlue" height="160">
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img src="docs/assets/sknf-bozon.png" alt="SKNF Bozon" height="160">
</p>

<h1 align="center">LightBlue</h1>

<p align="center">
  Projekt silnika szachowego w C++20, rozwijany w&nbsp;ramach <b>SKNF Bozon</b>
</p>

---

## O projekcie

**LightBlue** to grupowy projekt Studenckiego Koła Naukowego Fizyków **Bozon**. Mamy trzy cele:

1. **Zbudować silnik szachowy**, który komunikuje się przez protokół UCI i gra w dowolnym GUI.
2. **Sprawdzić, jak wybrane decyzje projektowe wpływają na siłę gry**, czyli porównać warianty (reprezentację planszy, generator pseudolegalny lub legalny, techniki przeszukiwania, ewaluację) i mierzyć różnice testami SPRT.
3. **Dowiedzieć się, jak działają silniki szachowe**: od bitboardów i generowania ruchów po alfa-betę i tablice transpozycji.

Plan projektu wraz z informacjami o zadaniach i postępie prac znajduje się na tablicy
**[GitHub Project](https://github.com/users/KrzysztofEmerling/projects/8/views/7?groupedBy%5BcolumnId%5D=447227562)**.

## Budowanie

Wymagania: kompilator z obsługą C++20 (GCC 11+, Clang 14+) i CMake 3.21+.

```bash
cmake --preset release
cmake --build --preset release
./build/release/src/app/lightblue
```

Dostępne presety:

| Preset       | Do czego                                                          |
| ------------ | ----------------------------------------------------------------- |
| `debug`      | codzienna praca: `-O0 -g`, ASan + UBSan, pełne logowanie          |
| `release`    | `-O3 -ffast-math` (odpowiednik `-Ofast`) + LTO, logowanie włączone |
| `dist`       | jak `release`, ale bez logowania i testów: do pomiarów siły gry   |
| `dist-small` | `-Os` + LTO, bez logowania: najmniejszy plik wykonywalny          |

Każdy preset buduje się do osobnego katalogu `build/<preset>/`.

## Testy

Testy pisane są w [doctest](https://github.com/doctest/doctest) i uruchamiane przez `ctest`:

```bash
cmake --preset debug && cmake --build --preset debug
ctest --preset debug     # codzienne testy (bez test_suite("slow"))
ctest --preset release   # wszystkie testy, razem z wolnymi (głęboki perft)
```

Testy modułu `<moduł>` to pliki `tests/<moduł>/*.cpp`. Nowy plik jest wykrywany automatycznie,
nie trzeba edytować CMake. Dane testowe trzymamy w `tests/data/` (w kodzie: `LIGHTBLUE_TEST_DATA_DIR`).
Przykład z omówieniem najważniejszych makr jest w [`tests/example/example_test.cpp`](tests/example/example_test.cpp).

## Formatowanie

Wspólny styl jest w pliku [`.clang-format`](.clang-format): wcięcie 4 spacje, limit 100 znaków,
klamra otwierająca w tej samej linii, komentarze pozostają nietknięte.

```bash
cmake --build --preset debug --target format        # formatuje src/ i tests/
cmake --build --preset debug --target format-check  # tylko sprawdza (np. przed PR)
```

Większość edytorów (VS Code, CLion, Vim, Emacs) sama odczytuje `.clang-format` i formatuje przy zapisie.

## Struktura repozytorium

```
LightBlue/
├── CMakeLists.txt     # konfiguracja budowy
├── CMakePresets.json  # presety budowy
├── cmake/             # funkcje pomocnicze CMake
├── docs/
│   ├── adr/           # Architecture Decision Records
│   └── assets/        # grafiki
├── src/
│   ├── core/          # typy, operacje bitowe, stałe, logowanie
│   ├── attacks/       # tablice ataków, magic bitboardy
│   ├── board/         # plansza, FEN, Zobrist, make/unmake
│   ├── movegen/       # generator ruchów, perft
│   ├── eval/          # ewaluacja statyczna
│   ├── search/        # przeszukiwanie
│   ├── uci/           # protokół UCI
│   └── app/           # punkt wejścia (main.cpp)
├── tests/             # testy per moduł, dane w tests/data/, przykład w tests/example/
├── scripts/           # narzędzia pomocnicze (liczby magiczne, SPRT)
└── PLAN_PROJEKTU.md   # architektura, konwencje i plan prac
```

Każdy moduł ma publiczne nagłówki w `src/<moduł>/include/engine/<moduł>/` i implementację w `src/<moduł>/src/`.
Zależności idą tylko w dół: `core -> attacks -> board -> movegen / eval -> search -> uci -> app`. Na przykład app może załączyć wszystko, ale uci nie może załączyć app

## Bitboardy i numeracja pól

Stosujemy naturalną numerację pól: `a1 = 0`, `b1 = 1`, …, `h1 = 7`, `a2 = 8`, …, `h8 = 63`
(`square = 8 * rank + file`). Bit `i` bitboardu odpowiada polu `i`.
Bitboardy można podglądać i układać w wizualizatorze online: **[bitboard-editor.vercel.app](https://bitboard-editor.vercel.app/)**

---

<p align="center">
  Projekt rozwijany w ramach <b>SKNF Bozon</b>
</p>
