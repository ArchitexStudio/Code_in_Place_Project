"""All-Time Offense vs All-Time Defense Simulator."""

import sys

MIN_PYTHON = (3, 10)


def _check_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        print(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required (nflreadpy dependency).\n"
            f"You are running Python {sys.version_info.major}.{sys.version_info.minor}."
        )
        sys.exit(1)


def main() -> None:
    """Run the interactive console game."""
    _check_python_version()

    from src.draft.flow import print_rules, run_draft
    from src.simulation.game import print_game_result, simulate_game

    print_rules()

    while True:
        try:
            state = run_draft()
            result = simulate_game(state)
            print_game_result(state, result)
        except KeyboardInterrupt:
            print("\n\nThanks for playing!")
            break
        except Exception as exc:
            print(f"\nError: {exc}")
            print("Please try again.")

        again = input("\nPlay again? (y/n): ").strip().lower()
        if again not in {"y", "yes"}:
            print("Thanks for playing!")
            break


if __name__ == "__main__":
    main()
