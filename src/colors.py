"""ANSI Color Terminal Formatting Utilities for CRONOS.

This module provides comprehensive ANSI escape code utilities for colored terminal
output in CRONOS heavy-ion collision simulations. It enables enhanced user experience
through color-coded logging, progress indicators, and error reporting in both
interactive and cluster environments.

Features:
- Complete ANSI color palette (foreground and background)
- Text styling (bold, dim, underline, blink)
- Convenient color methods with optional bold styling
- Cross-platform terminal compatibility
- Integration with CRONOS logging and checkpoint systems

Usage:
    from src.colors import Colors
    
    # Basic colored text
    print(Colors.green("Simulation completed successfully!"))
    print(Colors.red("Error: Memory allocation failed", bold=True))
    
    # Custom color combinations
    message = Colors.colorize("Custom warning", Colors.YELLOW, Colors.BOLD)
    logging.info(message)

Integration:
    Used throughout CRONOS for:
    - Checkpoint status reporting (green/yellow/red indicators)
    - Memory monitoring alerts (red warnings, yellow cautions)
    - Module execution progress (colored module names)
    - Error analysis and diagnostic output
    - SLURM job submission feedback

Compatibility:
    - Linux terminal environments (bash, zsh, etc.)
    - SSH sessions with TERM environment variable set
    - SLURM job logs (colors preserved in terminal output)
    - VS Code integrated terminal

Author: CRONOS Development Team
Requires: No external dependencies (pure Python ANSI codes)
"""


