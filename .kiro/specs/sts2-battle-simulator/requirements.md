# 需求文档

## 简介

本项目为《杀戮尖塔2》（Slay the Spire 2，以下简称 STS2）战斗模拟器，专为强化学习 AI 训练设计。模拟器仅覆盖战斗模块，实现核心战斗逻辑与部分静态资源（卡牌、遗物、怪物数据）。

本项目包含两个子模块：
- **Simulator Core**：纯战斗逻辑模拟器
- **Bridge**：通信中间层，作为本项目的子模块，负责将 Simulator 的状态推送给外部消费方（如 RL 框架），并接收外部指令转发给 Simulator

RL 框架不在本项目范围内，本项目只负责实现 Simulator Core 和 Bridge。

---

## 词汇表

- **Simulator**：STS2 战斗模拟器，本系统的核心组件，负责运行战斗逻辑
- **Bridge**：通信中间层，本项目的子模块，运行于同一进程内，负责将 Simulator 状态序列化并通过 ZeroMQ 推送给外部消费方，同时接收外部指令并转发给 Simulator 执行
- **RL 框架**：强化学习训练框架，外部项目，不在本项目范围内，通过 ZeroMQ 与 Bridge 通信
- **游戏 Mod**：未来可能的替代数据来源，通过 HTTP 与 Bridge 通信，不在本项目范围内
- **Battle**：一场战斗，由玩家与一组敌人组成，按回合制进行
- **Player**：玩家角色，拥有生命值、能量、手牌、遗物等属性
- **Enemy**：敌人单位，拥有生命值、护甲、意图等属性
- **Card**：卡牌，玩家可在战斗中打出的行动单元，具有费用、效果等属性
- **Relic**：遗物，为玩家提供被动效果的道具
- **Buff / Debuff**：增益/减益状态，附加在 Player 或 Enemy 上，影响战斗行为
- **Potion**：药水，Player 持有的一次性消耗品，使用后立即产生效果并从药水槽中移除
- **Intent**：敌人意图，表示敌人下一回合将执行的行动
- **Energy**：能量，玩家每回合开始时获得，用于打出卡牌
- **Block**：格挡值，抵消伤害，回合结束时清零
- **State**：战斗状态快照，包含当前战场所有可观测信息
- **Action**：动作，Wrapper 下发给 Simulator 的指令，如打出卡牌、选择目标、结束回合等
- **Event**：事件，Simulator 主动向 Wrapper 推送的状态变化通知

---

## 需求

### 需求 1：战斗初始化

**用户故事：** 作为 Wrapper，我希望能够初始化一场战斗，以便为强化学习 Agent 提供起始状态。

#### 验收标准

1. WHEN Wrapper 发送初始化指令并提供战斗配置（玩家牌组、遗物列表、敌人组合），THE Simulator SHALL 创建一个新的 Battle 实例并返回初始 State
2. WHEN 战斗初始化完成，THE Simulator SHALL 向 Wrapper 推送包含完整初始战场信息的 State 事件
3. IF 初始化配置中包含不存在的卡牌 ID 或遗物 ID，THEN THE Simulator SHALL 返回包含具体错误原因的错误响应，并拒绝创建 Battle

---

### 需求 2：回合制战斗流程

**用户故事：** 作为 Wrapper，我希望模拟器能够按照 STS2 的回合制规则推进战斗，以便 Agent 在真实的游戏规则下进行训练。

#### 可复用子流程

以下子流程被多个阶段共享调用：

- **[抓牌流程](n张)**：循环n次，每次判断抓牌堆是否有牌：有则抓一张到手牌（手牌已满则入弃牌堆）；无则将弃牌堆洗入抓牌堆后重试；弃牌堆也为空则终止本次抓牌。
- **[伤害结算](来源, 目标, 数值)**：应用力量/虚弱修正 → 应用脆弱修正 → Block先抵消，剩余扣HP → 触发受伤后效果（遗物/Buff）→ 立即执行[死亡检查](目标)。
- **[施加状态](目标, 状态类型, 层数)**：将状态叠加到目标状态列表，推送State。
- **[Buff/Debuff减层]**：遍历所有单位状态列表，有持续时间的减1层，归零则移除；若减层过程中产生HP变化（如中毒），每个单位处理完后立即执行[死亡检查]。
- **[死亡检查](目标)**：若目标为Enemy且HP≤0，标记为死亡并推送State；若所有Enemy均已死亡则触发战斗胜利并中断当前流程；若目标为Player且HP≤0则触发战斗失败并中断当前流程。[伤害结算]返回结果标志，调用方据此决定是否继续后续流程。

#### 战斗主循环

