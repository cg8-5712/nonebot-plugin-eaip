"""
Author: cg8-5712
Date: 2025-05-02
Version: 1.5.0
License: GPL-3.0
LastEditTime: 2025-05-02 17:45
Title: eAIP Chart Query Plugin
Description: This plugin allows users to query aeronautical charts using airport ICAO codes.
"""

from nonebot import on_command, require
require("nonebot_plugin_waiter")
from nonebot.plugin import PluginMetadata
from nonebot.params import CommandArg
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.adapters import Bot
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot_plugin_waiter import prompt_until
from nonebot_plugin_alconna import At, Text
from nonebot_plugin_htmlrender import template_to_pic
import shlex

from zhenxun.configs.path_config import TEMPLATE_PATH
from zhenxun.configs.config import Config
from zhenxun.configs.utils import PluginExtraData, RegisterConfig
from zhenxun.utils.message import MessageUtils
from zhenxun.services.log import logger
from .eaip import EaipHandler

# Define supported chart types
CHART_TYPES = [
    "ADC", "APDC", "GMC", "DGS", "AOC", "PATC", "FDA", "ATCMAS",
    "SID", "STAR", "WAYPOINT LIST", "DATABASE CODING TABLE", "IAC", "ATCSMAC"
]

__plugin_meta__ = PluginMetadata(
    name="eAIP Chart Query",
    description="Query airport charts information",
    usage="""
    Commands:
        @Bot eaip [ICAO code]: Display chart list as image
        @Bot eaip [ICAO code] --raw: Display chart list as text
        @Bot eaip [ICAO code] [Chart type]: Display charts of specified type
        @Bot eaip [ICAO code] [Runway]: Display runway-related charts
        @Bot eaip [ICAO code] -s [File number]: Display specific chart
        @Bot eaip [ICAO code] -c [code]: Match charts by code
        @Bot eaip [ICAO code] -f [keyword]: Search charts by filename keyword
        @Bot eaip set [Period]: Update AIRAC period (admin only)
    Supported chart types:
        ADC, APDC, GMC, DGS, AOC, PATC, FDA, ATCMAS, SID, STAR,
        WAYPOINT LIST, DATABASE CODING TABLE, IAC, ATCSMAC
    """,
    extra=PluginExtraData(
        version="1.0.0",
        configs=[
            RegisterConfig(
                module="eaip",
                key="AIRAC_PERIOD",
                value=2505,
                help="AIRAC Period (2505)",
                default_value=2505,),
            RegisterConfig(
                module="eaip",
                key="DIR_NAME",
                value="EAIP2025-05.V1.3",
                help="Directory path (EAIP2025-05.V1.3)",
                default_value="EAIP2025-05.V1.3",)
        ]).to_dict(),
)

Config.add_plugin_config(
    "eaip",
    "AIRAC_PERIOD",
    2505,
    help="AIRAC Period (2505)",
    type=int
)

Config.add_plugin_config(
    "eaip",
    "DIR_NAME",
    "EAIP2025-05.V1.3",
    help="Directory path (EAIP2025-05.V1.3)",
    type=str
)

eaip_handler = EaipHandler()
eaip_command = on_command("eaip", rule=to_me(), priority=3, block=True)

