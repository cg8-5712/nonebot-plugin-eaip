import json
import pymupdf
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any


class Logger:
    """日志处理类"""

    def __init__(self, name: str) -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def info(self, message: str) -> None:
        self.logger.info(message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)

    def error(self, message: str) -> None:
        self.logger.error(message)


class ChartProcessor:
    """航图处理类"""

    CHART_TYPES = [
        "ADC", "APDC", "GMC", "DGS", "AOC", "PATC", "FDA",
        "ATCMAS", "SID", "STAR", "WAYPOINT LIST",
        "DATABASE CODING TABLE", "IAC", "ATCSMAC"
    ]

    SPECIAL_CHART_TYPES = ["WAYPOINT LIST", "GMC", "APDC", "DATABASE CODING TABLE"]

    def __init__(self, data_path: Path) -> None:
        self.data_path = data_path
        self.ad_path = data_path / "Data" / "EAIP2025-05.V1.3" / "Terminal"
        self.json_path = data_path / "Data" / "JsonPath" / "AD.JSON"
        self.logger = Logger(__name__)

    def merge_pdfs(self, folder_path: Path, chart_type: str) -> Optional[Path]:
        """合并指定类型的PDF文件"""
        if not folder_path.exists() or not folder_path.is_dir():
            self.logger.warning(f"文件夹不存在：{folder_path}")
            return None

        pdf_files = sorted(folder_path.glob("*.pdf"))
        if not pdf_files:
            self.logger.warning(f"没有找到PDF文件：{folder_path}")
            return None

        try:
            merged_doc = pymupdf.open()
            for pdf_path in pdf_files:
                with pymupdf.open(str(pdf_path)) as doc:
                    merged_doc.insert_pdf(doc)

            merged_path = folder_path / f"{chart_type}-MERGED.pdf"
            merged_doc.save(str(merged_path))
            merged_doc.close()

            self.logger.info(f"PDF合并成功：{merged_path}")
            return merged_path

        except Exception as e:
            self.logger.error(f"合并PDF失败：{e}")
            return None

    def merge_special_charts(self, airport_path: Path) -> None:
        """合并特殊类型的图表"""
        for chart_type in self.SPECIAL_CHART_TYPES:
            type_folder = airport_path / chart_type
            if type_folder.exists() and type_folder.is_dir():
                self.logger.info(f"开始合并{chart_type}文件")
                self.merge_pdfs(type_folder, chart_type)

    @staticmethod
    def get_icao_from_path(path: Path) -> Optional[str]:
        """从文件路径中提取ICAO代码"""
        for i, part in enumerate(path.parts):
            if 'GeneralDoc' in part:
                return 'GeneralDoc'
            if 'Terminal' in part and i + 1 < len(path.parts):
                return path.parts[i + 1]
        return None

    def rename_chart_files(self) -> None:
        """重命名航图文件"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as file:
                chart_data = json.load(file)
            self.logger.info(f"读取JSON文件成功：{self.json_path}")

            for chart in chart_data:
                if not chart['pdfPath']:
                    continue

                old_path = self.data_path / chart['pdfPath'].lstrip('/')
                icao = self.get_icao_from_path(old_path)

                if not icao:
                    self.logger.warning(f"无法确定文件类型和ICAO：{old_path}")
                    continue

                new_name = (chart['name'].replace(':', '-')
                            .replace("/", '-')
                            .replace("\\", "-") + '.pdf')

                directory = self.ad_path / icao
                new_path = directory / new_name

                if old_path.exists():
                    try:
                        new_path.parent.mkdir(parents=True, exist_ok=True)
                        old_path.rename(new_path)
                        self.logger.info(f"文件重命名成功：{new_path}")
                    except OSError as e:
                        self.logger.error(f"重命名文件失败：{e}")
                else:
                    self.logger.warning(f"文件不存在：{old_path}")

        except Exception as e:
            self.logger.error(f"重命名过程失败：{e}")

    def organize_airport_files(self) -> None:
        """整理机场文件到对应分类文件夹"""
        try:
            airports = [d.name for d in self.ad_path.iterdir() if d.is_dir()]
            self.logger.info(f"获取到的机场列表：{airports}")

            for airport in airports:
                airport_path = self.ad_path / airport
                for pdf_file in airport_path.glob("*.pdf"):
                    for chart_type in self.CHART_TYPES:
                        if chart_type in pdf_file.name:
                            type_folder = airport_path / chart_type
                            type_folder.mkdir(parents=True, exist_ok=True)
                            new_path = type_folder / pdf_file.name
                            pdf_file.rename(new_path)
                            self.logger.info(f"移动文件成功：{pdf_file.name} -> {type_folder}")
                            break

        except Exception as e:
            self.logger.error(f"整理文件失败：{e}")

    def generate_index(self) -> None:
        """生成航图索引文件"""
        try:
            airports = [d.name for d in self.ad_path.iterdir() if d.is_dir()]

            for airport in airports:
                airport_path = self.ad_path / airport
                self.merge_special_charts(airport_path)

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

                self.logger.info(
                    f"生成索引完成 - 机场：{airport}，共{len(index_entries)}条记录"
                )

        except Exception as e:
            self.logger.error(f"生成索引失败：{e}")

    def update(self, actions: Optional[List[str]] = None) -> None:
        """更新机场航图数据"""
        valid_actions = ["rename", "organize", "index"]
        actions_to_run = actions if actions else valid_actions

        if not isinstance(actions_to_run, list):
            self.logger.error(f"参数类型错误：{actions_to_run}")
            return

        invalid_actions = [act for act in actions_to_run if act not in valid_actions]
        if invalid_actions:
            self.logger.error(f"存在无效的操作：{invalid_actions}")
            return

        action_functions = {
            "rename": self.rename_chart_files,
            "organize": self.organize_airport_files,
            "index": self.generate_index
        }

        try:
            for action in actions_to_run:
                self.logger.info(f"执行{action}操作")
                action_functions[action]()

            self.logger.info(f"更新完成，已执行操作：{actions_to_run}")

        except Exception as e:
            self.logger.error(f"更新过程出错：{e}")


def main():
    data_path = Path(r"F:\bian\pyproject\qbot\zhenxun_bot\zhenxun\plugins\data\AD\2505")
    processor = ChartProcessor(data_path)
    processor.update(["rename", "organize", "index"])


if __name__ == "__main__":
    main()