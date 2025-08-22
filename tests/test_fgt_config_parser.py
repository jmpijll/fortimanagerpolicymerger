from policy_merger.fgt_config_parser import parse_fgt_config_text


def test_parse_minimal_objects():
    cfg = (
        "config firewall address\n"
        "    edit \"HQ\"\n"
        "        set subnet 10.10.0.0 255.255.0.0\n"
        "    next\n"
        "end\n"
        "config firewall addrgrp\n"
        "    edit \"Sites\"\n"
        "        set member \"HQ\"\n"
        "    next\n"
        "end\n"
        "config firewall service custom\n"
        "    edit \"Web\"\n"
        "        set tcp-portrange 80-80 443-443\n"
        "    next\n"
        "end\n"
        "config firewall service group\n"
        "    edit \"Common\"\n"
        "        set member \"Web\"\n"
        "    next\n"
        "end\n"
        "config firewall vip\n"
        "    edit \"VIP1\"\n"
        "        set extip 1.2.3.4\n"
        "        set mappedip \"10.1.1.10\"\n"
        "    next\n"
        "end\n"
        "config firewall ippool\n"
        "    edit \"Pool1\"\n"
        "        set startip 5.5.5.5\n"
        "        set endip 5.5.5.10\n"
        "        set type overload\n"
        "    next\n"
        "end\n"
    )
    cat = parse_fgt_config_text(cfg)
    assert "HQ" in cat.addresses and cat.addresses["HQ"].subnet[0] == "10.10.0.0"
    assert "Sites" in cat.addr_groups and cat.addr_groups["Sites"].members == ["HQ"]
    assert "Web" in cat.services and cat.services["Web"].tcp_portrange == "80-80 443-443"
    assert "Common" in cat.service_groups and cat.service_groups["Common"].members == ["Web"]
    assert "VIP1" in cat.vips and cat.vips["VIP1"].mappedip == "10.1.1.10"
    assert "Pool1" in cat.ippools and cat.ippools["Pool1"].pool_type == "overload"


