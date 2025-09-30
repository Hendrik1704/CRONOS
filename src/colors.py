"""
ANSI color codes and utilities for terminal output formatting.
"""


class Colors:
    """ANSI color codes for terminal output."""

    # Regular colors
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    # Styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"

    # Background colors
    BG_RED = "\033[101m"
    BG_GREEN = "\033[102m"
    BG_YELLOW = "\033[103m"
    BG_BLUE = "\033[104m"
    BG_MAGENTA = "\033[105m"
    BG_CYAN = "\033[106m"
    BG_WHITE = "\033[107m"

    # Reset
    RESET = "\033[0m"

    @staticmethod
    def colorize(text, color, style=None):
        """
        Apply color and optional style to text.

        Args:
            text (str): The text to colorize
            color (str): The color code (e.g., Colors.YELLOW)
            style (str, optional): Optional style code (e.g., Colors.BOLD)

        Returns:
            str: Formatted text with ANSI codes
        """
        if style:
            return f"{style}{color}{text}{Colors.RESET}"
        return f"{color}{text}{Colors.RESET}"

    @staticmethod
    def yellow(text, bold=False):
        """Convenience method for yellow text."""
        if bold:
            return Colors.colorize(text, Colors.YELLOW, Colors.BOLD)
        return Colors.colorize(text, Colors.YELLOW)

    @staticmethod
    def green(text, bold=False):
        """Convenience method for green text."""
        if bold:
            return Colors.colorize(text, Colors.GREEN, Colors.BOLD)
        return Colors.colorize(text, Colors.GREEN)

    @staticmethod
    def red(text, bold=False):
        """Convenience method for red text."""
        if bold:
            return Colors.colorize(text, Colors.RED, Colors.BOLD)
        return Colors.colorize(text, Colors.RED)
    
    @staticmethod
    def cyan(text, bold=False):
        """Convenience method for cyan text."""
        if bold:
            return Colors.colorize(text, Colors.CYAN, Colors.BOLD)
        return Colors.colorize(text, Colors.CYAN)
