from __future__ import annotations

from policy_merger.csv_loader import find_header_row, read_policy_csv


def test_find_header_row(tmp_path):
    p = tmp_path / "sample.csv"
    p.write_text("prefix\nFirewall Policy\na,b,policyid\n1,2,3\n", encoding="utf-8")
    assert find_header_row(str(p)) == 2


def test_read_policy_csv_parses_columns(tmp_path):
    p = tmp_path / "RG-FOO-DEV-20250101-000000.csv"
    content = (
        "X\n"
        "Firewall Policy\n"
        "policyid,name,srcintf,dstintf,srcaddr,dstaddr,service,schedule,action,nat\n"
        "1,Rule A,port1,port2,SRC,DST,ALL,always,accept,disable\n"
    )
    p.write_text(content, encoding="utf-8")
    ps = read_policy_csv(str(p))
    assert "policyid" in ps.columns
    assert len(ps.rules) == 1
    assert ps.rules[0].raw["name"] == "Rule A"
    assert ps.source_fortigate.startswith("RG-FOO-DEV")


