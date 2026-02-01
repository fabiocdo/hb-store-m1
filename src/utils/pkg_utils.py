import subprocess
import tempfile
import struct
from pathlib import Path
from enum import Enum
import os


class PkgUtils:
    """
    PkgUtils provides methods to interact with PKG files via pkgtool.

    It handles entry listing, SFO metadata extraction and icon extraction.
    """

    class ExtractResult(Enum):
        OK = "ok"
        SKIP = "skip"
        NOT_FOUND = "not_found"
        INVALID = "invalid"
        ERROR = "error"

    def __init__(self):
        """
        Initialize PkgUtils.
        """
        self.pkgtool_path = os.getenv("PKGTOOL_PATH")
        self.env = {
            "DOTNET_SYSTEM_GLOBALIZATION_INVARIANT": os.environ["DOTNET_SYSTEM_GLOBALIZATION_INVARIANT"],
        }

    def extract_pkg_data(self, pkg: Path) -> tuple[ExtractResult, str]:
        """
        Extract and parse PARAM.SFO data from a PKG.

        :param pkg: Path to the PKG file
        :return: Tuple of (ExtractResult, path string)
        """

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                result = subprocess.run(
                    [self.pkgtool_path, "pkg_listentries", str(pkg)],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=self.env,
                )

                param_sfo_index = None
                lines = result.stdout.strip().splitlines()
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) < 5:
                        continue
                    index = int(parts[3])
                    name = parts[5] if parts[4].isdigit() else parts[4]
                    if name == "PARAM_SFO":
                        param_sfo_index = index
                        break

                if param_sfo_index is None:
                    return self.ExtractResult.NOT_FOUND, str(pkg)

                param_sfo_path = os.path.join(tmp_dir, "PARAM.SFO")

                subprocess.run(
                    [
                        self.pkgtool_path,
                        "pkg_extractentry",
                        str(pkg),
                        str(param_sfo_index),
                        param_sfo_path,
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=self.env,
                )

                with open(param_sfo_path, "rb") as f:
                    data = f.read()
        except subprocess.CalledProcessError:
            return self.ExtractResult.ERROR, str(pkg)

        result = {}

        magic, version, key_table_offset, data_table_offset, entry_count = struct.unpack_from(
            "<4sIIII", data, 0
        )

        if magic != b"\x00PSF":
            return self.ExtractResult.INVALID, str(pkg)

        entries_offset = 0x14

        for i in range(entry_count):
            off = entries_offset + i * 0x10

            key_off, data_fmt, data_len, data_max, data_off = struct.unpack_from(
                "<HHIII", data, off
            )

            key = data[key_table_offset + key_off :].split(b"\x00", 1)[0].decode(
                "utf-8", errors="ignore"
            )

            raw = data[
                data_table_offset + data_off : data_table_offset + data_off + data_len
            ]

            if key == "PUBTOOLVER":
                # explicitly treat as HEX
                value = raw.hex()

            elif data_fmt == 0x0404:  # string
                value = raw.rstrip(b"\x00").decode("utf-8", errors="ignore")

            elif data_fmt == 0x0402:  # int
                value = struct.unpack("<I", raw[:4])[0]

            else:
                try:
                    value = raw.rstrip(b"\x00").decode("utf-8")
                except UnicodeDecodeError:
                    value = raw.hex()

            result[key] = value

            if key == "PUBTOOLINFO" and isinstance(value, str):
                for part in value.split(","):
                    if part.startswith("c_date="):
                        c_date = part.split("=", 1)[1].strip()
                        if len(c_date) == 8 and c_date.isdigit():
                            result["release_date"] = f"{c_date[:4]}-{c_date[4:6]}-{c_date[6:8]}"
                        break

        return self.ExtractResult.OK, str(pkg)

    def extract_pkg_icon(self, pkg: Path, content_id: str) -> tuple[ExtractResult, str]:
        """
        Extract ICON0.PNG from a PKG.

        :param pkg: Path to the PKG file
        :param content_id: Content ID used as icon filename (without extension)
        :return: Tuple of (ExtractResult, path string)
        """
        output_dir = os.environ["MEDIA_DIR"]
        os.makedirs(output_dir, exist_ok=True)

        result = subprocess.run(
            [self.pkgtool_path, "pkg_listentries", str(pkg)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=self.env,
        )

        icon_index = None
        lines = result.stdout.strip().splitlines()
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 5:
                continue
            index = int(parts[3])
            name = parts[5] if parts[4].isdigit() else parts[4]
            if name == "ICON0_PNG":
                icon_index = index
                break

        final_name = f"{content_id}.png"
        final_path = os.path.join(output_dir, final_name)
        if os.path.exists(final_path):
            return self.ExtractResult.SKIP, final_path

        if icon_index is None:
            return self.ExtractResult.NOT_FOUND, str(pkg)

        subprocess.run(
            [
                self.pkgtool_path,
                "pkg_extractentry",
                str(pkg),
                str(icon_index),
                final_path,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=self.env,
        )

        return self.ExtractResult.OK, final_path
