"""
Author: cg8-5712
Date: 2025-04-20
Version: 1.0.0
License: GPL-3.0
LastEditTime: 2025-04-20 16:30:00
Title: eAIP 航图查询插件
Description: 该插件允许用户通过机场的 ICAO 代码查询航图信息。
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

# 定义支持的航图类型
CHART_TYPES = [
    "ADC", "APDC", "GMC", "DGS", "AOC", "PATC", "FDA", "ATCMAS",
    "SID", "STAR", "WAYPOINT LIST", "DATABASE CODING TABLE", "IAC", "ATCSMAC"
]

__plugin_meta__ = PluginMetadata(
    name="eAIP航图查询",
    description="查询机场航图信息",
    usage="""
    指令:
        @机器人 eaip [机场ICAO代码]: 以图片形式显示航图列表
        @机器人 eaip [机场ICAO代码] --raw: 以文本形式显示航图列表
        @机器人 eaip [机场ICAO代码] [航图类型]: 显示指定类型航图列表
        @机器人 eaip [机场ICAO代码] [跑道号]: 显示相关跑道航图列表
        @机器人 eaip [机场ICAO代码] -s [文件标号]: 显示指定航图
        @机器人 eaip [机场ICAO代码] -c [code]: 按code匹配航图
        @机器人 eaip [机场ICAO代码] -f [关键字]: 搜索文件名包含关键字的航图
        @机器人 eaip set [期数]: 更新订阅期(仅管理员)
    支持的航图类型：
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
                help="订阅期(2505)",
                default_value=2505,),
            RegisterConfig(
                module="eaip",
                key="DIR_NAME",
                value="EAIP2025-05.V1.3",
                help="文件路径(EAIP2025-05.V1.3)",
                default_value="EAIP2025-05.V1.3",)
        ]).to_dict(),
)

Config.add_plugin_config(
    "eaip",
    "AIRAC_PERIOD",
    2505,
    help="订阅期(2505)",
    type=int
)

Config.add_plugin_config(
    "eaip",
    "DIR_NAME",
    "EAIP2025-05.V1.3",
    help="文件路径(EAIP2025-05.V1.3)",
    type=str
)

eaip_handler = EaipHandler()
eaip_command = on_command("eaip", rule=to_me(), priority=3, block=True)

@eaip_command.handle()
async def handle_eaip(bot: Bot, event: GroupMessageEvent, args=CommandArg()):
    """处理 eAIP 命令"""
    args = shlex.split(args.extract_plain_text().strip())

    if not args:
        await MessageUtils.build_message([
            At(flag="user", target=str(event.user_id)),
            Text("请提供机场 ICAO 代码")
        ]).send(reply_to=True)
        return

    try:
        # 处理设置命令
        if args[0] == "set" and len(args) == 2:
            if not await SUPERUSER(bot, event):
                await MessageUtils.build_message([
                    At(flag="user", target=str(event.user_id)),
                    Text("只有管理员可以使用此命令")
                ]).send(reply_to=True)
                return
            result = await eaip_handler.update_period(args[1])
            await MessageUtils.build_message([
                At(flag="user", target=str(event.user_id)),
                Text(result)
            ]).send(reply_to=True)
            return

        # 处理航图查询
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
                        Text("请提供文件标号")
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
                        Text("请提供 code")
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
                        Text("请提供搜索关键字")
                    ]).send(reply_to=True)
                    return
                filename = args[2]
            else:
                search_type = args[1].upper()

        # 获取航图列表
        result = await eaip_handler.get_chart_list(icao, search_type, filename=filename)
        if result is None:
            await MessageUtils.build_message([
                At(flag="user", target=str(event.user_id)),
                Text("未找到相关航图")
            ]).send(reply_to=True)
            return

        if show_raw:
            # 文字形式返回
            await MessageUtils.build_message([
                At(flag="user", target=str(event.user_id)),
                Text(result + "\n请在60秒内回复序号选择航图：")
            ]).send(reply_to=True)
        else:
            # 生成HTML图片
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

        # 等待用户选择
        try:
            resp = await prompt_until(
                "请在60秒内回复序号选择航图：",
                lambda e: e.extract_plain_text().strip().isdigit(),
                timeout=60,
                retry=1,
                retry_prompt="输入错误，请重新输入有效的序号"
            )

            if resp:
                selection = resp.extract_plain_text().strip()
                chart = await eaip_handler.get_chart_by_selection(icao, selection)
                await MessageUtils.build_message([
                    At(flag="user", target=str(event.user_id)),
                    chart if chart else Text("未找到对应的航图")
                ]).send(reply_to=True)

        except Exception as e:
            await MessageUtils.build_message([
                At(flag="user", target=str(event.user_id)),
                Text("操作超时或选择无效，请重新查询")
            ]).send(reply_to=True)
            logger.error("选择航图失败", "eaip", e=e)

    except Exception as e:
        await MessageUtils.build_message([
            At(flag="user", target=str(event.user_id)),
            Text(f"处理请求失败: {str(e)}")
        ]).send(reply_to=True)
        logger.error("处理eAIP请求失败", "eaip", e=e)