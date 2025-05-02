"""
处理eAIP航图相关的核心功能
"""

import os
import json
import re
from pathlib import Path
from typing import Union, List, Dict, Optional
import pymupdf
from zhenxun.services.log import logger
from zhenxun.configs.path_config import PLUGIN_DATA_PATH
from zhenxun.configs.config import Config
from .eaip_init import ChartProcessor

EAIP_DATA_PATH = PLUGIN_DATA_PATH / "AD"

class EaipHandler:
    def __init__(self):
        # 从Config获取当前的AIRAC期数
        self.airac = Config.get_config("eaip", "AIRAC_PERIOD", 2505)
        self.dir_name = Config.get_config("eaip", "DIR_NAME", "EAIP2025-05.V1.3")
        # 使用EAIP_DATA_PATH和当前期数构建base_path
        self.base_path = EAIP_DATA_PATH / str(self.airac)

    async def update_period(self, period: str) -> str:
        """更新AIRAC期数"""
        if not period.isdigit() or len(period) != 4:
            return "无效的期数格式"
        try:
            airac = int(period)
            print(f"更新订阅期: {airac}")
            Config.set_config("eaip", "AIRAC_PERIOD", int(airac), True)
            print("更新订阅期成功")
            Config.set_config("eaip", "DIR_NAME", "EAIP2025-05.V1.3", True)
            print("更新订阅目录成功")
            # 检查新路径是否存在
            new_path = EAIP_DATA_PATH / str(airac)
            print(f"新路径: {new_path}")
            if not new_path.exists():
                return f"期数 {airac} 的数据目录不存在"

            self.base_path = new_path
            terminal_path = self.base_path / "Data" / self.dir_name / "Terminal"
            need_update = False

            print(f"检查 {self.base_path} 是否需要更新")


            for file in os.listdir(terminal_path):
                file_path = terminal_path / file
                if file_path.is_dir():
                    index_path = file_path / "index.json"
                    if not index_path.exists():
                        need_update = True
                        break

            if need_update:
                processor = ChartProcessor(self.base_path)
                processor.update(["rename", "organize", "index"])
            else:
                logger.info("所有机场的索引文件已存在，无需更新", "eaip")

            # 获取统计信息
            airports = [d for d in terminal_path.iterdir() if d.is_dir()]
            total_charts = 0
            airport_info = []

            for airport in airports:
                index_path = airport / "index.json"
                if index_path.exists():
                    with open(index_path, "r", encoding="utf-8") as f:
                        charts = json.load(f)
                        chart_count = len(charts)
                        total_charts += chart_count
                        airport_info.append(f"{airport.name}: {chart_count}张航图")

            result = (
                f"AIRAC期: {airac}\n"
                f"机场总数: {len(airports)}\n"
                f"航图总数: {total_charts}\n"
                f"机场索引:\n" + "\n".join(airport_info)
            )

            logger.success(f"更新订阅期成功: {airac}", "eaip",
                       param={"airports": len(airports), "charts": total_charts})
            return result

        except Exception as e:
            logger.error("更新订阅期失败", "eaip", e=e)
            return f"更新失败: {e}"

    async def get_chart_list(self, icao: str, search_type: str = None,
                          code: str = None, filename: str = None) -> Optional[str]:
        """获取航图列表"""
        try:
            airport_path = self.base_path / "Data" / self.dir_name / "Terminal" / icao
            if not airport_path.exists():
                return None

            charts = []
            index_path = airport_path / "index.json"

            if index_path.exists():
                with open(index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if code:
                    # 按 code 匹配
                    data = [x for x in data if x.get("code", "").upper() == code.upper()]
                elif filename:
                    # 按文件名搜索
                    data = [x for x in data if filename.lower() in x["name"].lower()]
                elif search_type:
                    if re.match(r"^\d{2}[LRC]?$", search_type):  # 跑道号
                        data = [x for x in data if search_type in x["name"]]
                    else:  # 航图类型
                        data = [x for x in data if x["sort"] == search_type]

                if not data:
                    return None

                return "\n".join([
                    f"{x['id']}. [{x['sort'] or '未分类'}] {x['name']}"
                    for x in data
                ])

            return None

        except Exception as e:
            logger.error("获取航图列表失败", "eaip", e=e)
            return None

    async def get_chart(self, icao: str, doc_id: str) -> Union[str, bytes]:
        """获取指定航图"""
        try:
            airport_path = self.base_path / "Data" / self.dir_name / "Terminal" / icao
            if not airport_path.exists():
                return f"未找到机场 {icao} 的航图"

            index_path = airport_path / "index.json"
            if not index_path.exists():
                return "未找到索引文件"

            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            chart = next((x for x in data if str(x["id"]) == str(doc_id)), None)
            if not chart:
                return f"未找到标号为 {doc_id} 的航图"

            pdf_path = airport_path / chart["path"]
            if not pdf_path.exists():
                return "航图文件不存在"

            return await self._convert_pdf_to_image(pdf_path)

        except Exception as e:
            logger.error("获取航图失败", "eaip", e=e)
            return f"获取航图失败: {e}"

    async def get_chart_by_selection(self, icao: str, selection: str) -> Union[str, bytes]:
        """根据用户选择获取航图"""
        try:
            airport_path = self.base_path / "Data" / self.dir_name / "Terminal" / icao
            index_path = airport_path / "index.json"

            if not index_path.exists():
                return "未找到索引文件"

            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            try:
                idx = int(selection) - 1
                if not 0 <= idx < len(data):
                    return "无效的序号"

                chart = data[idx]
                pdf_path = airport_path / chart["path"]
                if not pdf_path.exists():
                    return "航图文件不存在"

                return await self._convert_pdf_to_image(pdf_path)

            except ValueError:
                return "无效的选择"

        except Exception as e:
            logger.error("获取所选航图失败", "eaip", e=e)
            return f"获取所选航图失败: {e}"

    async def get_chart_by_code(self, icao: str, code: str) -> Union[str, bytes]:
        """根据代码直接获取航图"""
        try:
            airport_path = self.base_path / "Data" / self.dir_name / "Terminal" / icao
            if not airport_path.exists():
                return f"未找到机场 {icao} 的航图"

            index_path = airport_path / "index.json"
            if not index_path.exists():
                return "未找到索引文件"

            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 按 code 精确匹配
            chart = next((x for x in data if x.get("code", "").upper() == code.upper()), None)
            if not chart:
                return f"未找到代码为 {code} 的航图"

            pdf_path = airport_path / chart["path"]
            if not pdf_path.exists():
                return "航图文件不存在"

            return await self._convert_pdf_to_image(pdf_path)

        except Exception as e:
            logger.error("获取航图失败", "eaip", e=e)
            return f"获取航图失败: {e}"

    async def _convert_pdf_to_image(self, pdf_path: Path) -> bytes:
        """将PDF转换为图片"""
        try:
            doc = pymupdf.open(str(pdf_path))
            page = doc[0]
            zoom = 2.8
            mat = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(
                matrix=mat,
                colorspace="rgb",
                alpha=False,
                annots=True
            )
            img_path = pdf_path.with_suffix('.png')
            pix.save(str(img_path))
            doc.close()

            with open(img_path, 'rb') as f:
                image_bytes = f.read()
            img_path.unlink()  # 删除临时文件
            return image_bytes

        except Exception as e:
            logger.error("PDF转图片失败", "eaip", e=e)
            raise Exception(f"PDF转图片失败: {e}")