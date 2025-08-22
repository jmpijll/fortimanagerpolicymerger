from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional

from policy_merger.cli_gen import (
    Address,
    AddressGroup,
    Service,
    ServiceGroup,
    Vip,
    IpPool,
    ObjectCatalog,
)


def _extract_blocks(lines: List[str], header: str) -> List[List[str]]:
    blocks: List[List[str]] = []
    in_section = False
    section_lines: List[str] = []
    for ln in lines:
        s = ln.strip()
        if s == header:
            in_section = True
            section_lines = []
            continue
        if in_section and s == "end":
            in_section = False
            blocks.append(section_lines[:])
            section_lines = []
            continue
        if in_section:
            section_lines.append(ln)
    return blocks


_re_edit = re.compile(r"\bedit\s+\"(?P<name>[^\"]+)\"")
_re_set = re.compile(r"\bset\s+(?P<key>\S+)\s+(?P<val>.+)$")


def _parse_table(block: List[str]) -> Dict[str, Dict[str, str]]:
    """Parse a FortiOS table section into name→{key:value} dict."""
    result: Dict[str, Dict[str, str]] = {}
    current: Optional[str] = None
    for raw in block:
        s = raw.strip()
        m_edit = _re_edit.search(s)
        if m_edit:
            current = m_edit.group("name")
            result[current] = {}
            continue
        m_set = _re_set.search(s)
        if current and m_set:
            key = m_set.group("key").strip()
            val = m_set.group("val").strip()
            result[current][key] = val
        if s == "next":
            current = None
    return result


def parse_fgt_config_text(text: str, catalog: Optional[ObjectCatalog] = None) -> ObjectCatalog:
    """Parse FortiGate config text to ObjectCatalog (best-effort)."""
    if catalog is None:
        catalog = ObjectCatalog()
    lines = text.splitlines()

    # Addresses
    for block in _extract_blocks(lines, "config firewall address"):
        tbl = _parse_table(block)
        for name, kv in tbl.items():
            subnet_val = kv.get("subnet", "").split()
            if len(subnet_val) >= 2:
                ip, mask = subnet_val[0], subnet_val[1]
                catalog.addresses[name] = Address(name=name, subnet=(ip, mask), comment=_strip_quotes(kv.get("comment")))

    # Address groups
    for block in _extract_blocks(lines, "config firewall addrgrp"):
        tbl = _parse_table(block)
        for name, kv in tbl.items():
            members = _split_members(kv.get("member"))
            catalog.addr_groups[name] = AddressGroup(name=name, members=members, comment=_strip_quotes(kv.get("comment")))

    # Services (custom)
    for block in _extract_blocks(lines, "config firewall service custom"):
        tbl = _parse_table(block)
        for name, kv in tbl.items():
            catalog.services[name] = Service(
                name=name,
                tcp_portrange=_strip_quotes(kv.get("tcp-portrange")),
                udp_portrange=_strip_quotes(kv.get("udp-portrange")),
                comment=_strip_quotes(kv.get("comment")),
            )

    # Service groups
    for block in _extract_blocks(lines, "config firewall service group"):
        tbl = _parse_table(block)
        for name, kv in tbl.items():
            members = _split_members(kv.get("member"))
            catalog.service_groups[name] = ServiceGroup(name=name, members=members, comment=_strip_quotes(kv.get("comment")))

    # VIPs
    for block in _extract_blocks(lines, "config firewall vip"):
        tbl = _parse_table(block)
        for name, kv in tbl.items():
            portforward = kv.get("portforward", "").strip().lower() == "enable"
            catalog.vips[name] = Vip(
                name=name,
                extip=_strip_quotes(kv.get("extip", "")),
                mappedip=_strip_quotes(kv.get("mappedip", "")),
                extintf=_strip_quotes(kv.get("extintf")),
                portforward=portforward,
                extport=_strip_quotes(kv.get("extport")),
                mappedport=_strip_quotes(kv.get("mappedport")),
                comment=_strip_quotes(kv.get("comment")),
            )

    # IP pools
    for block in _extract_blocks(lines, "config firewall ippool"):
        tbl = _parse_table(block)
        for name, kv in tbl.items():
            startip = _strip_quotes(kv.get("startip", ""))
            endip = _strip_quotes(kv.get("endip", ""))
            pool_type = _strip_quotes(kv.get("type"))
            catalog.ippools[name] = IpPool(name=name, startip=startip, endip=endip, pool_type=pool_type or None, comment=_strip_quotes(kv.get("comment")))

    return catalog


def _strip_quotes(val: Optional[str]) -> Optional[str]:
    if val is None:
        return None
    s = val.strip()
    if s.startswith('"') and s.endswith('"') and len(s) >= 2:
        return s[1:-1]
    return s


def _split_members(val: Optional[str]) -> List[str]:
    if not val:
        return []
    s = val.strip()
    # members are typically quoted names separated by spaces
    names = re.findall(r'\"([^\"]+)\"', s)
    return names


