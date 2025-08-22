from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from policy_merger.models import PolicyRule


# -----------------------------
# Object catalog (optional)
# -----------------------------


@dataclass
class Address:
    name: str
    subnet: Tuple[str, str]  # (ip, mask)
    comment: Optional[str] = None


@dataclass
class AddressGroup:
    name: str
    members: List[str]
    comment: Optional[str] = None


@dataclass
class Service:
    name: str
    tcp_portrange: Optional[str] = None  # e.g., "80-80 443-443"
    udp_portrange: Optional[str] = None  # e.g., "500-500 4500-4500"
    comment: Optional[str] = None


@dataclass
class ServiceGroup:
    name: str
    members: List[str]
    comment: Optional[str] = None


@dataclass
class Vip:
    name: str
    extip: str
    mappedip: str
    extintf: Optional[str] = None
    portforward: bool = False
    extport: Optional[str] = None
    mappedport: Optional[str] = None
    comment: Optional[str] = None


@dataclass
class IpPool:
    name: str
    startip: str
    endip: str
    pool_type: Optional[str] = None  # overload|one-to-one
    comment: Optional[str] = None


@dataclass
class ObjectCatalog:
    addresses: Dict[str, Address] = field(default_factory=dict)
    addr_groups: Dict[str, AddressGroup] = field(default_factory=dict)
    services: Dict[str, Service] = field(default_factory=dict)
    service_groups: Dict[str, ServiceGroup] = field(default_factory=dict)
    vips: Dict[str, Vip] = field(default_factory=dict)
    ippools: Dict[str, IpPool] = field(default_factory=dict)


# -----------------------------
# Utilities
# -----------------------------


def _q(name: str) -> str:
    """Quote a FortiOS object name safely for CLI."""
    safe = name.replace('"', "'")
    return f'"{safe}"'


def _split_values(value: Optional[str]) -> List[str]:
    """Split a multi-value cell conservatively.

    FortiManager CSV typically separates multiple names by spaces. Names with
    spaces are uncommon but possible; in that edge case users should rely on an
    object catalog to avoid naive tokenization. Here we split by whitespace and
    filter empties.
    """
    if not value:
        return []
    s = value.strip()
    if not s:
        return []
    # Normalize whitespace to single spaces then split
    tokens = [t for t in " ".join(s.split()).split(" ") if t]
    return tokens


def _emit_block(header: str, lines: Iterable[str]) -> List[str]:
    emitted = [header]
    emitted.extend(lines)
    emitted.append("end")
    return emitted


def _emit_edit_block(name: str, setters: Iterable[str]) -> List[str]:
    lines = [f"    edit {_q(name)}"]
    for s in setters:
        if s:
            lines.append(f"        {s}")
    lines.append("    next")
    return lines


# -----------------------------
# Generators per section
# -----------------------------


def generate_addresses(addresses: Dict[str, Address]) -> List[str]:
    if not addresses:
        return []
    lines: List[str] = []
    for name in sorted(addresses.keys()):
        a = addresses[name]
        setters = [
            f"set subnet {a.subnet[0]} {a.subnet[1]}",
            f"set comment {_q(a.comment)}" if a.comment else None,
        ]
        lines.extend(_emit_edit_block(a.name, setters))
    return _emit_block("config firewall address", lines)


def generate_address_groups(groups: Dict[str, AddressGroup]) -> List[str]:
    if not groups:
        return []
    lines: List[str] = []
    for name in sorted(groups.keys()):
        g = groups[name]
        members = " ".join(_q(m) for m in sorted(set(g.members))) if g.members else None
        setters = [
            f"set member {members}" if members else None,
            f"set comment {_q(g.comment)}" if g.comment else None,
        ]
        lines.extend(_emit_edit_block(g.name, setters))
    return _emit_block("config firewall addrgrp", lines)


def generate_services(services: Dict[str, Service]) -> List[str]:
    if not services:
        return []
    lines: List[str] = []
    for name in sorted(services.keys()):
        s = services[name]
        setters = [
            f"set tcp-portrange {s.tcp_portrange}" if s.tcp_portrange else None,
            f"set udp-portrange {s.udp_portrange}" if s.udp_portrange else None,
            f"set comment {_q(s.comment)}" if s.comment else None,
        ]
        lines.extend(_emit_edit_block(s.name, setters))
    return _emit_block("config firewall service custom", lines)