**阶段1：初始化**
- 构建抓牌堆、遗物、药水、Player、Enemy列表
- 触发"战斗开始"事件（遗物/Buff）
- 为每个Enemy设置初始Intent

**阶段2：主控回合开始**
- 清除Player Block
- 重置Player能量至上限
- 触发"回合开始"事件（遗物/Buff）
- 调用[抓牌流程](5张)

**阶段3：主控行动（循环等待Wrapper指令）**
每次收到指令：
- 触发"行动前"事件
- 执行指令效果（出牌/使用药水），调用[伤害结算] / [施加状态]等子流程
- 触发"行动后"事件
- 推送State
- 直到收到"结束回合"指令退出循环

**阶段4：主控回合结束**
- 触发"回合结束"事件（遗物/Buff）
- 调用[Buff/Debuff减层]
- 弃置手牌到弃牌堆

**阶段5：敌人行动**
- 触发"敌人阶段开始"事件
- 逐个Enemy（跳过已死亡）：执行当前Intent，调用[伤害结算] / [施加状态]等子流程；每个Enemy行动后立即执行[死亡检查]；更新Intent到下一个
- 触发"敌人阶段结束"事件
- 调用[Buff/Debuff减层]

**循环**：回到阶段2，直到战斗结束。

---

### 需求 3：卡牌打出与效果执行

**用户故事：** 作为 Wrapper，我希望能够指定打出某张手牌并选择目标，以便 Agent 执行战斗动作。

#### 验收标准

1. WHEN Wrapper 发送打牌指令（包含手牌索引和目标索引），THE Simulator SHALL 验证该卡牌是否可打出（能量足够、目标合法）
2. WHEN 卡牌验证通过，THE Simulator SHALL 扣除对应能量、执行卡牌效果、将卡牌移入弃牌堆，并推送更新后的 State 事件
3. IF 卡牌需要目标但 Wrapper 未提供目标索引，THEN THE Simulator SHALL 返回错误响应，不执行该卡牌
4. IF Wrapper 指定的目标索引对应已死亡的 Enemy，THEN THE Simulator SHALL 返回错误响应，不执行该卡牌
5. IF Wrapper 发送打牌指令时 Player 能量不足，THEN THE Simulator SHALL 返回错误响应，不执行该卡牌
6. WHEN 卡牌效果为造成伤害，THE Simulator SHALL 先用目标的 Block 抵消伤害，Block 不足时扣除剩余伤害对应的生命值
7. WHEN 打出攻击类卡牌（attack），THE Simulator SHALL 对单个目标造成指定数值的伤害
8. WHEN 打出防御类卡牌（defend），THE Simulator SHALL 为 Player 增加指定数值的 Block
9. WHEN 打出抓牌类卡牌（draw），THE Simulator SHALL 立即从牌堆抽取指定数量的卡牌到手牌
10. WHEN 打出施加 Buff/Debuff 类卡牌，THE Simulator SHALL 将对应状态叠加到指定目标单位上
11. WHEN 打出 AOE 类卡牌，THE Simulator SHALL 对所有存活 Enemy 各造成指定数值的伤害
12. WHEN 打出连击（multi-hit）类卡牌，THE Simulator SHALL 对目标依次造成多次独立伤害，每次伤害均独立触发 Block 抵消和 Vulnerable 计算
13. WHEN 打出费用大于等于 2 的高费卡牌，THE Simulator SHALL 执行比同类低费卡牌效果更强的对应效果

---

### 需求 4：Buff / Debuff 状态系统

**用户故事：** 作为 Wrapper，我希望模拟器能够正确处理增益和减益状态，以便 Agent 学习状态效果的策略价值。

#### 验收标准

1. THE Simulator SHALL 支持以下核心 Buff/Debuff：力量（Strength）、敏捷（Dexterity）、脆弱（Vulnerable）、虚弱（Weak）
2. WHEN 卡牌或 Enemy 行动施加 Buff/Debuff，THE Simulator SHALL 将其叠加到目标单位的状态列表，并在 State 中体现
3. WHEN 回合结束时，THE Simulator SHALL 对所有具有持续时间的 Buff/Debuff 减少 1 层，层数归零时移除该状态
4. WHEN 单位拥有力量（Strength）状态时打出攻击卡，THE Simulator SHALL 将该次每次攻击伤害增加等于力量层数的数值
5. WHEN 单位拥有敏捷（Dexterity）状态时获得 Block，THE Simulator SHALL 将该次获得的 Block 数值增加等于敏捷层数的数值
6. WHEN 处于脆弱（Vulnerable）状态的单位受到攻击伤害，THE Simulator SHALL 将该次伤害乘以 1.5 后取整
7. WHEN 处于虚弱（Weak）状态的单位打出攻击卡，THE Simulator SHALL 将该次伤害乘以 0.75 后取整

