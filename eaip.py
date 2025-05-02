"""
Author: cg8-5712
Date: 2025-05-02
Version: 1.5.0
License: GPL-3.0
LastEditTime: 2025-05-02 17:45
Title: eAIP Chart Query Plugin
Description: Core handler for processing eAIP chart data. This module provides functionality
for managing and retrieving aeronautical charts, including AIRAC cycle updates,
chart listing, and PDF to image conversion.
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
        # Get current AIRAC cycle from Config
        self.airac = Config.get_config("eaip", "AIRAC_PERIOD", 2505)
        self.dir_name = Config.get_config("eaip", "DIR_NAME", "EAIP2025-05.V1.3")
        # Build base_path using EAIP_DATA_PATH and current cycle
        self.base_path = EAIP_DATA_PATH / str(self.airac)

    async def update_period(self, period: str) -> str:
        """Update AIRAC cycle period"""
        if not period.isdigit() or len(period) != 4:
            return "Invalid period format"
        try:
            airac = int(period)
            print(f"Updating subscription period: {airac}")
            Config.set_config("eaip", "AIRAC_PERIOD", int(airac), True)
            print("Period update successful")
            Config.set_config("eaip", "DIR_NAME", "EAIP2025-05.V1.3", True)
            print("Directory update successful")
            # Check if new path exists
            new_path = EAIP_DATA_PATH / str(airac)
            print(f"New path: {new_path}")
            if not new_path.exists():
                return f"Data directory for period {airac} does not exist"

            self.base_path = new_path
            terminal_path = self.base_path / "Data" / self.dir_name / "Terminal"
            need_update = False

            print(f"Checking if {self.base_path} needs update")

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
                logger.info("All airport index files exist, no update needed", "eaip")

            # Get statistics
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
                        airport_info.append(f"{airport.name}: {chart_count} charts")

            result = (
                f"AIRAC Period: {airac}\n"
                f"Total Airports: {len(airports)}\n"
                f"Total Charts: {total_charts}\n"
                f"Airport Index:\n" + "\n".join(airport_info)
            )

            logger.success(f"Period update successful: {airac}", "eaip",
                       param={"airports": len(airports), "charts": total_charts})
            return result

        except Exception as e:
            logger.error("Failed to update period", "eaip", e=e)
            return f"Update failed: {e}"

    async def get_chart_list(self, icao: str, search_type: str = None,
                          code: str = None, filename: str = None) -> Optional[str]:
        """Get chart list"""
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
                    # Match by code
                    data = [x for x in data if x.get("code", "").upper() == code.upper()]
                elif filename:
                    # Search by filename
                    data = [x for x in data if filename.lower() in x["name"].lower()]
                elif search_type:
                    if re.match(r"^\d{2}[LRC]?$", search_type):  # Runway number
                        data = [x for x in data if search_type in x["name"]]
                    else:  # Chart type
                        data = [x for x in data if x["sort"] == search_type]

                if not data:
                    return None

                return "\n".join([
                    f"{x['id']}. [{x['sort'] or 'Uncategorized'}] {x['name']}"
                    for x in data
                ])

            return None

        except Exception as e:
            logger.error("Failed to get chart list", "eaip", e=e)
            return None

    async def get_chart(self, icao: str, doc_id: str) -> Union[str, bytes]:
        """Get specific chart"""
        try:
            airport_path = self.base_path / "Data" / self.dir_name / "Terminal" / icao
            if not airport_path.exists():
                return f"No charts found for airport {icao}"

            index_path = airport_path / "index.json"
            if not index_path.exists():
                return "Index file not found"

            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            chart = next((x for x in data if str(x["id"]) == str(doc_id)), None)
            if not chart:
                return f"Chart with ID {doc_id} not found"

            pdf_path = airport_path / chart["path"]
            if not pdf_path.exists():
                return "Chart file does not exist"

            return await self._convert_pdf_to_image(pdf_path)

        except Exception as e:
            logger.error("Failed to get chart", "eaip", e=e)
            return f"Failed to get chart: {e}"

    async def get_chart_by_selection(self, icao: str, selection: str) -> Union[str, bytes]:
        """Get chart by user selection"""
        try:
            airport_path = self.base_path / "Data" / self.dir_name / "Terminal" / icao
            index_path = airport_path / "index.json"

            if not index_path.exists():
                return "Index file not found"

            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            try:
                idx = int(selection) - 1
                if not 0 <= idx < len(data):
                    return "Invalid selection number"

                chart = data[idx]
                pdf_path = airport_path / chart["path"]
                if not pdf_path.exists():
                    return "Chart file does not exist"

                return await self._convert_pdf_to_image(pdf_path)

            except ValueError:
                return "Invalid selection"

        except Exception as e:
            logger.error("Failed to get selected chart", "eaip", e=e)
            return f"Failed to get selected chart: {e}"

    async def get_chart_by_code(self, icao: str, code: str) -> Union[str, bytes]:
        """Get chart directly by code"""
        try:
            airport_path = self.base_path / "Data" / self.dir_name / "Terminal" / icao
            if not airport_path.exists():
                return f"No charts found for airport {icao}"

            index_path = airport_path / "index.json"
            if not index_path.exists():
                return "Index file not found"

            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Exact match by code
            chart = next((x for x in data if x.get("code", "").upper() == code.upper()), None)
            if not chart:
                return f"Chart with code {code} not found"

            pdf_path = airport_path / chart["path"]
            if not pdf_path.exists():
                return "Chart file does not exist"

            return await self._convert_pdf_to_image(pdf_path)

        except Exception as e:
            logger.error("Failed to get chart", "eaip", e=e)
            return f"Failed to get chart: {e}"

    async def _convert_pdf_to_image(self, pdf_path: Path) -> bytes:
        """Convert PDF to image"""
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
            img_path.unlink()  # Delete temporary file
            return image_bytes

        except Exception as e:
            logger.error("Failed to convert PDF to image", "eaip", e=e)
            raise Exception(f"PDF to image conversion failed: {e}")