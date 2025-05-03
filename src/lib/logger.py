import logging

def setup_logger(verbose: bool = False, quiet: bool = False):
    """
    Configura el logger para el proyecto.

    Args:
        verbose: Si es True, establece el nivel de log en DEBUG.
        quiet: Si es True, establece el nivel de log en ERROR.
        Default es INFO.
    """
    if verbose:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.ERROR
    else:
        log_level = logging.INFO

    logging.basicConfig(
        format='%(levelname)s: %(message)s',
        level=log_level
    )