---

### 需求 5：敌人行为系统

**用户故事：** 作为 Wrapper，我希望模拟器能够模拟敌人的行为模式，以便 Agent 学习应对不同敌人的策略。

#### 验收标准

1. THE Simulator SHALL 为每个 Enemy 定义一组具名行动（Move），每个 Move 包含行动名称和效果列表，效果列表采用与卡牌相同的数据驱动格式。
2. THE Simulator SHALL 支持两种行动选择模式：
   - `sequential_loop`：按固定顺序循环执行 Move 列表，完全数据驱动，无需代码；
   - `fn`：注入 Python 选择函数，函数签名为 `(enemy, ctx: BattleContext, turn: int) -> str`，返回本回合执行的 Move 名称，用于表达条件分支逻辑。
3. THE Simulator SHALL 内置的 3 种敌人全部采用 `sequential_loop` 模式，行动序列参照 STS2 真实敌人设计，完全通过数据配置，无需注入函数。
4. WHEN Enemy 回合执行时，THE Simulator SHALL 根据当前选择模式确定本回合 Move，执行其效果列表，调用 [伤害结算] / [施加状态] 等子流程。
5. WHEN Enemy 行动执行完毕，THE Simulator SHALL 更新该 Enemy 的下一回合 Intent 并在 State 中体现，Intent 包含行动类型和数值（如攻击伤害值）。
6. IF Enemy 生命值降至 0，THEN THE Simulator SHALL 将该 Enemy 标记为死亡，后续回合跳过其行动，且不再作为合法攻击目标。
7. THE Simulator SHALL 支持通过资源注册接口注册自定义敌人定义，注册时可指定 `sequential_loop` 模式的行动列表或 `fn` 模式的选择函数。

---

### 需求 6：静态资源数据

**用户故事：** 作为开发者，我希望模拟器内置一批静态卡牌、遗物和敌人数据，以便快速搭建训练环境而无需外部数据源。

#### 验收标准

1. THE Simulator SHALL 内置不少于 15 张卡牌的静态数据，覆盖以下全部 7 种机制类型：攻击（单体伤害）、防御（获得 Block）、抓牌（从牌堆抽牌）、施加 Buff/Debuff、AOE（对所有敌人造成伤害）、连击（多次打击）、高费牌（费用大于等于 2）
2. THE Simulator SHALL 内置不少于 5 个遗物的静态数据，覆盖多种触发时机类型，包括但不限于：回合开始触发（turn_start）、受到伤害触发（on_damage_taken）、打出卡牌触发（on_card_played）
3. THE Simulator SHALL 内置不少于 3 种敌人的静态数据，每种敌人参照 STS2 真实敌人行为设计，具有完整的固定循环行动序列定义
4. THE Simulator SHALL 以结构化 Python 数据（如 dataclass 或 dict）存储静态资源，支持通过唯一 ID 查询
5. WHEN 查询不存在的静态资源 ID，THE Simulator SHALL 抛出明确的 KeyError 或返回 None，不产生静默错误
6. THE Simulator SHALL 采用混合资源配置方案：简单效果通过结构化数据描述（如 `{"type": "deal_damage", "value": 6, "target": "single"}`），复杂效果支持注入 Python 函数；引擎优先检查函数注入，无函数则走数据解析路径。
7. THE Simulator SHALL 内置支持以下基础效果类型的数据驱动解析：`deal_damage`（单体伤害）、`gain_block`（获得格挡）、`draw_cards`（抓牌）、`apply_buff`（施加状态）、`deal_damage_all`（AOE伤害）、`deal_damage_multi`（连击伤害）、`gain_energy`（获得能量）。
8. THE Simulator SHALL 提供资源注册接口，允许外部代码在初始化前注册自定义卡牌、遗物、药水、敌人、状态定义；注册时可传入 Python 函数作为效果实现，也可使用纯数据描述；注册后可通过唯一 ID 在战斗配置中引用。
9. THE Simulator SHALL 将内置静态资源与运行时注册资源统一存储在同一资源注册表（Registry）中，对外提供一致的查询接口，支持通过 JSON 文件或 Python dict 批量加载。
10. WHEN 查询不存在的静态资源 ID，THE Simulator SHALL 抛出明确的 KeyError 或返回 None，不产生静默错误。

---

### 需求 7：Bridge 通信模块

**用户故事：** 作为外部消费方（RL 框架或其他工具），我希望通过标准化接口与模拟器通信，以便将模拟器集成到训练流程中。

#### 架构说明

本项目采用以下通信架构：

