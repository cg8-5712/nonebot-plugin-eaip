# nonebot-plugin-eaip

<div align="center">

# Electronic Aeronautical Information Publication (eAIP) Chart Plugin

A Zhenxun Bot plugin for querying and managing aeronautical charts from eAIP.


<a href="https://www.python.org">
    <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue" alt="python">
</a>

<a href="https://onebot.dev/">
  <img src="https://img.shields.io/badge/OneBot-v11-black?style=social&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABABAMAAABYR2ztAAAAIVBMVEUAAAAAAAADAwMHBwceHh4UFBQNDQ0ZGRkoKCgvLy8iIiLWSdWYAAAAAXRSTlMAQObYZgAAAQVJREFUSMftlM0RgjAQhV+0ATYK6i1Xb+iMd0qgBEqgBEuwBOxU2QDKsjvojQPvkJ/ZL5sXkgWrFirK4MibYUdE3OR2nEpuKz1/q8CdNxNQgthZCXYVLjyoDQftaKuniHHWRnPh2GCUetR2/9HsMAXyUT4/3UHwtQT2AggSCGKeSAsFnxBIOuAggdh3AKTL7pDuCyABcMb0aQP7aM4AnAbc/wHwA5D2wDHTTe56gIIOUA/4YYV2e1sg713PXdZJAuncdZMAGkAukU9OAn40O849+0ornPwT93rphWF0mgAbauUrEOthlX8Zu7P5A6kZyKCJy75hhw1Mgr9RAUvX7A3csGqZegEdniCx30c3agAAAABJRU5ErkJggg==" alt="onebot">
</a>
<a href="https://onebot.dev/">
  <img src="https://img.shields.io/badge/OneBot-v12-black?style=social&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABABAMAAABYR2ztAAAAIVBMVEUAAAAAAAADAwMHBwceHh4UFBQNDQ0ZGRkoKCgvLy8iIiLWSdWYAAAAAXRSTlMAQObYZgAAAQVJREFUSMftlM0RgjAQhV+0ATYK6i1Xb+iMd0qgBEqgBEuwBOxU2QDKsjvojQPvkJ/ZL5sXkgWrFirK4MibYUdE3OR2nEpuKz1/q8CdNxNQgthZCXYVLjyoDQftaKuniHHWRnPh2GCUetR2/9HsMAXyUT4/3UHwtQT2AggSCGKeSAsFnxBIOuAggdh3AKTL7pDuCyABcMb0aQP7aM4AnAbc/wHwA5D2wDHTTe56gIIOUA/4YYV2e1sg713PXdZJAuncdZMAGkAukU9OAn40O849+0ornPwT93rphWF0mgAbauUrEOthlX8Zu7P5A6kZyKCJy75hhw1Mgr9RAUvX7A3csGqZegEdniCx30c3agAAAABJRU5ErkJggg==" alt="onebot">
