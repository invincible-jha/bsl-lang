"""Unit tests for bsl.plugins.registry — PluginRegistry, error types,
entry-point loading, and all public methods.
"""
from __future__ import annotations

import importlib.metadata
import logging
from abc import ABC, abstractmethod
from unittest.mock import MagicMock, patch

import pytest

from bsl.plugins.registry import (
    PluginAlreadyRegisteredError,
    PluginNotFoundError,
    PluginRegistry,
)


# ---------------------------------------------------------------------------
# Test fixtures — abstract base and concrete implementations
# ---------------------------------------------------------------------------


class BasePlugin(ABC):
    @abstractmethod
    def run(self) -> str: ...


class ConcretePluginA(BasePlugin):
    def run(self) -> str:
        return "A"


class ConcretePluginB(BasePlugin):
    def run(self) -> str:
        return "B"


class NotAPlugin:
    """Does NOT subclass BasePlugin — used for error path testing."""
    pass


def _fresh_registry(name: str = "test") -> PluginRegistry[BasePlugin]:
    """Return a new empty registry for each test."""
    return PluginRegistry(BasePlugin, name)


# ===========================================================================
# PluginNotFoundError
# ===========================================================================


class TestPluginNotFoundError:
    def test_is_key_error(self) -> None:
        with pytest.raises(KeyError):
            raise PluginNotFoundError("my-plugin", "my-registry")

    def test_has_plugin_name_attribute(self) -> None:
        error = PluginNotFoundError("my-plugin", "my-registry")
        assert error.plugin_name == "my-plugin"

    def test_has_registry_name_attribute(self) -> None:
        error = PluginNotFoundError("my-plugin", "my-registry")
        assert error.registry_name == "my-registry"

    def test_message_contains_plugin_name(self) -> None:
        error = PluginNotFoundError("my-plugin", "my-registry")
        assert "my-plugin" in str(error)


# ===========================================================================
# PluginAlreadyRegisteredError
# ===========================================================================


class TestPluginAlreadyRegisteredError:
    def test_is_value_error(self) -> None:
        with pytest.raises(ValueError):
            raise PluginAlreadyRegisteredError("my-plugin", "my-registry")

    def test_has_plugin_name_attribute(self) -> None:
        error = PluginAlreadyRegisteredError("dup-plugin", "my-registry")
        assert error.plugin_name == "dup-plugin"

    def test_has_registry_name_attribute(self) -> None:
        error = PluginAlreadyRegisteredError("dup-plugin", "my-registry")
        assert error.registry_name == "my-registry"

    def test_message_contains_plugin_name(self) -> None:
        error = PluginAlreadyRegisteredError("dup-plugin", "my-registry")
        assert "dup-plugin" in str(error)


# ===========================================================================
# PluginRegistry — construction and basic state
# ===========================================================================


class TestPluginRegistryConstruction:
    def test_empty_registry_has_zero_length(self) -> None:
        registry = _fresh_registry()
        assert len(registry) == 0

    def test_empty_registry_list_plugins_is_empty(self) -> None:
        registry = _fresh_registry()
        assert registry.list_plugins() == []

    def test_repr_contains_name(self) -> None:
        registry = _fresh_registry("processors")
        assert "processors" in repr(registry)

    def test_repr_contains_base_class_name(self) -> None:
        registry = _fresh_registry()
        assert "BasePlugin" in repr(registry)

    def test_repr_contains_empty_plugins_list(self) -> None:
        registry = _fresh_registry()
        assert "[]" in repr(registry)


# ===========================================================================
# register (decorator)
# ===========================================================================


