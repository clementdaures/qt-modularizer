"""Core engines of QtModularizer: ``.ui`` parsing and code generation.
"""

# region Imports & Config

# qt_modularizer/core/..
from .config import ConfigError, ProjectConfig, roles_for_class
from .generator import CodeGenerator, GenerationResult, GeneratorError
from .parser import CustomWidgetInfo, UIParser, UIParserError, WidgetInfo, WidgetNotFoundError

__all__ = [
    "CodeGenerator",
    "GenerationResult",
    "GeneratorError",
    "ConfigError",
    "ProjectConfig",
    "roles_for_class",
    "CustomWidgetInfo",
    "UIParser",
    "UIParserError",
    "WidgetInfo",
    "WidgetNotFoundError",
]

# endregion
