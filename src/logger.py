from loguru import logger

logger.add("logs/file_{time}.log", level="INFO")