class TestPluginRegistryRegisterDecorator:
    def test_decorator_registers_class_and_returns_it(self) -> None:
        registry = _fresh_registry()

        @registry.register("plugin-a")
        class LocalPlugin(BasePlugin):
            def run(self) -> str:
                return "local"

        assert LocalPlugin is not None
        assert registry.get("plugin-a") is LocalPlugin

    def test_decorator_increments_length(self) -> None:
        registry = _fresh_registry()

        @registry.register("plugin-a")
        class LocalPlugin(BasePlugin):
            def run(self) -> str:
                return "local"

        assert len(registry) == 1

    def test_decorator_duplicate_name_raises_already_registered(self) -> None:
        registry = _fresh_registry()
        registry.register_class("plugin-a", ConcretePluginA)

        with pytest.raises(PluginAlreadyRegisteredError):
            @registry.register("plugin-a")
            class LocalPlugin(BasePlugin):
                def run(self) -> str:
                    return "dup"

    def test_decorator_wrong_base_class_raises_type_error(self) -> None:
        registry = _fresh_registry()

        with pytest.raises(TypeError):
            @registry.register("bad-plugin")
            class BadPlugin:  # type: ignore[misc]
                pass

    def test_membership_check_after_register(self) -> None:
        registry = _fresh_registry()
        registry.register_class("plugin-a", ConcretePluginA)
        assert "plugin-a" in registry

    def test_decorator_logs_debug_message(self, caplog: pytest.LogCaptureFixture) -> None:
        registry = _fresh_registry()
        with caplog.at_level(logging.DEBUG, logger="bsl.plugins.registry"):
            @registry.register("logged-plugin")
            class LoggedPlugin(BasePlugin):
                def run(self) -> str:
                    return "logged"

        assert "logged-plugin" in caplog.text


# ===========================================================================
# register_class (programmatic)
# ===========================================================================


class TestPluginRegistryRegisterClass:
    def test_register_class_stores_class(self) -> None:
        registry = _fresh_registry()
        registry.register_class("plugin-a", ConcretePluginA)
        assert registry.get("plugin-a") is ConcretePluginA

    def test_register_class_duplicate_raises_already_registered(self) -> None:
        registry = _fresh_registry()
        registry.register_class("plugin-a", ConcretePluginA)
        with pytest.raises(PluginAlreadyRegisteredError):
            registry.register_class("plugin-a", ConcretePluginB)

    def test_register_class_wrong_type_raises_type_error(self) -> None:
        registry = _fresh_registry()
        with pytest.raises(TypeError):
            registry.register_class("bad", NotAPlugin)  # type: ignore[arg-type]

    def test_register_class_non_class_raises_type_error(self) -> None:
        registry = _fresh_registry()
        with pytest.raises(TypeError):
            registry.register_class("bad", "not_a_class")  # type: ignore[arg-type]

    def test_register_two_different_classes(self) -> None:
        registry = _fresh_registry()
        registry.register_class("a", ConcretePluginA)
        registry.register_class("b", ConcretePluginB)
        assert len(registry) == 2


# ===========================================================================
# deregister
# ===========================================================================


class TestPluginRegistryDeregister:
    def test_deregister_removes_plugin(self) -> None:
        registry = _fresh_registry()
        registry.register_class("plugin-a", ConcretePluginA)
        registry.deregister("plugin-a")
        assert "plugin-a" not in registry

    def test_deregister_decrements_length(self) -> None:
        registry = _fresh_registry()
        registry.register_class("plugin-a", ConcretePluginA)
        registry.deregister("plugin-a")
        assert len(registry) == 0

    def test_deregister_nonexistent_raises_not_found(self) -> None:
        registry = _fresh_registry()
        with pytest.raises(PluginNotFoundError):
            registry.deregister("ghost")

    def test_deregister_logs_debug(self, caplog: pytest.LogCaptureFixture) -> None:
        registry = _fresh_registry()
        registry.register_class("to-remove", ConcretePluginA)
        with caplog.at_level(logging.DEBUG, logger="bsl.plugins.registry"):
            registry.deregister("to-remove")
        assert "to-remove" in caplog.text


# ===========================================================================
# get
# ===========================================================================


class TestPluginRegistryGet:
    def test_get_returns_registered_class(self) -> None:
        registry = _fresh_registry()
        registry.register_class("plugin-a", ConcretePluginA)
        result = registry.get("plugin-a")
        assert result is ConcretePluginA

    def test_get_nonexistent_raises_not_found(self) -> None:
        registry = _fresh_registry()
        with pytest.raises(PluginNotFoundError):
            registry.get("ghost")

    def test_get_class_is_instantiable(self) -> None:
        registry = _fresh_registry()
        registry.register_class("plugin-a", ConcretePluginA)
        cls = registry.get("plugin-a")
        instance = cls()
        assert instance.run() == "A"


# ===========================================================================
# list_plugins
# ===========================================================================