```
Simulator Core
     ↕ 进程内函数调用
   Bridge（本项目子模块）
     ↕ ZeroMQ ipc://（同机器高速通信）
外部消费方（RL 框架，不在本项目范围）
```

未来切换游戏 Mod 模式时，Bridge 作为独立进程部署，游戏 Mod 通过 HTTP 向 Bridge 推送状态，Bridge 对外接口（ZeroMQ 侧）保持不变，RL 框架无需修改。

#### 验收标准

1. THE Simulator SHALL 提供进程内同步 Python API（`Simulator` 类），供 Bridge 直接函数调用，不经过网络。
2. THE Bridge SHALL 作为本项目子模块（`bridge/` 目录），与 Simulator Core 运行于同一进程，通过函数调用获取状态和发送指令。
3. THE Bridge SHALL 通过 ZeroMQ REQ-REP 模式对外暴露接口，使用 `ipc://` 协议（同机器 Unix Socket），供外部消费方连接。
4. WHEN Simulator 内部状态发生变化，THE Bridge SHALL 将序列化后的 state dict 通过 ZeroMQ 推送给外部消费方，并等待回复的 action 指令。
5. WHEN Bridge 收到外部消费方的 action 指令，THE Bridge SHALL 解析指令并调用 Simulator 对应的 API 方法执行。
6. THE Bridge SHALL 将所有对外暴露的 State 序列化为 JSON 格式，字段结构固定且有文档说明。
7. THE Bridge SHALL 为所有公开接口方法提供类型注解（Type Hints），入参和返回值均有明确类型定义。
8. IF Simulator 在 Battle 已结束后收到动作指令，THEN THE Bridge SHALL 返回包含"战斗已结束"说明的错误响应，不修改任何状态。
9. THE Simulator Core SHALL 保证每个 Battle 实例完全独立、无全局共享状态，以支持外层多进程并行运行多个实例。
10. THE Bridge SHALL 的回调函数接口采用标准同步函数签名 `(state: dict) -> None`，Simulator 本身不依赖异步运行时。
11. RL 框架的实现不在本项目范围内，本项目只保证 Bridge 的 ZeroMQ 接口协议文档完整，供外部消费方对接。

---

### 需求 8：状态观测与合法动作查询

**用户故事：** 作为 Wrapper，我希望能够查询当前合法动作列表，以便 Agent 只在合法动作空间内进行决策。

#### 验收标准

1. WHEN Wrapper 调用合法动作查询接口，THE Simulator SHALL 返回当前回合所有可执行动作的列表，包括可打出的手牌（含目标）、可使用的药水（含目标）和结束回合
2. THE Simulator SHALL 在返回的合法动作列表中，为每个打牌动作标注对应的手牌索引、卡牌 ID 和目标索引（无目标卡牌目标索引为 -1）
3. WHILE Player 能量为 0 且手牌中无零费卡牌，THE Simulator SHALL 在合法动作列表中仅包含结束回合动作和可用药水动作
4. THE Simulator SHALL 保证：对合法动作列表中的任意动作执行打牌操作，均不会返回能量不足或目标非法的错误响应

---

### 需求 9：药水系统

**用户故事：** 作为 Wrapper，我希望 Agent 能够在战斗中使用药水，以便在关键时刻获得即时效果。

#### 验收标准

1. THE Simulator SHALL 支持以下 4 种药水类型：护甲药水（Block Potion）、攻击药水（Attack Potion）、抓牌药水（Card Draw Potion）、能量药水（Energy Potion）
2. WHEN Player 使用护甲药水，THE Simulator SHALL 立即为 Player 增加指定数值的 Block
3. WHEN Player 使用攻击药水并指定目标，THE Simulator SHALL 对目标 Enemy 造成指定数值的伤害
4. WHEN Player 使用抓牌药水，THE Simulator SHALL 立即从牌堆抽取指定数量的卡牌到手牌
5. WHEN Player 使用能量药水，THE Simulator SHALL 立即为 Player 增加指定数值的能量
6. WHEN 药水被使用，THE Simulator SHALL 将该药水从 Player 的药水槽中移除，并推送更新后的 State 事件
7. WHEN Wrapper 发送使用药水指令（包含药水槽位索引和目标索引），THE Simulator SHALL 验证该槽位存在药水且目标合法
8. IF 攻击药水指定的目标索引对应已死亡的 Enemy，THEN THE Simulator SHALL 返回错误响应，不消耗该药水
9. IF Wrapper 指定的药水槽位索引不存在药水，THEN THE Simulator SHALL 返回错误响应，不执行任何效果
10. THE Simulator SHALL 在 State 中暴露 Player 当前持有的药水列表，包含每个槽位的药水类型和槽位索引

---
