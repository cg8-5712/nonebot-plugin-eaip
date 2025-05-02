"""
Author: cg8-5712
Date: 2025-05-02
Version: 1.5.0
License: GPL-3.0
LastEditTime: 2025-05-02 17:45
Title: AIP Chart Service
Description: Service class for processing and managing aeronautical charts.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import pymupdf
from zhenxun.services.log import logger
from zhenxun.configs.path_config import PLUGIN_DATA_PATH
from zhenxun.configs.config import Config

@dataclass
class ChartFile:
    """航图文件数据模型"""
    name: str
    path: str
    chart_type: str
    icao: str

    @property
    def full_path(self) -> Path:
        """获取完整路径"""
        return Path(self.path) / self.name


class ChartProcessor:
    """航图处理服务"""

    CHART_TYPES = [
        "ADC", "APDC", "GMC", "DGS", "AOC", "PATC", "FDA",
        "ATCMAS", "SID", "STAR", "WAYPOINT LIST",
        "DATABASE CODING TABLE", "IAC", "ATCSMAC"
    ]

    SPECIAL_CHART_TYPES = ["WAYPOINT LIST", "GMC", "APDC", "DATABASE CODING TABLE"]

    def __init__(self, data_path: Path) -> None:
        """初始化航图处理器"""
        self.data_path = data_path
        self.dir_name = Config.get_config("eaip", "DIR_NAME", "EAIP2025-05.V1.3")
        self.ad_path = data_path / "Data" / self.dir_name / "Terminal"
        self.json_path = data_path / "Data" / "JsonPath" / "AD.JSON"

        self._validate_paths()

    def _validate_paths(self) -> None:
        """验证路径有效性"""
        if not self.data_path.exists():
            logger.error("数据目录不存在", "航图处理", target=str(self.data_path))
            raise ValueError(f"数据目录不存在: {self.data_path}")

        if not self.ad_path.exists():
            logger.error("Terminal目录不存在", "航图处理", target=str(self.ad_path))
            raise ValueError(f"Terminal目录不存在: {self.ad_path}")

        if not self.json_path.exists():
            logger.error("AD.JSON文件不存在", "航图处理", target=str(self.json_path))
            raise ValueError(f"AD.JSON文件不存在: {self.json_path}")

    def merge_pdfs(self, folder_path: Path, chart_type: str) -> Optional[Path]:
        """合并指定类型的PDF文件"""
        if not folder_path.exists() or not folder_path.is_dir():
            logger.warning("文件夹不存在", "航图合并", target=str(folder_path))
            return None

        pdf_files = sorted(folder_path.glob("*.pdf"))
        if not pdf_files:
            logger.warning("没有找到PDF文件", "航图合并", target=str(folder_path))
            return None

        try:
            merged_doc = pymupdf.open()
            for pdf_path in pdf_files:
                with pymupdf.open(str(pdf_path)) as doc:
                    merged_doc.insert_pdf(doc)

            merged_path = folder_path / f"{chart_type}-MERGED.pdf"
            merged_doc.save(str(merged_path))
            merged_doc.close()

            logger.success("PDF合并成功", "航图合并", param={"path": str(merged_path)})
            return merged_path

        except Exception as e:
            logger.error("合并PDF失败", "航图合并", target=str(folder_path), e=e)
            return None

    def _merge_special_charts(self, airport_path: Path) -> None:
        """合并特殊类型图表"""
        for chart_type in self.SPECIAL_CHART_TYPES:
            type_folder = airport_path / chart_type
            if type_folder.exists() and type_folder.is_dir():
                logger.info("处理特殊图表", "航图处理", target={"类型": chart_type, "路径": str(type_folder)})
                self.merge_pdfs(type_folder, chart_type)

    @staticmethod
    def _get_icao_from_path(path: Path) -> Optional[str]:
        """从路径提取ICAO代码"""
        for i, part in enumerate(path.parts):
            if "GeneralDoc" in part:
                return "GeneralDoc"
            if "Terminal" in part and i + 1 < len(path.parts):
                return path.parts[i + 1]
        return None

    def _rename_chart_files(self) -> None:
        """重命名航图文件"""
        try:
            with open(self.json_path, "r", encoding="utf-8") as file:
                chart_data = json.load(file)
            logger.info("读取航图数据", "航图处理", target=str(self.json_path))

            for chart in chart_data:
                if not chart.get("pdfPath"):
                    continue

                old_path = self.data_path / chart["pdfPath"].lstrip("/")
                icao = self._get_icao_from_path(old_path)

                if not icao:
                    logger.warning(
                        "无法确定ICAO代码",
                        "航图处理",
                        target=str(old_path)
                    )
                    continue

                new_name = (chart["name"].replace(":", "-")
                           .replace("/", "-")
                           .replace("\\", "-") + ".pdf")

                directory = self.ad_path / icao
                new_path = directory / new_name

                if old_path.exists():
                    try:
                        new_path.parent.mkdir(parents=True, exist_ok=True)
                        old_path.rename(new_path)
                        logger.success(
                            "重命名成功",
                            "航图处理",
                            param={"原路径": str(old_path), "新路径": str(new_path)}
                        )
                    except OSError as e:
                        logger.error(
                            "重命名失败",
                            "航图处理",
                            target=str(old_path),
                            e=e
                        )
                else:
                    logger.warning(
                        "文件不存在",
                        "航图处理",
                        target=str(old_path)
                    )

        except Exception as e:
            logger.error("重命名过程失败", "航图处理", e=e)

    def _organize_airport_files(self) -> None:
        """整理机场文件"""
        try:
            airports = [d.name for d in self.ad_path.iterdir() if d.is_dir()]
            logger.info("开始整理机场文件", "航图处理", target={"机场数量": len(airports)})

            for airport in airports:
                airport_path = self.ad_path / airport
                for pdf_file in airport_path.glob("*.pdf"):
                    for chart_type in self.CHART_TYPES:
                        if chart_type in pdf_file.name:
                            type_folder = airport_path / chart_type
                            type_folder.mkdir(parents=True, exist_ok=True)
                            new_path = type_folder / pdf_file.name
                            pdf_file.rename(new_path)
                            logger.success(
                                "移动文件完成",
                                "航图处理",
                                param={"文件": str(pdf_file), "目标": str(new_path)}
                            )
                            break

        except Exception as e:
            logger.error("整理文件失败", "航图处理", e=e)

    def _generate_index(self) -> None:
        """生成航图索引"""
        try:
            airports = [d.name for d in self.ad_path.iterdir() if d.is_dir()]

            for airport in airports:
                airport_path = self.ad_path / airport
                self._merge_special_charts(airport_path)

                index_entries: List[Dict[str, str]] = []
                chart_id = 1

                # 处理根目录下的PDF文件
                for pdf_file in airport_path.glob("*.pdf"):
                    path = pdf_file.name.replace("\\", "/")
                    index_entries.append({
                        "id": str(chart_id),
                        "code": "general",
                        "name": pdf_file.name,
                        "path": path,
                        "sort": "general"  # 根目录下的文件标记为未分类
                    })
                    chart_id += 1

                # 处理子文件夹中的PDF文件
                for folder in airport_path.iterdir():
                    if not folder.is_dir():
                        continue

                    for pdf_file in folder.glob("*.pdf"):
                        path = f"{folder.name}/{pdf_file.name}".replace("\\", "/")
                        index_entries.append({
                            "id": str(chart_id),
                            "code": str(pdf_file.name.split(folder.name)[0]).split(f"{airport}-")[-1],
                            "name": pdf_file.name,
                            "path": path,
                            "sort": folder.name
                        })
                        chart_id += 1

                index_file = airport_path / "index.json"
                with open(index_file, "w", encoding="utf-8") as f:
                    json.dump(index_entries, f, ensure_ascii=False, indent=4)

                logger.success(
                    "索引生成完成",
                    "航图处理",
                    param={"机场": airport, "图表数量": len(index_entries)}
                )

        except Exception as e:
            logger.error("生成索引失败", "航图处理", e=e)

    def update(self, actions: Optional[List[str]] = None) -> None:
        """更新机场航图数据"""
        valid_actions = ["rename", "organize", "index"]
        actions_to_run = actions if actions else valid_actions

        if not isinstance(actions_to_run, list):
            logger.error(
                "参数类型错误",
                "航图处理",
                target={"actions": actions_to_run}
            )
            return

        invalid_actions = [act for act in actions_to_run if act not in valid_actions]
        if invalid_actions:
            logger.error(
                "存在无效的操作",
                "航图处理",
                target={"invalid_actions": invalid_actions}
            )
            return

        try:
            for action in actions_to_run:
                logger.info(f"执行{action}操作", "航图处理")
                if action == "rename":
                    self._rename_chart_files()
                elif action == "organize":
                    self._organize_airport_files()
                elif action == "index":
                    self._generate_index()

            logger.success(
                "更新完成",
                "航图处理",
                param={"completed_actions": actions_to_run}
            )

        except Exception as e:
            logger.error("更新过程出错", "航图处理", e=e)


def main() -> None:
    """主函数"""
    data_path = Path(PLUGIN_DATA_PATH) / "eaip" / "AD" / "2505"
    processor = ChartProcessor(data_path)
    processor.update(["rename", "organize", "index"])


if __name__ == "__main__":
    main()