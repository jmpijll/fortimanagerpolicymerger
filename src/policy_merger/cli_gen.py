from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Set

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
    # Normalize whitespace to single spaces and split
    s = " ".join(s.split())
    raw = [t for t in s.split(" ") if t]
    # Pair tokens like ["VLAN201:", "Office"] into "VLAN201: Office"
    paired: List[str] = []
    i = 0
    while i < len(raw):
        tok = raw[i]
        if tok.endswith(":") and i + 1 < len(raw):
            paired.append(f"{tok} {raw[i+1]}")
            i += 2
            continue
        if tok.endswith(":"):
            tok = tok[:-1]
        paired.append(tok)
        i += 1
    # de-duplicate while preserving order
    seen: set = set()
    uniq: List[str] = []
    for t in paired:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


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
# Catalog-aware greedy mapping of tokens into known names
def _map_tokens_with_catalog(value: Optional[str], known_names: Set[str]) -> List[str]:
    if not value:
        return []
    s = value.strip()
    if not s or not known_names:
        return _split_values(value)
    # Normalize whitespace and split to raw tokens without pairing
    raw_tokens = [t for t in " ".join(s.split()).split(" ") if t]
    i = 0
    out: List[str] = []
    n = len(raw_tokens)
    while i < n:
        matched = None
        # Try longest span first
        for j in range(n, i, -1):
            cand = " ".join(raw_tokens[i:j])
            if cand in known_names:
                matched = cand
                i = j
                break
        if matched is None:
            # Fallback to single token
            matched = raw_tokens[i]
            i += 1
        out.append(matched)
    # De-duplicate while preserving order
    seen: Set[str] = set()
    uniq: List[str] = []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq

# -----------------------------
# Helpers for profiles/logging
# -----------------------------


def _truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"enable", "enabled", "1", "true", "yes"}


def _has_any_profile(r: Dict[str, str]) -> bool:  # type: ignore[name-defined]
    for k in ("av-profile", "webfilter-profile", "dnsfilter-profile", "ips-sensor", "application-list", "ssl-ssh-profile"):
        if r.get(k):
            return True
    return False


def _map_logtraffic(val: Optional[str]) -> str:
    if not val:
        return "utm"
    s = str(val).strip().lower()
    # Map common CSV values to CLI
    if s in {"utm", "all", "disable"}:
        return s
    if s in {"enabled", "enable", "yes", "true"}:
        return "all"
    if s in {"no", "false"}:
        return "disable"
    return s


# -----------------------------
# Interface token mapping (FMG → FGT CLI)
# -----------------------------


def _map_interface_tokens(value: Optional[str]) -> List[str]:
    if not value:
        return []
    s = " ".join(value.strip().split())
    if not s:
        return []
    raw_tokens = [t for t in s.split(" ") if t]
    mapped: List[str] = []
    for tok in raw_tokens:
        t = tok.strip()
        if not t:
            continue
        # FMG placeholder for SSL VPN tunnel interface
        if t.lower() == "sslvpn_tun_intf":
            t = "ssl.root"
        # Expand zone.interface shorthand: "_default.VLAN1" → "_default", "VLAN1"
        if t.startswith("_") and "." in t and not t.startswith("\""):
            zone, iface = t.split(".", 1)
            if zone:
                mapped.append(zone)
            if iface:
                mapped.append(iface)
            continue
        mapped.append(t)
    # de-duplicate while preserving order
    seen: set = set()
    out: List[str] = []
    for m in mapped:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out



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