@eaip_command.handle()
async def handle_eaip(bot: Bot, event: GroupMessageEvent, args=CommandArg()):
    """Handle eAIP command"""
    args = shlex.split(args.extract_plain_text().strip())

    if not args:
        await MessageUtils.build_message([
            At(flag="user", target=str(event.user_id)),
            Text("Please provide an airport ICAO code")
        ]).send(reply_to=True)
        return

    try:
        # Handle set command
        if args[0] == "set" and len(args) == 2:
            if not await SUPERUSER(bot, event):
                await MessageUtils.build_message([
                    At(flag="user", target=str(event.user_id)),
                    Text("Only administrators can use this command")
                ]).send(reply_to=True)
                return
            result = await eaip_handler.update_period(args[1])
            await MessageUtils.build_message([
                At(flag="user", target=str(event.user_id)),
                Text(result)
            ]).send(reply_to=True)
            return

        # Handle chart queries
        icao = args[0].upper()
        search_type = None
        filename = None
        show_raw = "--raw" in args
        args = [arg for arg in args if arg != "--raw"]

        if len(args) > 1:
            if args[1].startswith("-s"):
                if len(args) <= 2:
                    await MessageUtils.build_message([
                        At(flag="user", target=str(event.user_id)),
                        Text("Please provide a file number")
                    ]).send(reply_to=True)
                    return
                doc_id = args[2]
                result = await eaip_handler.get_chart(icao, doc_id)
                await MessageUtils.build_message([
                    At(flag="user", target=str(event.user_id)),
                    result
                ]).send(reply_to=True)
                return
            elif args[1].startswith("-c"):
                if len(args) <= 2:
                    await MessageUtils.build_message([
                        At(flag="user", target=str(event.user_id)),
                        Text("Please provide a code")
                    ]).send(reply_to=True)
                    return
                code = args[2].upper()
                result = await eaip_handler.get_chart_by_code(icao, code)
                await MessageUtils.build_message([
                    At(flag="user", target=str(event.user_id)),
                    result
                ]).send(reply_to=True)
                return
            elif args[1].startswith("-f"):
                if len(args) <= 2:
                    await MessageUtils.build_message([
                        At(flag="user", target=str(event.user_id)),
                        Text("Please provide a search keyword")
                    ]).send(reply_to=True)
                    return
                filename = args[2]
            else:
                search_type = args[1].upper()

        # Get chart list
        result = await eaip_handler.get_chart_list(icao, search_type, filename=filename)
        if result is None:
            await MessageUtils.build_message([
                At(flag="user", target=str(event.user_id)),
                Text("No charts found")
            ]).send(reply_to=True)
            return

        if show_raw:
            # Return as text
            await MessageUtils.build_message([
                At(flag="user", target=str(event.user_id)),
                Text(result + "\nPlease reply with a number to select a chart within 60 seconds:")
            ]).send(reply_to=True)
        else:
            # Generate HTML image
            charts = []
            for line in result.split('\n'):
                if not line.strip():
                    continue
                parts = line.split('.', 1)
                if len(parts) != 2:
                    continue
                chart_id = parts[0].strip()
                content = parts[1].strip()
                chart_type = content[1:content.find(']')].strip()
                chart_name = content[content.find(']')+1:].strip()
                charts.append({
                    'id': chart_id,
                    'type': chart_type,
                    'name': chart_name
                })

            image = await template_to_pic(
                template_path=str(
                    (TEMPLATE_PATH / "aviation" / "eaip").absolute()
                ),
                template_name="main.html",
                templates={
                    "icao": icao,
                    "charts": charts
                },
                pages={
                    "viewport": {"width": 1000, "height": 800},
                    "base_url": f"file://{(TEMPLATE_PATH / 'aviation' / 'eaip').absolute()}"
                },
                wait=2
            )

            await MessageUtils.build_message([
                At(flag="user", target=str(event.user_id)),
                image
            ]).send(reply_to=True)

        # Wait for user selection
        try:
            resp = await prompt_until(
                "Please enter a number to select a chart within 60 seconds:",
                lambda e: e.extract_plain_text().strip().isdigit(),
                timeout=60,
                retry=1,
                retry_prompt="Invalid input, please enter a valid number"
            )

            if resp:
                selection = resp.extract_plain_text().strip()
                chart = await eaip_handler.get_chart_by_selection(icao, selection)
                await MessageUtils.build_message([
                    At(flag="user", target=str(event.user_id)),
                    chart if chart else Text("Chart not found")
                ]).send(reply_to=True)

        except Exception as e:
            await MessageUtils.build_message([
                At(flag="user", target=str(event.user_id)),
                Text("Operation timed out or invalid selection, please query again")
            ]).send(reply_to=True)
            logger.error("Failed to select chart", "eaip", e=e)

    except Exception as e:
        await MessageUtils.build_message([
            At(flag="user", target=str(event.user_id)),
            Text(f"Failed to process request: {str(e)}")
        ]).send(reply_to=True)
        logger.error("Failed to process eAIP request", "eaip", e=e)