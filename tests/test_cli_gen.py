from policy_merger.cli_gen import (
    Address,
    AddressGroup,
    ObjectCatalog,
    Service,
    ServiceGroup,
    Vip,
    IpPool,
    generate_fgt_cli,
)
from policy_merger.models import PolicyRule


def make_rule(**kv):
    return PolicyRule(raw=kv, source_fortigate="FGT")


def test_generate_simple_policy_only():
    rules = [
        make_rule(
            name="AllowWeb",
            srcintf="port1",
            dstintf="port2",
            srcaddr="HQ-NET",
            dstaddr="DC-NET",
            service="HTTP HTTPS",
            schedule="always",
            action="accept",
            nat="enable",
        )
    ]
    cli = generate_fgt_cli(rules, catalog=None, include_objects=False)
    assert "config firewall policy" in cli
    assert "set name \"AllowWeb\"" in cli
    assert "set srcintf \"port1\"" in cli
    assert "set service \"HTTP\" \"HTTPS\"" in cli


def test_generate_with_objects_ordering():
    catalog = ObjectCatalog(
        addresses={
            "HQ-NET": Address(name="HQ-NET", subnet=("10.10.0.0", "255.255.0.0")),
            "DC-NET": Address(name="DC-NET", subnet=("10.20.0.0", "255.255.0.0")),
        },
        addr_groups={
            "Sites": AddressGroup(name="Sites", members=["HQ-NET", "DC-NET"])
        },
        services={
            "Web": Service(name="Web", tcp_portrange="80-80 443-443")
        },
        service_groups={
            "Common": ServiceGroup(name="Common", members=["Web"])
        },
        vips={
            "VIP1": Vip(name="VIP1", extip="1.2.3.4", mappedip="10.1.1.10")
        },
        ippools={
            "Pool1": IpPool(name="Pool1", startip="5.5.5.5", endip="5.5.5.10", pool_type="overload")
        },
    )
    rules = [
        make_rule(
            name="AllowWeb",
            srcintf="port1",
            dstintf="port2",
            srcaddr="Sites",
            dstaddr="VIP1",
            service="Common",
            schedule="always",
            action="accept",
            nat="enable",
        )
    ]

    cli = generate_fgt_cli(rules, catalog=catalog)
    # Basic sanity: each section present in order
    assert cli.find("config firewall address") < cli.find("config firewall addrgrp")
    assert cli.find("config firewall service custom") < cli.find("config firewall service group")
    assert cli.find("config firewall vip") < cli.find("config firewall policy")
    # Members are emitted in sorted order for determinism
    assert "set member \"DC-NET\" \"HQ-NET\"" in cli
    assert "set tcp-portrange 80-80 443-443" in cli