def generate_service_groups(groups: Dict[str, ServiceGroup]) -> List[str]:
    if not groups:
        return []
    lines: List[str] = []
    for name in sorted(groups.keys()):
        g = groups[name]
        members = " ".join(_q(m) for m in sorted(set(g.members))) if g.members else None
        setters = [
            f"set member {members}" if members else None,
            f"set comment {_q(g.comment)}" if g.comment else None,
        ]
        lines.extend(_emit_edit_block(g.name, setters))
    return _emit_block("config firewall service group", lines)


def generate_vips(vips: Dict[str, Vip]) -> List[str]:
    if not vips:
        return []
    lines: List[str] = []
    for name in sorted(vips.keys()):
        v = vips[name]
        setters = [
            f"set extip {v.extip}",
            f"set mappedip {_q(v.mappedip)}",
            f"set extintf {_q(v.extintf)}" if v.extintf else None,
            "set portforward enable" if v.portforward else None,
            f"set extport {v.extport}" if v.extport else None,
            f"set mappedport {v.mappedport}" if v.mappedport else None,
            f"set comment {_q(v.comment)}" if v.comment else None,
        ]
        lines.extend(_emit_edit_block(v.name, setters))
    return _emit_block("config firewall vip", lines)


def generate_ippools(pools: Dict[str, IpPool]) -> List[str]:
    if not pools:
        return []
    lines: List[str] = []
    for name in sorted(pools.keys()):
        p = pools[name]
        setters = [
            f"set startip {p.startip}",
            f"set endip {p.endip}",
            f"set type {p.pool_type}" if p.pool_type else None,
            f"set comment {_q(p.comment)}" if p.comment else None,
        ]
        lines.extend(_emit_edit_block(p.name, setters))
    return _emit_block("config firewall ippool", lines)


def generate_policies(rules: Sequence[PolicyRule]) -> List[str]:
    if not rules:
        return []
    lines: List[str] = []
    for rule in rules:
        r = rule.raw
        srcintf = _split_values(r.get("srcintf"))
        dstintf = _split_values(r.get("dstintf"))
        srcaddr = _split_values(r.get("srcaddr"))
        dstaddr = _split_values(r.get("dstaddr"))
        services = _split_values(r.get("service"))

        srcintf_line = (
            f"set srcintf {' '.join(_q(i) for i in srcintf)}" if srcintf else "set srcintf \"any\""
        )
        dstintf_line = (
            f"set dstintf {' '.join(_q(i) for i in dstintf)}" if dstintf else "set dstintf \"any\""
        )
        setters = [
            # allocate next-id; name for determinism
            f"set name {_q(r.get('name', r.get('policyid', 'policy')))}",
            srcintf_line,
            dstintf_line,
            f"set srcaddr {' '.join(_q(a) for a in srcaddr)}" if srcaddr else "set srcaddr \"all\"",
            f"set dstaddr {' '.join(_q(a) for a in dstaddr)}" if dstaddr else "set dstaddr \"all\"",
            f"set service {' '.join(_q(s) for s in services)}" if services else "set service \"ALL\"",
            f"set schedule {_q(r.get('schedule', 'always'))}",
            f"set action {r.get('action', 'accept')}",
            "set nat enable" if str(r.get("nat", "disable")).lower() in {"enable", "1", "true", "yes"} else None,
        ]
        policy_lines = ["    edit 0"]
        for s in setters:
            if s:
                policy_lines.append(f"        {s}")
        policy_lines.append("    next")
        lines.extend(policy_lines)

    return _emit_block("config firewall policy", lines)


# -----------------------------
# Orchestrator
# -----------------------------


def generate_fgt_cli(
    rules: Sequence[PolicyRule],
    catalog: Optional[ObjectCatalog] = None,
    include_objects: bool = True,
) -> str:
    sections: List[str] = []

    # Header banner (comments)
    sections.append("# Generated by Policy Merger\n# Version: 1.0.0\n")

    if include_objects and catalog is not None:
        # Emit in required order
        for emitter, data in [
            (generate_addresses, catalog.addresses),
            (generate_address_groups, catalog.addr_groups),
            (generate_services, catalog.services),
            (generate_service_groups, catalog.service_groups),
            (generate_vips, catalog.vips),
            (generate_ippools, catalog.ippools),
        ]:
            block = emitter(data)
            if block:
                sections.append("\n".join(block) + "\n")

    policy_block = generate_policies(rules)
    if policy_block:
        sections.append("\n".join(policy_block) + "\n")

    return "\n".join(sections)