</a>
<a href="https://bot.q.qq.com/wiki/">
  <img src="https://img.shields.io/badge/QQ-Bot-lightgrey?style=social&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMTIuODIgMTMwLjg5Ij48ZyBkYXRhLW5hbWU9IuWbvuWxgiAyIj48ZyBkYXRhLW5hbWU9IuWbvuWxgiAxIj48cGF0aCBkPSJNNTUuNjMgMTMwLjhjLTcgMC0xMy45LjA4LTIwLjg2IDAtMTkuMTUtLjI1LTMxLjcxLTExLjQtMzQuMjItMzAuMy00LjA3LTMwLjY2IDE0LjkzLTU5LjIgNDQuODMtNjYuNjQgMi0uNTEgNS4yMS0uMzEgNS4yMS0xLjYzIDAtMi4xMy4xNC0yLjEzLjE0LTUuNTcgMC0uODktMS4zLTEuNDYtMi4yMi0yLjMxLTYuNzMtNi4yMy03LjY3LTEzLjQxLTEtMjAuMTggNS40LTUuNTIgMTEuODctNS40IDE3LjgtLjU5IDYuNDkgNS4yNiA2LjMxIDEzLjA4LS44NiAyMS0uNjguNzQtMS43OCAxLjYtMS43OCAyLjY3djQuMjFjMCAxLjM1IDIuMiAxLjYyIDQuNzkgMi4zNSAzMS4wOSA4LjY1IDQ4LjE3IDM0LjEzIDQ1IDY2LjM3LTEuNzYgMTguMTUtMTQuNTYgMzAuMjMtMzIuNyAzMC42My04LjAyLjE5LTE2LjA3LS4wMS0yNC4xMy0uMDF6IiBmaWxsPSIjMDI5OWZlIi8+PHBhdGggZD0iTTMxLjQ2IDExOC4zOGMtMTAuNS0uNjktMTYuOC02Ljg2LTE4LjM4LTE3LjI3LTMtMTkuNDIgMi43OC0zNS44NiAxOC40Ni00Ny44MyAxNC4xNi0xMC44IDI5Ljg3LTEyIDQ1LjM4LTMuMTkgMTcuMjUgOS44NCAyNC41OSAyNS44MSAyNCA0NS4yOS0uNDkgMTUuOS04LjQyIDIzLjE0LTI0LjM4IDIzLjUtNi41OS4xNC0xMy4xOSAwLTE5Ljc5IDAiIGZpbGw9IiNmZWZlZmUiLz48cGF0aCBkPSJNNDYuMDUgNzkuNThjLjA5IDUgLjIzIDkuODItNyA5Ljc3LTcuODItLjA2LTYuMS01LjY5LTYuMjQtMTAuMTktLjE1LTQuODItLjczLTEwIDYuNzMtOS44NHM2LjM3IDUuNTUgNi41MSAxMC4yNnoiIGZpbGw9IiMxMDlmZmUiLz48cGF0aCBkPSJNODAuMjcgNzkuMjdjLS41MyAzLjkxIDEuNzUgOS42NC01Ljg4IDEwLTcuNDcuMzctNi44MS00LjgyLTYuNjEtOS41LjItNC4zMi0xLjgzLTEwIDUuNzgtMTAuNDJzNi41OSA0Ljg5IDYuNzEgOS45MnoiIGZpbGw9IiMwODljZmUiLz48L2c+PC9nPjwvc3ZnPg==" alt="QQ">
</a>
<br>
<a href="https://www.codefactor.io/repository/github/cg8-5712/nonebot-plugin-eaip/">
    <img src="https://www.codefactor.io/repository/github/cg8-5712/nonebot-plugin-eaip/badge" alt="CodeFactor" />
</a>
<a href="./LICENSE">
    <img src="https://img.shields.io/badge/license-GPL3.0-FE7D37" alt="license">
</a>
<a href="https://github.com/cg8-5712/nonebot-plugin-eaip/activity">
    <img src="https://img.shields.io/github/last-commit/cg8-5712/nonebot-plugin-eaip/main" alt="Last Commit"/>
</a>


</div>

## Overview

This plugin provides functionality to query and manage aeronautical charts from electronic Aeronautical Information Publications (eAIP). It supports various chart types including SID, STAR, IAC, and more.

## Features

- Query charts by ICAO airport code
- Filter charts by type (SID, STAR, IAC, etc.)
- Support for multiple AIRAC cycles
- PDF to image conversion for chart display
- Automatic chart organization and indexing
- Both text and image-based chart listings

## Installation

1. Install the plugin in your Zhenxun Bot plugins directory:
```bash
git clone https://github.com/cg8-5712/nonebot-plugin-eaip.git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Commands

- Basic chart query:
```
@Bot eaip [ICAO]
```

- Query specific chart type:
```
@Bot eaip [ICAO] [CHART_TYPE]
```

- Query by runway:
```
@Bot eaip [ICAO] [RUNWAY]
```

- Search by code:
```
@Bot eaip [ICAO] -c [CODE]
```

- Search by filename:
```
@Bot eaip [ICAO] -f [KEYWORD]
```

- Update AIRAC cycle (admin only):
```
@Bot eaip set [PERIOD]
```

### Supported Chart Types

- ADC (Aerodrome Chart)
- APDC (Aircraft Parking/Docking Chart)
- GMC (Ground Movement Chart)
- SID (Standard Instrument Departure)
- STAR (Standard Terminal Arrival Route)
- IAC (Instrument Approach Chart)
- And more...

## Configuration

The plugin configuration is managed through Zhenxun Bot's config system:

```python
Config.add_plugin_config(
    "eaip",
    "AIRAC_PERIOD",
    2505,
    help="Current AIRAC cycle (e.g., 2505)",
    type=int
)

Config.add_plugin_config(
    "eaip",
    "DIR_NAME",
    "EAIP2025-05.V1.3",
    help="eAIP directory name",
    type=str
)
```

## Dependencies

See [requirements.txt](requirements.txt)

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Author

cg8-5712

## Version

1.5.0