def generate_policies(rules: Sequence[PolicyRule], name_overrides: Optional[List[str]] = None, catalog: Optional[ObjectCatalog] = None) -> List[str]:
    if not rules:
        return []
    lines: List[str] = []
    for idx, rule in enumerate(rules):
        r = rule.raw
        srcintf = _map_interface_tokens(r.get("srcintf"))
        dstintf = _map_interface_tokens(r.get("dstintf"))
        # Address/service mapping: prefer catalog names if provided
        if catalog is not None:
            addr_names: Set[str] = (
                set(catalog.addresses.keys())
                | set(catalog.addr_groups.keys())
                | set(catalog.vips.keys())
            )
            svc_names: Set[str] = set(catalog.services.keys()) | set(catalog.service_groups.keys())
            srcaddr = _map_tokens_with_catalog(r.get("srcaddr"), addr_names)
            dstaddr = _map_tokens_with_catalog(r.get("dstaddr"), addr_names)
            services = _map_tokens_with_catalog(r.get("service"), svc_names)
        else:
            srcaddr = _split_values(r.get("srcaddr"))
            dstaddr = _split_values(r.get("dstaddr"))
            services = _split_values(r.get("service"))
        # Dominance rules: if 'all'/'any' present in addresses or 'ALL' in services
        if any(t.lower() == 'all' or t.lower() == 'any' for t in srcaddr):
            srcaddr = ['all']
        if any(t.lower() == 'all' or t.lower() == 'any' for t in dstaddr):
            dstaddr = ['all']
        if any(t.upper() == 'ALL' for t in services):
            services = ['ALL']
        # name override (if provided)
        name_value = None
        if name_overrides is not None and 0 <= idx < len(name_overrides):
            name_value = name_overrides[idx]
        if not name_value:
            name_value = r.get('name', r.get('policyid', 'policy'))

        srcintf_line = (
            f"set srcintf {' '.join(_q(i) for i in srcintf)}" if srcintf else "set srcintf \"any\""
        )
        dstintf_line = (
            f"set dstintf {' '.join(_q(i) for i in dstintf)}" if dstintf else "set dstintf \"any\""
        )
        setters = [
            # allocate next-id; name for determinism
            f"set name {_q(name_value)}",
            srcintf_line,
            dstintf_line,
            f"set srcaddr {' '.join(_q(a) for a in srcaddr)}" if srcaddr else "set srcaddr \"all\"",
            f"set dstaddr {' '.join(_q(a) for a in dstaddr)}" if dstaddr else "set dstaddr \"all\"",
            f"set service {' '.join(_q(s) for s in services)}" if services else "set service \"ALL\"",
            f"set schedule {_q(r.get('schedule', 'always'))}",
            f"set action {r.get('action', 'accept')}",
            "set nat enable" if str(r.get("nat", "disable")).lower() in {"enable", "1", "true", "yes"} else None,
            # Profiles and logging (only when present)
            "set utm-status enable" if _truthy(r.get("utm-status")) or _has_any_profile(r) else None,
            f"set av-profile {_q(r['av-profile'])}" if r.get('av-profile') else None,
            f"set webfilter-profile {_q(r['webfilter-profile'])}" if r.get('webfilter-profile') else None,
            f"set dnsfilter-profile {_q(r['dnsfilter-profile'])}" if r.get('dnsfilter-profile') else None,
            f"set ips-sensor {_q(r['ips-sensor'])}" if r.get('ips-sensor') else None,
            f"set application-list {_q(r['application-list'])}" if r.get('application-list') else None,
            f"set ssl-ssh-profile {_q(r['ssl-ssh-profile'])}" if r.get('ssl-ssh-profile') else None,
            f"set logtraffic {_map_logtraffic(r.get('logtraffic'))}" if r.get('logtraffic') else None,
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


def build_unique_policy_names(rules: Sequence[PolicyRule], max_len: int = 35) -> Tuple[List[str], List[Tuple[str, str]]]:
    """Create unique policy names within max_len. Returns (overrides, renames).

    - overrides: list aligned with rules containing the final name for each rule
    - renames: list of (original_name, new_name) for entries that changed
    """
    used: set[str] = set()
    overrides: List[str] = []
    renames: List[Tuple[str, str]] = []

    def _truncate_for_suffix(base: str, suffix: str) -> str:
        if len(base) + len(suffix) <= max_len:
            return base
        return base[: max_len - len(suffix)]

    for rule in rules:
        base_name = str(rule.raw.get('name') or rule.raw.get('policyid') or 'policy').strip()
        if not base_name:
            base_name = 'policy'
        candidate = base_name if len(base_name) <= max_len else base_name[:max_len]
        if candidate not in used:
            used.add(candidate)
            overrides.append(candidate)
            continue
        # Need to add numeric suffix -1, -2, ... ensuring uniqueness and length
        i = 1
        while True:
            suffix = f"-{i}"
            cand = _truncate_for_suffix(base_name, suffix) + suffix
            if cand not in used:
                used.add(cand)
                overrides.append(cand)
                if cand != base_name:
                    renames.append((base_name, cand))
                break
            i += 1
    return overrides, renames


def generate_fgt_cli(
    rules: Sequence[PolicyRule],
    catalog: Optional[ObjectCatalog] = None,
    include_objects: bool = False,
    name_overrides: Optional[List[str]] = None,
) -> str:
    sections: List[str] = []

    # Header banner (comments)
    sections.append("# Generated by Policy Merger\n# Version: 1.0.0\n")

    # Ensure unique policy names
    overrides: Optional[List[str]] = None
    renames: List[Tuple[str, str]] = []
    if name_overrides is not None:
        overrides = name_overrides
    else:
        overrides, renames = build_unique_policy_names(rules, max_len=35)
    if renames:
        sections.append("# Renamed policies for uniqueness (max 35):")
        for old, new in renames[:200]:  # cap to keep script concise
            sections.append(f"# {old} -> {new}")
        sections.append("")

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

    policy_block = generate_policies(rules, name_overrides=overrides, catalog=catalog)
    if policy_block:
        sections.append("\n".join(policy_block) + "\n")

    return "\n".join(sections)


