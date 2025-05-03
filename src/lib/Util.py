import logging


def read_file(filepath: str) -> bytes:
    try:
        with open(filepath, "rb") as file:
            file_data = file.read()
            return file_data
    except FileNotFoundError:
        logging.error(f"Archivo no encontrado: {filepath}")
        return
