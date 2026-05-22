"""
infrastructure/interfaces.py — Abstract interfaces (TASK 2.2).
All concrete implementations depend on these interfaces.
Tests use mock implementations.
"""
from abc import ABC, abstractmethod
from typing import Optional


class IADRepository(ABC):
    @abstractmethod
    def get_all_computer_names(self) -> list[str]: ...
    @abstractmethod
    def is_domain_controller(self, name: str) -> Optional[bool]: ...
    @abstractmethod
    def name_exists(self, name: str) -> Optional[bool]: ...
    @abstractmethod
    def get_distinguished_name(self, name: str) -> Optional[str]: ...
    @abstractmethod
    def rename_ad_object(self, dn: str, new_name: str) -> bool: ...


class IPSRunner(ABC):
    @abstractmethod
    def run_script(self, script: str, params: dict, timeout: int = 30): ...
    @abstractmethod
    def run_rename_computer(self, old_name: str, new_name: str) -> bool: ...
    @abstractmethod
    def run_restart_computer(self, name: str) -> bool: ...


class IWMIClient(ABC):
    @abstractmethod
    def get_active_users(self, computer: str) -> list: ...
    @abstractmethod
    def get_active_user(self, computer: str) -> tuple: ...


class IUserNotifier(ABC):
    @abstractmethod
    def notify(self, computer: str, message: str) -> bool: ...


class ISPNManager(ABC):
    @abstractmethod
    def update_spns(self, old_name: str, new_name: str) -> bool: ...


class IAuditLogger(ABC):
    @abstractmethod
    def log(self, operation: str, operator: str, details: str,
            event_id: int = None, is_error: bool = False) -> None: ...
