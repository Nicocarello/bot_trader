"""
Abstract Base Module for all AI Trading System Agents.
Enforces strict type contracts.
"""

import abc
from pydantic import BaseModel

class BaseAgent(abc.ABC):
    """
    Abstract interface for all agents within the MVP architecture.
    """
    def __init__(self, name: str):
        self.name = name

    @abc.abstractmethod
    def process(self, *args, **kwargs) -> BaseModel:
        """
        Process the generic inputs and return a strictly typed Pydantic structure.
        Must be implemented by child classes.
        """
        pass
