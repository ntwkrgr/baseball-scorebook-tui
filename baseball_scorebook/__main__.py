"""Entry point: python -m baseball_scorebook"""

from baseball_scorebook.app import BaseballScorebookApp


def main() -> None:
    app = BaseballScorebookApp()
    app.run()


if __name__ == "__main__":
    main()
