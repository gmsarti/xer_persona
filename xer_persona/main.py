from xer_persona.logging_config import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


def main():
    print("Hello from xer-persona!")


if __name__ == "__main__":
    main()
