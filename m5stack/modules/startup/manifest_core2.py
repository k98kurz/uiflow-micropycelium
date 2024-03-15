# SPDX-FileCopyrightText: 2024 M5Stack Technology CO LTD
#
# SPDX-License-Identifier: MIT

package(
    "startup",
    (
        "__init__.py",
        "core2/__init__.py",
        "core2/app.py",
        "core2/framework.py",
        "core2/apps/app_list.py",
        "core2/apps/app_run.py",
        "core2/apps/dev.py",
        "core2/apps/ezdata.py",
        "core2/apps/settings.py",
        "core2/apps/status_bar.py",
    ),
    base_path="..",
    opt=3,
)