class Colors:
    """ANSI escape code utilities for colored terminal output in CRONOS simulations.
    
    Provides a comprehensive set of ANSI color codes, text styles, and convenience
    methods for enhancing terminal output readability. Designed specifically for
    heavy-ion collision simulation workflows where colored output improves user
    experience in both interactive and batch processing environments.
    
    Class Attributes:
        Color codes (foreground):
            RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE
        
        Text styling:
            BOLD, DIM, UNDERLINE, BLINK
        
        Background colors:
            BG_RED, BG_GREEN, BG_YELLOW, BG_BLUE, BG_MAGENTA, BG_CYAN, BG_WHITE
        
        Control:
            RESET: Clears all formatting
    
    Methods:
        colorize(): Apply custom color and style combinations
        yellow(), green(), red(), cyan(): Convenience methods with optional bold
    
    Example:
        >>> # Simulation status indicators
        >>> print(Colors.green("✓ KoMPoST completed", bold=True))
        >>> print(Colors.yellow("⚠ High memory usage detected"))
        >>> print(Colors.red("✗ MUSIC failed - out of memory", bold=True))
        
        >>> # Custom combinations
        >>> warning = Colors.colorize("CHECKPOINT", Colors.YELLOW, Colors.BOLD)
        >>> error_bg = Colors.colorize(" ERROR ", Colors.WHITE, Colors.BG_RED)
    
    Notes:
        - All methods return strings with embedded ANSI escape sequences
        - Colors are automatically reset after each formatted string
        - Safe to use in environments without color support (codes ignored)
        - Optimized for dark terminal backgrounds (standard in HPC environments)
    """

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
        """Apply ANSI color and optional styling to text with automatic reset.
        
        Core formatting method that combines color and style codes with automatic
        reset handling. Used as the foundation for all color convenience methods
        and enables custom color combinations for specialized output formatting.
        
        Args:
            text (str): The text content to format with color/style
            color (str): ANSI color code (use Colors class constants):
                - Colors.RED, Colors.GREEN, Colors.YELLOW, etc.
                - Colors.BG_RED, Colors.BG_GREEN, etc. for backgrounds
            style (str, optional): ANSI style code for text formatting:
                - Colors.BOLD: Bold/bright text weight
                - Colors.DIM: Reduced intensity/faded appearance
                - Colors.UNDERLINE: Underlined text
                - Colors.BLINK: Blinking text (terminal dependent)
        
        Returns:
            str: Formatted text with embedded ANSI escape sequences:
                - Format: [style][color]text[RESET]
                - Automatically includes Colors.RESET to prevent color bleeding
                - Safe for concatenation and logging integration
        
        Examples:
            >>> # Basic color application
            >>> red_text = Colors.colorize("Error message", Colors.RED)
            >>> print(red_text)  # Displays in red, then resets
            
            >>> # Color with styling
            >>> alert = Colors.colorize("CRITICAL", Colors.RED, Colors.BOLD)
            >>> print(alert)  # Bold red text
            
            >>> # Background color combination
            >>> highlight = Colors.colorize("ATTENTION", Colors.WHITE, Colors.BG_RED)
            >>> print(highlight)  # White text on red background
        
        Notes:
            - Colors.RESET is automatically appended to prevent formatting bleed
            - Multiple styles can be combined by manual concatenation if needed
            - Terminal compatibility varies for advanced styles (blink, etc.)
        """
        if style:
            return f"{style}{color}{text}{Colors.RESET}"
        return f"{color}{text}{Colors.RESET}"

    @staticmethod
    def yellow(text, bold=False):
        """Format text in yellow for warnings and informational messages.
        
        Commonly used in CRONOS for checkpoint resumption notifications,
        memory usage warnings, and general informational output.
        
        Args:
            text (str): Text content to format in yellow
            bold (bool): Apply bold styling for emphasis (default: False)
        
        Returns:
            str: Yellow-colored text with optional bold styling
        
        Examples:
            >>> Colors.yellow("Resuming from checkpoint")
            >>> Colors.yellow("High memory usage detected", bold=True)
        """
        if bold:
            return Colors.colorize(text, Colors.YELLOW, Colors.BOLD)
        return Colors.colorize(text, Colors.YELLOW)

    @staticmethod
    def green(text, bold=False):
        """Format text in green for success and completion messages.
        
        Standard color for positive status indicators in CRONOS including
        successful module completion, checkpoint creation, and simulation
        progress confirmations.
        
        Args:
            text (str): Text content to format in green
            bold (bool): Apply bold styling for emphasis (default: False)
        
        Returns:
            str: Green-colored text with optional bold styling
        
        Examples:
            >>> Colors.green("✓ MUSIC completed successfully")
            >>> Colors.green("Simulation prepared", bold=True)
        """
        if bold:
            return Colors.colorize(text, Colors.GREEN, Colors.BOLD)
        return Colors.colorize(text, Colors.GREEN)

    @staticmethod
    def red(text, bold=False):
        """Format text in red for errors and critical failures.
        
        Primary color for error reporting in CRONOS including module failures,
        memory errors, configuration problems, and critical system issues
        requiring immediate attention.
        
        Args:
            text (str): Text content to format in red
            bold (bool): Apply bold styling for emphasis (default: False)
        
        Returns:
            str: Red-colored text with optional bold styling
        
        Examples:
            >>> Colors.red("✗ SMASH failed: out of memory")
            >>> Colors.red("CRITICAL ERROR", bold=True)
        """
        if bold:
            return Colors.colorize(text, Colors.RED, Colors.BOLD)
        return Colors.colorize(text, Colors.RED)

    @staticmethod
    def cyan(text, bold=False):
        """Format text in cyan for headers and section dividers.
        
        Used in CRONOS for section headers, detailed status breakdowns,
        and organizational elements in complex output displays like
        checkpoint summaries and memory analysis reports.
        
        Args:
            text (str): Text content to format in cyan
            bold (bool): Apply bold styling for emphasis (default: False)
        
        Returns:
            str: Cyan-colored text with optional bold styling
        
        Examples:
            >>> Colors.cyan("=== Module Configuration ===", bold=True)
            >>> Colors.cyan("Memory Analysis:")
        """
        if bold:
            return Colors.colorize(text, Colors.CYAN, Colors.BOLD)
        return Colors.colorize(text, Colors.CYAN)
