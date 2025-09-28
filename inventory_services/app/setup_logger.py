import logging
import logging.config
import os

import dotenv

dotenv.load_dotenv()


def get_log_level() -> str:
    """Returns logging level depending on the environment."""
    return "DEBUG" if os.getenv("DEVELOPMENT", "False") == "True" else "INFO"


def build_logging_config() -> dict:
    """Builds logging config for all loggers under planner_calc package."""
    level = get_log_level()
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "colored": {
                "()": "colorlog.ColoredFormatter",
                "format": (
                    "%(log_color)s%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "log_colors": {
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
            },
            "simple": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "my_stdout": {
                "class": "logging.StreamHandler",
                "formatter": "colored",
                "stream": "ext://sys.stdout",
            },
            "my_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "simple",
                "filename": "output.log",
                "maxBytes": 10485760,
                "backupCount": 5,
            },
        },
        "root": {
            "handlers": ["my_stdout", "my_file"],
            "level": level,
        },
    }


def setup_logging() -> None:
    """Sets up logging only for the project package."""
    logging.config.dictConfig(build_logging_config())
