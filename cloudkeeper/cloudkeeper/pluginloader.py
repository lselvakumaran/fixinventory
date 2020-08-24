import pkg_resources
import inspect
import cloudkeeper.logging
from typing import List
from cloudkeeper.args import ArgumentParser
from cloudkeeper.baseplugin import BasePlugin, BaseCliPlugin, PluginType

log = cloudkeeper.logging.getLogger(__name__)


plugins = {}
initialized = False


class PluginLoader:
    """Cloudkeeper Plugin Loader"""

    def __init__(self) -> None:
        # self.__plugins is a dict with key PluginType and value List
        # The List will hold all the Plugins of a PluginType
        # Current PluginTypes are COLLECTOR and PERSISTENT. So the Dict could look something like this:
        # {
        #   PluginType.COLLECTOR: [AWSPlugin, GCPPlugin, AzurePlugin],
        #   PluginType.PERSISTENT: [SlackNotificationPlugin, VolumeCleanupPlugin, GraphBackupPlugin]
        # }
        global plugins

        for plugin_type in PluginType:
            if plugin_type not in plugins:
                plugins[plugin_type] = []

    def find_plugins(self) -> None:
        """Finds Cloudkeeper Plugins

        Cloudkeeper Plugins have an entry point cloudkeeper.plugins.
        Any package resource with an entry point of that name will be handed to app_plugin()
        which validates that the package resource is a subclass of BasePlugin.
        """
        global initialized
        log.debug("Finding plugins")
        for entry_point in pkg_resources.iter_entry_points("cloudkeeper.plugins"):
            plugin = entry_point.load()
            self.add_plugin(plugin)
        initialized = True

    def add_plugin(self, plugin) -> bool:
        """Adds a Plugin class to the list of Plugins"""
        global plugins
        if (
            inspect.isclass(plugin)
            and not inspect.isabstract(plugin)
            and issubclass(plugin, (BasePlugin, BaseCliPlugin))
        ):
            log.debug(f"Found plugin {plugin} ({plugin.plugin_type.name})")
            if plugin not in plugins[plugin.plugin_type]:
                plugins[plugin.plugin_type].append(plugin)
        return True

    def plugins(self, plugin_type: PluginType) -> List:
        """Returns the list of Plugins of a certain PluginType"""
        if not initialized:
            self.find_plugins()
        selected_plugins = []
        for Plugin in plugins[plugin_type]:
            if plugin_type == PluginType.COLLECTOR:
                if (
                    not ArgumentParser.args.collector
                    or Plugin.cloud in ArgumentParser.args.collector
                ):
                    selected_plugins.append(Plugin)
                else:
                    log.debug(f"Plugin {Plugin} not in plugin list - skipping")
            else:
                selected_plugins.append(Plugin)
        return selected_plugins

    @staticmethod
    def add_args(arg_parser: ArgumentParser) -> None:
        """Add args to the arg parser

        This adds the PluginLoader()'s own args.
        """
        arg_parser.add_argument(
            "--collector",
            help="Collectors to load (default: all)",
            dest="collector",
            type=str,
            default=None,
            nargs="+",
        )

    def add_plugin_args(self, arg_parser: ArgumentParser) -> None:
        """Add args to the arg parser

        This adds all the Plugin's args.
        """
        if not initialized:
            self.find_plugins()
        log.debug("Adding plugin args")
        for type_plugins in plugins.values():  # iterate over all PluginTypes
            for Plugin in type_plugins:  # iterate over each Plugin of each PluginType
                Plugin.add_args(
                    arg_parser
                )  # add that Plugin's args to the ArgumentParser
