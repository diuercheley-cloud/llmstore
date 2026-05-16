import re
from typing import Any


SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?$"
)


class SemanticVersioningService:
    def parse_version(self, version: str) -> dict[str, Any]:
        match = SEMVER_RE.fullmatch(version.strip())
        if not match:
            raise ValueError("invalid semantic version")
        parsed = {
            "major": int(match.group("major")),
            "minor": int(match.group("minor")),
            "patch": int(match.group("patch")),
            "prerelease": match.group("prerelease") or "",
            "raw": version.strip(),
        }
        return parsed

    def compare_versions(self, source: str, target: str) -> dict[str, Any]:
        left = self.parse_version(source)
        right = self.parse_version(target)
        left_tuple = (left["major"], left["minor"], left["patch"])
        right_tuple = (right["major"], right["minor"], right["patch"])
        if left_tuple < right_tuple:
            order = -1
        elif left_tuple > right_tuple:
            order = 1
        else:
            order = 0
        if order == 0 and left["prerelease"] != right["prerelease"]:
            order = -1 if left["prerelease"] and not right["prerelease"] else 1
            if left["prerelease"] and right["prerelease"]:
                order = -1 if left["prerelease"] < right["prerelease"] else 1 if left["prerelease"] > right["prerelease"] else 0
        return {
            "source": left,
            "target": right,
            "order": order,
            "same_major": left["major"] == right["major"],
            "same_minor": left["major"] == right["major"] and left["minor"] == right["minor"],
            "same_patch": left_tuple == right_tuple,
        }

    def is_backward_compatible(self, source: str, target: str) -> bool:
        result = self.compare_versions(source, target)
        if not result["same_major"]:
            return False
        return result["source"]["minor"] <= result["target"]["minor"]

    def is_forward_compatible(self, source: str, target: str) -> bool:
        result = self.compare_versions(source, target)
        if not result["same_major"]:
            return False
        return result["source"]["minor"] >= result["target"]["minor"]

    def is_bidirectional_compatible(self, source: str, target: str) -> bool:
        result = self.compare_versions(source, target)
        return result["same_minor"]

    def explain_version_comparison(self, result: dict[str, Any]) -> str:
        order_map = {-1: "older", 0: "equal", 1: "newer"}
        return (
            f"source={result['source']['raw']} is {order_map[result['order']]} than "
            f"target={result['target']['raw']}; same_major={result['same_major']}; "
            f"same_minor={result['same_minor']}"
        )
