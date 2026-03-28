from __future__ import annotations
from sts2_simulator.data.registry import BuffDef, Registry


def register_builtin_buffs(registry: Registry) -> None:
    registry.register_buff(BuffDef(
        id="strength",
        name="力量",
        is_permanent=False,
        reduce_on="turn_end",
    ))
    registry.register_buff(BuffDef(
        id="dexterity",
        name="敏捷",
        is_permanent=False,
        reduce_on="turn_end",
    ))
    registry.register_buff(BuffDef(
        id="vulnerable",
        name="脆弱",
        is_permanent=False,
        reduce_on="turn_start",
    ))
    registry.register_buff(BuffDef(
        id="weak",
        name="虚弱",
        is_permanent=False,
        reduce_on="turn_start",
    ))
    registry.register_buff(BuffDef(
        id="ritual",
        name="仪式",
        is_permanent=False,
        reduce_on="turn_end",
    ))