class TestPluginRegistryListPlugins:
    def test_list_plugins_is_sorted(self) -> None:
        registry = _fresh_registry()
        registry.register_class("zebra", ConcretePluginA)
        registry.register_class("alpha", ConcretePluginB)
        plugins = registry.list_plugins()
        assert plugins == ["alpha", "zebra"]

    def test_list_plugins_empty_returns_empty_list(self) -> None:
        assert _fresh_registry().list_plugins() == []

    def test_list_plugins_after_deregister(self) -> None:
        registry = _fresh_registry()
        registry.register_class("a", ConcretePluginA)
        registry.register_class("b", ConcretePluginB)
        registry.deregister("a")
        assert registry.list_plugins() == ["b"]


# ===========================================================================
# __contains__ and __len__
# ===========================================================================


class TestPluginRegistryMagicMethods:
    def test_contains_true_when_registered(self) -> None:
        registry = _fresh_registry()
        registry.register_class("plugin", ConcretePluginA)
        assert "plugin" in registry

    def test_contains_false_when_not_registered(self) -> None:
        assert "ghost" not in _fresh_registry()

    def test_len_grows_with_registrations(self) -> None:
        registry = _fresh_registry()
        assert len(registry) == 0
        registry.register_class("a", ConcretePluginA)
        assert len(registry) == 1
        registry.register_class("b", ConcretePluginB)
        assert len(registry) == 2


# ===========================================================================
# load_entrypoints
# ===========================================================================


class TestPluginRegistryLoadEntrypoints:
    def test_load_entrypoints_empty_group_does_nothing(self) -> None:
        registry = _fresh_registry()
        with patch(
            "bsl.plugins.registry.importlib.metadata.entry_points",
            return_value=[],
        ):
            registry.load_entrypoints("bsl.plugins.empty")
        assert len(registry) == 0

    def test_load_entrypoints_registers_valid_plugin(self) -> None:
        registry = _fresh_registry()

        mock_ep = MagicMock()
        mock_ep.name = "dynamic-plugin"
        mock_ep.load.return_value = ConcretePluginA

        with patch(
            "bsl.plugins.registry.importlib.metadata.entry_points",
            return_value=[mock_ep],
        ):
            registry.load_entrypoints("bsl.plugins")

        assert "dynamic-plugin" in registry
        assert registry.get("dynamic-plugin") is ConcretePluginA

    def test_load_entrypoints_skips_already_registered(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        registry = _fresh_registry()
        registry.register_class("existing-plugin", ConcretePluginA)

        mock_ep = MagicMock()
        mock_ep.name = "existing-plugin"

        with patch(
            "bsl.plugins.registry.importlib.metadata.entry_points",
            return_value=[mock_ep],
        ):
            with caplog.at_level(logging.DEBUG, logger="bsl.plugins.registry"):
                registry.load_entrypoints("bsl.plugins")

        assert "existing-plugin" in caplog.text
        assert len(registry) == 1  # still just one

    def test_load_entrypoints_handles_load_exception_gracefully(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        registry = _fresh_registry()

        mock_ep = MagicMock()
        mock_ep.name = "bad-plugin"
        mock_ep.load.side_effect = ImportError("no module named bad_thing")

        with patch(
            "bsl.plugins.registry.importlib.metadata.entry_points",
            return_value=[mock_ep],
        ):
            with caplog.at_level(logging.ERROR, logger="bsl.plugins.registry"):
                registry.load_entrypoints("bsl.plugins")

        assert len(registry) == 0

    def test_load_entrypoints_handles_register_type_error(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        registry = _fresh_registry()

        mock_ep = MagicMock()
        mock_ep.name = "bad-type-plugin"
        mock_ep.load.return_value = NotAPlugin  # wrong base class

        with patch(
            "bsl.plugins.registry.importlib.metadata.entry_points",
            return_value=[mock_ep],
        ):
            with caplog.at_level(logging.WARNING, logger="bsl.plugins.registry"):
                registry.load_entrypoints("bsl.plugins")

        assert len(registry) == 0

    def test_load_entrypoints_is_idempotent(self) -> None:
        registry = _fresh_registry()

        mock_ep = MagicMock()
        mock_ep.name = "stable-plugin"
        mock_ep.load.return_value = ConcretePluginA

        with patch(
            "bsl.plugins.registry.importlib.metadata.entry_points",
            return_value=[mock_ep],
        ):
            registry.load_entrypoints("bsl.plugins")
            registry.load_entrypoints("bsl.plugins")  # second call — idempotent

        assert len(registry) == 1
