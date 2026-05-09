/**
 * Apply Chinese translations to DH processed pack data.
 * Translation source: RidRisR/DaggerHeart-CharacterSheet (simplified CN)
 * Translations are embedded in this script — no external dependencies required.
 */

import { readFileSync, writeFileSync, existsSync } from "fs";
import { join, resolve } from "path";

const packDir = resolve("backend/app/systems/daggerheart/default_packs/processed");

// ── Class translations ──
const CLASS_CN = {
  "bard": "吟游诗人", "druid": "德鲁伊", "guardian": "守护者",
  "ranger": "游侠", "rogue": "游荡者", "seraph": "炽天使",
  "sorcerer": "术士", "warrior": "战士", "wizard": "法师",
};

// ── Ancestry translations ──
const ANCESTRY_CN = {
  "clank": "铁偶", "dwarf": "矮人", "elf": "精灵", "faerie": "妖精",
  "faun": "牧神", "firbolg": "费尔伯格", "fungril": "真菌族",
  "galapa": "龟人", "giant": "巨人", "goblin": "地精",
  "halfling": "半身人", "human": "人类", "katari": "猫人",
  "orc": "兽人", "ribbet": "蛙人", "simiah": "猴人",
  "drakona": "龙裔", "infernis": "炎魔",
};

// ── Community translations ──
const COMMUNITY_CN = {
  "highborne": "高贵之人", "loreborne": "博学之人", "orderborne": "秩序之人",
  "ridgeborne": "山脊之人", "seaborne": "海洋之人", "shadowborne": "暗影之人",
  "wanderborne": "流浪之人", "wildborne": "荒野之人",
  "underborne": "地底之人", "slyborne": "诡道之人",
};

// ── Subclass translations ──
const SUBCLASS_CN = {
  "school-of-war": "战争学派", "school-of-knowledge": "知识学派",
  "syndicate": "辛迪加", "nightwalker": "夜行者",
  "primal-origin": "原始起源", "elemental-origin": "元素起源",
  "divine-wielder": "神圣执行者", "winged-sentinel": "翼卫",
  "call-of-the-brave": "勇者的呼唤", "call-of-the-slayer": "杀戮者的呼唤",
  "vengeance": "复仇", "stalwart": "坚毅",
  "beastbound": "兽缚者", "wayfinder": "寻路者",
  "warden-of-the-elements": "元素守望者", "warden-of-renewal": "新生守望者",
  "wordsmith": "咏言师", "troubadour": "游吟诗人",
};

// ── Domain translations ──
const DOMAIN_CN = {
  "sage": "贤者", "valor": "勇气", "arcana": "奥术",
  "blade": "利刃", "codex": "典籍", "splendor": "辉耀",
  "midnight": "午夜", "grace": "优雅", "bone": "骸骨",
};

// ── Card type translations ──
const CARD_TYPE_CN = {
  "ability": "能力", "spell": "法术", "grimoire": "魔典",
};

// ── Weapon translations (EN name -> CN name) ──
// Based on RidRisR/DaggerHeart-CharacterSheet + FVTT variant spellings
const WEAPON_CN = {
  // T1 Physical (both spelling variants)
  "Broadsword": "阔剑", "Longsword": "长剑",
  "Battle Axe": "战斧", "Battleaxe": "战斧",
  "Greatsword": "巨剑", "Mace": "钉头锤", "Warhammer": "战锤",
  "Dagger": "匕首", "Cudgel": "短棍", "Knife": "短刀",
  "Rapier": "刺剑", "Halberd": "戟", "Spear": "长矛",
  "Shortbow": "短弓", "Crossbow": "弩", "Longbow": "长弓",
  "Cutlass": "短弯刀",
  // T1 Magic
  "Arcane Gauntlets": "奥术护手", "Hallowed Axe": "圣斧",
  "Glowing Ring": "发光戒指", "Glowing Rings": "发光戒指",
  "Handheld Rune": "手持符文", "Hand Runes": "手持符文",
  "Returning Blade": "回力剑",
  "Short Staff": "短杖", "Shortstaff": "短杖",
  "Two-Handed Staff": "双手法杖", "Dualstaff": "双手法杖",
  "Scepter": "权杖", "Wand": "魔杖",
  "Grand Staff": "巨杖", "Greatstaff": "巨杖",
  "Quarterstaff": "短棍",
  // T1 Secondary
  "Short Sword": "短剑", "Shortsword": "短剑",
  "Round Shield": "圆盾", "Tower Shield": "塔盾",
  "Small Dagger": "小匕首", "Whip": "鞭子",
  "Grappling Hook": "抓钩", "Grappler": "抓钩",
  "Hand Crossbow": "手弩",
  // Wheelchair (accessibility)
  "Light-Frame Wheelchair": "轻型轮椅", "Heavy-Frame Wheelchair": "重型轮椅",
  "Arcane-Frame Wheelchair": "奥术轮椅",
  // T2 improved base (both spelling variants)
  "Improved Broadsword": "改良阔剑", "Improved Longsword": "改良长剑",
  "Improved Battle Axe": "改良战斧", "Improved Battleaxe": "改良战斧",
  "Improved Greatsword": "改良巨剑",
  "Improved Mace": "改良钉头锤", "Improved Warhammer": "改良战锤",
  "Improved Dagger": "改良匕首", "Improved Cudgel": "改良短棍",
  "Improved Knife": "改良短刀", "Improved Rapier": "改良刺剑",
  "Improved Halberd": "改良戟", "Improved Spear": "改良长矛",
  "Improved Shortbow": "改良短弓", "Improved Crossbow": "改良弩",
  "Improved Longbow": "改良长弓", "Improved Cutlass": "改良短弯刀",
  "Improved Arcane Gauntlets": "改良奥术护手", "Improved Hallowed Axe": "改良圣斧",
  "Improved Glowing Ring": "改良发光戒指", "Improved Glowing Rings": "改良发光戒指",
  "Improved Handheld Rune": "改良手持符文", "Improved Hand Runes": "改良手持符文",
  "Improved Returning Blade": "改良回力剑",
  "Improved Short Staff": "改良短杖", "Improved Shortstaff": "改良短杖",
  "Improved Two-Handed Staff": "改良双手法杖", "Improved Dualstaff": "改良双手法杖",
  "Improved Scepter": "改良权杖", "Improved Wand": "改良魔杖",
  "Improved Grand Staff": "改良巨杖", "Improved Greatstaff": "改良巨杖",
  "Improved Quarterstaff": "改良短棍",
  "Improved Short Sword": "改良短剑", "Improved Shortsword": "改良短剑",
  "Improved Round Shield": "改良圆盾", "Improved Tower Shield": "改良塔盾",
  "Improved Small Dagger": "改良小匕首", "Improved Whip": "改良鞭子",
  "Improved Grappling Hook": "改良抓钩", "Improved Grappler": "改良抓钩",
  "Improved Hand Crossbow": "改良手弩",
  "Improved Light-Frame Wheelchair": "改良轻型轮椅",
  "Improved Heavy-Frame Wheelchair": "改良重型轮椅",
  "Improved Arcane-Frame Wheelchair": "改良奥术轮椅",
  // T2 unique physical
  "Gilded Scimitar": "鎏金弯刀", "Gilded Falchion": "鎏金弯刀",
  "Punch Blades": "拳刃", "Knuckle Blades": "拳刃",
  "Ulrok Broadsword": "乌洛克阔剑", "Urok Broadsword": "乌洛克阔剑",
  "Bladewhip": "刃鞭", "Bladed Whip": "刃鞭",
  "Steel-Forged Halberd": "钢铸戟", "Steelforged Halberd": "钢铸戟",
  "War Sickle": "战镰", "War Scythe": "战镰",
  "Blunderbuss": "火铳", "Greatbow": "巨弓",
  "Finestring Bow": "细弦弓", "Finehair Bow": "细弦弓",
  // T2 unique magic
  "Blade of the Self": "自我之刃", "Ego Blade": "自我之刃",
  "Spellsword": "施法剑", "Casting Sword": "施法剑",
  "Devouring Dagger": "吞噬匕首", "Hammer of Exota": "异界之锤",
  "Yutari Bloodbow": "尤塔里血弓", "Elder Bow": "长者之弓",
  "Scepter of Ilias": "伊利亚斯的权杖", "Scepter of Elias": "伊利亚斯的权杖",
  "Wand of Befuddlement": "迷惑魔杖", "Wand of Enthrallment": "迷惑魔杖",
  "Keeper's Staff": "看守者之杖",
  // T2 secondary unique
  "Spiked Shield": "尖刺盾牌", "Parrying Dagger": "格挡匕首",
  "Returning Axe": "回力斧",
  // T3 improved base (both spelling variants)
  "Advanced Broadsword": "高级阔剑", "Advanced Longsword": "高级长剑",
  "Advanced Battle Axe": "高级战斧", "Advanced Battleaxe": "高级战斧",
  "Advanced Greatsword": "高级巨剑",
  "Advanced Mace": "高级钉头锤", "Advanced Warhammer": "高级战锤",
  "Advanced Dagger": "高级匕首", "Advanced Cudgel": "高级短棍",
  "Advanced Knife": "高级短刀", "Advanced Rapier": "高级刺剑",
  "Advanced Halberd": "高级戟", "Advanced Spear": "高级长矛",
  "Advanced Shortbow": "高级短弓", "Advanced Crossbow": "高级弩",
  "Advanced Longbow": "高级长弓", "Advanced Cutlass": "高级短弯刀",
  "Advanced Arcane Gauntlets": "高级奥术护手", "Advanced Hallowed Axe": "高级圣斧",
  "Advanced Glowing Ring": "高级发光戒指", "Advanced Glowing Rings": "高级发光戒指",
  "Advanced Handheld Rune": "高级手持符文", "Advanced Hand Runes": "高级手持符文",
  "Advanced Returning Blade": "高级回力剑",
  "Advanced Short Staff": "高级短杖", "Advanced Shortstaff": "高级短杖",
  "Advanced Two-Handed Staff": "高级双手法杖", "Advanced Dualstaff": "高级双手法杖",
  "Advanced Scepter": "高级权杖", "Advanced Wand": "高级魔杖",
  "Advanced Grand Staff": "高级巨杖", "Advanced Greatstaff": "高级巨杖",
  "Advanced Quarterstaff": "高级短棍",
  "Advanced Short Sword": "高级短剑", "Advanced Shortsword": "高级短剑",
  "Advanced Round Shield": "高级圆盾", "Advanced Tower Shield": "高级塔盾",
  "Advanced Small Dagger": "高级小匕首", "Advanced Whip": "高级鞭子",
  "Advanced Grappling Hook": "高级抓钩", "Advanced Grappler": "高级抓钩",
  "Advanced Hand Crossbow": "高级手弩",
  "Advanced Light-Frame Wheelchair": "高级轻型轮椅",
  "Advanced Heavy-Frame Wheelchair": "高级重型轮椅",
  "Advanced Arcane-Frame Wheelchair": "高级奥术轮椅",
  // T3 unique physical
  "Morpho Blade": "闪蝶之刃", "Flickerfly Blade": "闪蝶之刃",
  "Blade of Valor": "勇气之剑", "Bravesword": "勇气之剑",
  "Hammer of Wrath": "愤怒之锤",
  "Labrys Axe": "拉布里斯斧", "Sledge Axe": "拉布里斯斧",
  "Meridian Knife": "经络短刀", "Meridian Cutlass": "经络短弯刀",
  "Concealed Saber": "伸缩军刀", "Retractable Saber": "伸缩军刀",
  "Double Flail": "双连枷",
  "Talonclaw": "利爪之刃", "Talon Blades": "利爪之刃",
  "Blackpowder Revolver": "黑火药左轮", "Black Powder Revolver": "黑火药左轮",
  "Barbed Bow": "尖刺弓", "Spiked Bow": "尖刺弓",
  // T3 unique magic
  "Luck Axe": "运气之斧", "Axe of Fortunis": "运气之斧",
  "Blessed Dagger": "祝福匕首", "Blessed Anlace": "祝福匕首",
  "Ghostblade": "鬼魂之刃",
  "Rune of Destruction": "毁灭符文", "Runes of Ruination": "毁灭符文",
  "Vidagast's Pendant": "维多加斯特的吊坠", "Widogast Pendant": "维多加斯特的吊坠",
  "Gilded Bow": "鎏金弓",
  "Flame Staff": "火焰杖", "Firestaff": "火焰杖",
  "Mage Orb": "法师球",
  "Ilmari's Rifle": "伊尔玛里的步枪",
  // T3 secondary unique
  "Buckler": "小盾", "Braveshield": "勇气之盾",
  "Power Gauntlet": "强力拳套", "Powered Gauntlet": "强力拳套",
  "Slingshot": "弹弓", "Hand Sling": "弹弓",
  // T4 base (both spelling variants)
  "Legendary Broadsword": "传奇阔剑", "Legendary Longsword": "传奇长剑",
  "Legendary Battle Axe": "传奇战斧", "Legendary Battleaxe": "传奇战斧",
  "Legendary Greatsword": "传奇巨剑",
  "Legendary Mace": "传奇钉头锤", "Legendary Warhammer": "传奇战锤",
  "Legendary Dagger": "传奇匕首", "Legendary Cudgel": "传奇短棍",
  "Legendary Knife": "传奇短刀", "Legendary Rapier": "传奇刺剑",
  "Legendary Halberd": "传奇戟", "Legendary Spear": "传奇长矛",
  "Legendary Shortbow": "传奇短弓", "Legendary Crossbow": "传奇弩",
  "Legendary Longbow": "传奇长弓", "Legendary Cutlass": "传奇短弯刀",
  "Legendary Arcane Gauntlets": "传奇奥术护手", "Legendary Hallowed Axe": "传奇圣斧",
  "Legendary Glowing Ring": "传奇发光戒指", "Legendary Glowing Rings": "传奇发光戒指",
  "Legendary Handheld Rune": "传奇手持符文", "Legendary Hand Runes": "传奇手持符文",
  "Legendary Returning Blade": "传奇回力剑",
  "Legendary Short Staff": "传奇短杖", "Legendary Shortstaff": "传奇短杖",
  "Legendary Two-Handed Staff": "传奇双手法杖", "Legendary Dualstaff": "传奇双手法杖",
  "Legendary Scepter": "传奇权杖", "Legendary Wand": "传奇魔杖",
  "Legendary Grand Staff": "传奇巨杖", "Legendary Greatstaff": "传奇巨杖",
  "Legendary Quarterstaff": "传奇短棍",
  "Legendary Short Sword": "传奇短剑", "Legendary Shortsword": "传奇短剑",
  "Legendary Round Shield": "传奇圆盾", "Legendary Tower Shield": "传奇塔盾",
  "Legendary Small Dagger": "传奇小匕首", "Legendary Whip": "传奇鞭子",
  "Legendary Grappling Hook": "传奇抓钩", "Legendary Grappler": "传奇抓钩",
  "Legendary Hand Crossbow": "传奇手弩",
  "Legendary Light-Frame Wheelchair": "传奇轻型轮椅",
  "Legendary Heavy-Frame Wheelchair": "传奇重型轮椅",
  "Legendary Arcane-Frame Wheelchair": "传奇奥术轮椅",
  // T4 unique physical
  "Twin Blade Sword": "双刃剑", "Dual-Ended Sword": "双刃剑",
  "Impact Gauntlets": "冲击拳套", "Impact Gauntlet": "冲击拳套",
  "Greataxe": "巨斧",
  "Curved Dagger": "弧形匕首",
  "Extended Polearm": "延伸长柄武器",
  "Pendulum Ropeblade": "摆动绳刃", "Swinging Ropeblade": "摆动绳刃",
  "Ricochet Axe": "弹跳斧", "Ricochet Axes": "弹跳斧",
  "Antali Bow": "安塔利弓", "Aantari Bow": "安塔利弓",
  "Hand Cannon": "手炮",
  // T4 unique magic
  "Lightflame Sword": "光焰剑", "Sword of Light & Flame": "光焰剑",
  "Siphoning Gauntlets": "虹吸拳套",
  "Midas Scythe": "迈达斯镰刀",
  "Floating Shards": "漂浮碎刃", "Floating Bladeshards": "漂浮碎刃",
  "Thistlebow": "蓟弓", "Bloodstaff": "血杖",
  "Staff of Ethek": "埃塞克之杖", "Wand of Essek": "埃塞克之杖",
  "Magebane Revolver": "魔战士左轮", "Magus Revolver": "魔战士左轮",
  "Fusion Gloves": "融合手套",
  // T4 secondary unique
  "Shield of Courage": "勇气之盾",
  "Fistclaw": "拳爪", "Knuckle Claws": "拳爪",
  "Lodestone Shard": "引物碎片", "Primer Shard": "引物碎片",
};

// ── Armor translations (EN name -> CN name) ──
const ARMOR_CN = {
  // T1
  "Gambeson Armor": "填充布甲", "Leather Armor": "皮甲",
  "Chainmail Armor": "链甲", "Full Plate Armor": "全板甲",
  "Bare Bones": "赤膊",
  // T2
  "Improved Gambeson Armor": "改良填充布甲", "Improved Leather Armor": "改良皮甲",
  "Improved Chainmail Armor": "改良链甲", "Improved Full Plate Armor": "改良全板甲",
  "Elundrian Chain Armor": "埃伦德里安链甲", "Harrowbone Armor": "掠骸护甲",
  "Irontree Breastplate Armor": "铁木胸甲", "Runetan Floating Armor": "符文浮甲",
  "Tyris Soft Armor": "泰瑞斯软甲", "Rosewild Armor": "蔷薇野甲",
  // T3
  "Advanced Gambeson Armor": "高级填充布甲", "Advanced Leather Armor": "高级皮甲",
  "Advanced Chainmail Armor": "高级链甲", "Advanced Full Plate Armor": "高级全板甲",
  "Bellamoi Fine Armor": "贝拉莫伊精致护甲", "Dragonscale Armor": "龙鳞护甲",
  "Spiked Plate Armor": "尖刺护甲", "Bladefare Armor": "剑刃护甲",
  "Monett's Cloak": "莫奈特的斗篷", "Runes of Fortification": "强化符文",
  // T4
  "Legendary Gambeson Armor": "传奇填充布甲", "Legendary Leather Armor": "传奇皮甲",
  "Legendary Chainmail Armor": "传奇链甲", "Legendary Full Plate Armor": "传奇全板甲",
  "Dunamis Silkchain": "威能丝甲", "Channeling Armor": "引导护甲",
  "Emberwoven Armor": "织烬护甲", "Full Fortified Armor": "全面强化护甲",
  "Veritas Opal Armor": "诚实蛋白石护甲", "Savior Chainmail": "救世主链甲",
};

// ── Loot translations ──
const LOOT_CN = {
  "Arcane Cloak": "奥术斗篷", "Charm Relic": "魅力圣物",
  "Flickerfly Pendant": "萤火虫吊坠", "Gecko Gloves": "壁虎手套",
  "Gem of Precision": "精准宝石", "Glider": "滑翔翼",
  "Hopekeeper Locket": "希望守护坠盒",
  "Minor Stamina Potion Recipe": "初级耐力药剂配方",
  "Mythic Dust Recipe": "神话粉尘配方", "Vial of Darksmoke Recipe": "暗烟小瓶配方",
  "Minor Health Potion Recipe": "初级生命药剂配方",
  "Shard of Memory": "记忆碎片", "Valorstone": "勇气石", "Woven Net": "编织网",
  "Paragon's Chain": "典范之链", "Paragon\u2019s Chain": "典范之链",
  "Stride Relic": "步幅圣物",
  "Corrector Sprite": "矫正精灵", "Manacles": "镣铐",
  "Dual Flask": "双层瓶", "Piercing Arrows": "穿透箭",
  "Infinite Bag": "无限之袋", "Lorekeeper": "知识守护者",
  "Ring of Silence": "静默之戒", "Speaking Orbs": "通讯球",
  "Alistair's Torch": "阿利斯泰尔的火炬", "Alistair\u2019s Torch": "阿利斯泰尔的火炬",
  "Arcane Prism": "奥术棱镜",
  "Lakestrider Boots": "踏湖之靴", "Glamour Stone": "幻影石",
  "Elusive Amulet": "闪避护符", "Premium Bedroll": "高级铺盖",
  "Phoenix Feather": "凤凰之羽", "Control Relic": "控制圣物",
  "Honing Relic": "磨砺圣物", "Gem of Insight": "洞察宝石",
  "Companion Case": "同伴匣", "Fire Jar": "火焰罐",
  "Ring of Resistance": "抗性之戒", "Box of Many Goods": "百宝箱",
  "Airblade Charm": "风刃挂饰", "Portal Seed": "传送种子",
  "Skeleton Key": "万能钥匙", "Belt of Unity": "团结之带",
  "Charging Quiver": "充能箭袋", "Gem of Audacity": "大胆宝石",
  "Ring of Unbreakable Resolve": "不屈意志之戒", "Clay Companion": "黏土同伴",
  "Bolster Relic": "强化圣物", "Suspended Rod": "悬浮法杖",
  "Bloodstone": "血石", "Empty Chest": "空宝箱",
  "Gem of Might": "力量宝石", "Calming Pendant": "安抚吊坠",
  "Gem of Sagacity": "睿智宝石", "Piper Whistle": "笛手口哨",
  "Bag of Ficklesand": "流沙之袋", "Attune Relic": "调谐圣物",
  "Enlighten Relic": "启迪圣物", "Greatstone": "巨石",
  "Homing Compasses": "追踪罗盘", "Gem of Alacrity": "敏捷宝石",
};

// ── Consumable translations ──
const CONSUMABLE_CN = {
  "Health Potion": "生命药剂", "Minor Health Potion": "初级生命药剂",
  "Major Health Potion": "高级生命药剂",
  "Bolster Potion": "强化药剂", "Major Bolster Potion": "高级强化药剂",
  "Charm Potion": "魅力药剂", "Major Charm Potion": "高级魅力药剂",
  "Control Potion": "控制药剂", "Major Control Potion": "高级控制药剂",
  "Attune Potion": "调谐药剂", "Major Attune Potion": "高级调谐药剂",
  "Enlighten Potion": "启迪药剂", "Major Enlighten Potion": "高级启迪药剂",
  "Stride Potion": "步幅药剂", "Major Stride Potion": "高级步幅药剂",
  "Grindletooth Venom": "磨牙毒液", "Improved Grindletooth Venom": "改良磨牙毒液",
  "Major Arcane Shard": "高级奥术碎片", "Minor Arcane Shard": "初级奥术碎片",
  "Improved Arcane Shard": "改良奥术碎片", "Unstable Arcane Shard": "不稳定奥术碎片",
  "Featherbone": "羽骨", "Hopehold Flare": "希望之光信号弹",
  "Sweet Moss": "甜苔藓", "Shrinking Potion": "缩小药剂",
  "Stamina Potion": "耐力药剂", "Minor Stamina Potion": "初级耐力药剂",
  "Major Stamina Potion": "高级耐力药剂",
  "Smokebomb": "烟雾弹", "Sparkdust": "火花粉尘",
  "Firevial": "火焰小瓶", "Gilded Dust": "鎏金粉尘",
  "Mythic Dust": "神话粉尘", "Growth Potion": "成长药剂",
  "Growing Potion": "成长药剂", "Toxin Elixir": "毒素灵药",
  "Channelstone": "引导石", "Gill Salve": "鳃膏",
  "Vial of Darksmoke": "暗烟小瓶", "Bonding Honey": "联结蜜",
  "Bridge Seed": "桥梁种子", "Mirror of Marigold": "金盏花之镜",
  "Homet's Secret Potion": "霍梅特的秘密药剂", "Homet\u2019s Secret Potion": "霍梅特的秘密药剂",
  "Armor Stitcher": "护甲缝补器",
  "Vial of Moondrip": "月滴小瓶", "Sleeping Sap": "安眠树液",
  "Feast of Xuria": "苏里亚的盛宴", "Jumping Root": "跳跃根",
  "Acidpaste": "酸蚀膏", "Snap Powder": "爆裂粉",
  "Potion of Stability": "稳定药剂", "Blinding Orb": "致盲光球",
  "Dripfang Poison": "滴牙毒液", "Circle of the Void": "虚空之环",
  "Morphing Clay": "变形黏土", "Varik Leaves": "瓦里克树叶",
  "Sun Tree Sap": "太阳树汁", "Wingsprout": "翅芽",
  "Knowledge Stone": "知识之石", "Blood of the Yorgi": "约吉之血",
  "Ogre Musk": "食人魔麝香", "Redthorn Saliva": "红刺唾液",
  "Dragonbloom Tea": "龙花茶", "Death Tea": "死亡之茶",
  "Stardrop": "星滴", "Replication Parchment": "复制羊皮纸",
  "Jar of Lost Voices": "失落之声罐",
};

// ── Beastform translations ──
const BEASTFORM_CN = {
  "Striking Serpent": "突袭毒蛇", "Pouncing Predator": "猛扑捕食者",
  "Terrible Lizard": "可怖蜥种", "Armored Sentry": "甲壳哨兵",
  "Mighty Lizard": "巨型蜥种", "Mighty Strider": "健步行者",
  "Stalking Arachnid": "追猎蜘蛛", "Nimble Grazer": "灵巧食草者",
  "Aquatic Predator": "深洋捕食者", "Aquatic Scout": "深洋斥候",
  "Rampaging Beast": "庞然巨兽",
  "Soaring Raptor": "翔空猛禽", "Great Winged Beast": "翔空巨禽",
  "Hunting Hawk": "翔空猛禽", "Pack Hunter": "群居捕食者",
  "Pack Predator": "群居捕食者", "Agile Scout": "迅捷斥候",
  "Household Friend": "居家伴侣",
  "Charging Bull": "强大野兽", "Powerful Beast": "强大野兽",
  "Lumbering Bear": "传奇野兽", "Legendary Beast": "传奇野兽",
  "Swooping Falcon": "翔空猛禽",
  "Great Ape": "巨型捕食者", "Great Predator": "巨型捕食者",
  "Hulking Brute": "庞然巨兽", "Massive Behemoth": "庞然巨兽",
  "Alpha Predator": "顶级掠食者",
  "Colossal Beast": "庞然巨兽",
  "Ancient Wyrm": "可怖蜥种",
  "Titan Tortoise": "甲壳哨兵",
  "Primal Horror": "原始恐惧",
  "Winged Beast": "翔空巨禽",
  "Mythic Hybrid": "神话混种生物", "Legendary Hybrid": "传奇混种生物",
  "Mythic Aerial Hunter": "神话空猎者", "Mythic Beast": "神话野兽",
  "Epic Aquatic Beast": "史诗海兽",
  "Beastform Transformation": "兽形态变身",
};

// ── Domain Card translations (by slug) ──
// Based on builtin-base.json from RidRisR/DaggerHeart-CharacterSheet
const DOMAIN_CARD_SLUG_CN = {
  // Arcana
  "rune-ward": "符文护符", "unleash-chaos": "释放混沌", "wall-walk": "墙面行走",
  "cinder-grasp": "余烬之握", "floating-eye": "浮游之眼", "counterspell": "法术反制",
  "flight": "飞行奇术", "blink-out": "闪烁现身", "preservation-blast": "护身爆发",
  "chain-lightning": "连锁闪电", "premonition": "预见未来", "rift-walker": "裂隙行者",
  "telekinesis": "心灵遥控", "arcana-touched": "奥术恩泽", "cloaking-blast": "匿踪诡术",
  "arcane-reflection": "奥术反射", "confusing-aura": "惑像灵光", "earthquake": "地动山摇",
  "sensory-projection": "感官投射", "adjust-reality": "调整现实", "falling-sky": "星辰陨落",
  // Blade
  "get-back-up": "卷土重来", "not-good-enough": "还不够好", "whirlwind": "旋风猛袭",
  "a-soldiers-bond": "老兵羁绊", "a-soldier's-bond": "老兵羁绊", "a-soldier\u2019s-bond": "老兵羁绊", "reckless": "鲁莽攻击", "scramble": "快步急闪",
  "versatile-fighter": "多面武者", "deadly-focus": "致命专注", "fortified-armor": "强化护甲",
  "champions-edge": "勇士锐锋", "champion's-edge": "勇士锐锋", "champion\u2019s-edge": "勇士锐锋", "vitality": "蓬勃生命", "battle-hardened": "久经沙场",
  "rage-up": "怒意重击", "blade-touched": "利刃恩泽", "glancing-blow": "斜掠攻势",
  "battle-cry": "战斗咆哮", "frenzy": "狂怒出击", "gore-and-glory": "血与荣耀",
  "reapers-strike": "死亡收割", "reaper's-strike": "死亡收割", "reaper\u2019s-strike": "死亡收割",
  "battle-monster": "战场猛兽", "onslaught": "猛攻强袭",
  // Bone
  "deft-maneuvers": "灵巧机动", "i-see-it-coming": "先见之明", "untouchable": "不可侵犯",
  "ferocity": "凶猛残暴", "strategic-approach": "战术方针", "brace": "警戒防备",
  "tactician": "战术行家", "boost": "高高跃起", "redirect": "借力打力",
  "know-thy-enemy": "知己知彼", "signature-move": "招牌动作", "rapid-riposte": "迅速报复",
  "recovery": "恢复如新", "bone-touched": "骸骨恩泽", "cruel-precision": "残酷精准",
  "breaking-blow": "碎骨打击", "wrangle": "缠斗乱战", "on-the-brink": "生死边缘",
  "splintering-strike": "分裂打击", "deathrun": "死亡奔袭", "swift-step": "闪转腾挪",
  // Codex
  "book-of-ava": "艾娃之书", "book-of-illiat": "伊利亚特之书", "book-of-tyfar": "提法之书",
  "book-of-sitil": "斯泰尔之书", "book-of-vagras": "瓦格拉斯之书", "book-of-korvax": "库瓦斯之书",
  "book-of-norai": "诺莱伊之书", "book-of-exota": "埃索塔之书", "book-of-grynn": "格林之书",
  "manifest-wall": "具现之墙", "teleport": "传送术", "banish": "放逐术",
  "sigil-of-retribution": "惩戒符印", "book-of-homet": "霍梅特之书", "codex-touched": "典籍恩泽",
  "book-of-vyola": "维奥拉之书", "safe-haven": "避风港湾", "book-of-ronin": "罗宁之书",
  "disintegration-wave": "解离波", "book-of-yarrow": "亚罗之书", "transcendent-union": "超凡联结",
  // Grace
  "deft-deceiver": "欺瞒熟手", "enrapture": "心醉神迷", "inspirational-words": "豪言壮语",
  "tell-no-lies": "无可讳言", "troublemaker": "惹是生非", "hypnotic-shimmer": "催眠闪光",
  "invisibility": "无影无踪", "soothing-speech": "宽慰言语", "through-your-eyes": "感官共享",
  "thought-delver": "挖掘思想", "words-of-discord": "挑拨离间", "never-upstaged": "绝不怯场",
  "share-the-burden": "排忧解难", "endless-charisma": "无穷魅力", "grace-touched": "优雅恩泽",
  "astral-projection": "星界投影", "mass-enrapture": "群体心醉神迷", "copycat": "如法炮制",
  "master-of-the-craft": "技艺大师", "encore": "再次上演",
  // Midnight
  "notorious": "恶名昭彰", "pick-and-pull": "妙手空空", "rain-of-blades": "滂沱剑雨",
  "uncanny-disguise": "奇异伪装", "midnight-spirit": "午夜精魂", "shadowbind": "暗影束缚",
  "chokehold": "锁喉勒颈", "veil-of-night": "暗夜帷幕", "stealth-expertise": "潜行专家",
  "glyph-of-nightfall": "夜幕符文", "hush": "沉默不言", "phantom-retreat": "移形换影",
  "dark-whispers": "黑暗低语", "mass-disguise": "群体伪装", "midnight-touched": "午夜恩泽",
  "vanishing-dodge": "无踪影遁", "shadowhunter": "暗影猎手", "spellcharge": "法术充能",
  "night-terror": "夜魇降临", "twilight-toll": "暮光丧钟", "eclipse": "日蚀无光",
  "specter-of-the-dark": "黑暗幽影",
  // Sage
  "gifted-tracker": "追猎才能", "natures-tongue": "自然之语", "nature's-tongue": "自然之语", "nature\u2019s-tongue": "自然之语", "vicious-entangle": "怨毒缠绕",
  "conjure-swarm": "召唤虫群", "natural-familiar": "自然魔宠", "corrosive-projectile": "腐蚀射弹",
  "towering-stalk": "高茎成塔", "death-grip": "死亡卷握", "healing-field": "治疗之域",
  "thorn-skin": "荆棘皮肤", "wild-fortress": "荒野壁垒", "conjured-steeds": "召唤坐骑",
  "forager": "丰收采集", "sage-touched": "贤者恩泽", "wild-surge": "狂野浪涌",
  "forest-sprites": "森林精魂", "rejuvenation-barrier": "回春屏障", "fane-of-the-wilds": "野地神殿",
  "plant-dominion": "植物统御", "force-of-nature": "自然之力",
  "tempest": "狂风怒号",
  // Splendor
  "bolt-beacon": "曳光信标", "mending-touch": "修复之触", "reassurance": "解忧消难",
  "final-words": "临终遗言", "healing-hands": "治愈之手", "second-wind": "复苏之风",
  "voice-of-reason": "理性之声", "divination": "预言卜筮", "life-ward": "生命护符",
  "shape-material": "物质塑形", "smite": "惩戒重击", "restoration": "复原术法",
  "zone-of-protection": "保护之域", "healing-strike": "治愈打击", "splendor-touched": "辉耀恩泽",
  "shield-aura": "护盾灵光", "stunning-sunlight": "震撼烈阳", "overwhelming-aura": "威压灵光",
  "salvation-beam": "救赎光束", "invigoration": "壮举再现", "resurrection": "亡者苏生",
  // Valor
  "bare-bones": "铁骨铮铮", "forceful-push": "有力推击", "i-am-your-shield": "吾身为盾",
  "body-basher": "蛮力冲撞", "bold-presence": "刚健风采", "critical-inspiration": "关键鼓舞",
  "lean-on-me": "中流砥柱", "goad-them-on": "激将大法", "support-tank": "坚盾后援",
  "armorer": "护甲大师", "rousing-strike": "振奋打击", "inevitable": "命中注定",
  "rise-up": "奋起直追", "shrug-it-off": "泰然自若", "valor-touched": "勇气恩泽",
  "full-surge": "火力全开", "ground-pound": "撼地猛击", "hold-the-line": "坚守阵线",
  "lead-by-example": "以身作则", "unbreakable": "坚不可摧", "unyielding-armor": "不灭甲胄",
};


function applyToFile(filename, mapper) {
  const fpath = join(packDir, filename);
  if (!existsSync(fpath)) { console.log(`  SKIP ${filename} (not found)`); return; }
  const data = JSON.parse(readFileSync(fpath, "utf8"));
  let updated = 0;
  for (const entry of data) {
    if (mapper(entry)) updated++;
  }
  writeFileSync(fpath, JSON.stringify(data, null, 2), "utf8");
  console.log(`  ${filename}: ${updated}/${data.length} entries updated`);
}

// ── Apply translations ──
console.log("\nApplying translations...\n");

applyToFile("classes.json", (e) => {
  const cn = CLASS_CN[e.slug];
  if (cn) { e.name_cn = cn; return true; }
  return false;
});

applyToFile("ancestries.json", (e) => {
  const cn = ANCESTRY_CN[e.slug];
  if (cn) { e.name_cn = cn; return true; }
  return false;
});

applyToFile("communities.json", (e) => {
  const cn = COMMUNITY_CN[e.slug];
  if (cn) { e.name_cn = cn; return true; }
  return false;
});

applyToFile("subclasses.json", (e) => {
  const cn = SUBCLASS_CN[e.slug];
  if (cn) { e.name_cn = cn; return true; }
  return false;
});

applyToFile("domain_cards.json", (e) => {
  let changed = false;
  if (e.domain && DOMAIN_CN[e.domain]) {
    e.domain_cn = DOMAIN_CN[e.domain];
    changed = true;
  }
  if (e.card_type && CARD_TYPE_CN[e.card_type]) {
    e.card_type_cn = CARD_TYPE_CN[e.card_type];
    changed = true;
  }
  const cn = DOMAIN_CARD_SLUG_CN[e.slug];
  if (cn) { e.name_cn = cn; changed = true; }
  return changed;
});

applyToFile("weapons.json", (e) => {
  const cn = WEAPON_CN[e.name];
  if (cn) { e.name_cn = cn; return true; }
  return false;
});

applyToFile("armors.json", (e) => {
  const cn = ARMOR_CN[e.name];
  if (cn) { e.name_cn = cn; return true; }
  return false;
});

applyToFile("loot.json", (e) => {
  const cn = LOOT_CN[e.name];
  if (cn) { e.name_cn = cn; return true; }
  return false;
});

applyToFile("consumables.json", (e) => {
  const cn = CONSUMABLE_CN[e.name];
  if (cn) { e.name_cn = cn; return true; }
  return false;
});

applyToFile("beastforms.json", (e) => {
  const cn = BEASTFORM_CN[e.name];
  if (cn) { e.name_cn = cn; return true; }
  return false;
});

// Print stats for items without CN translations
console.log("\n--- Missing translations check ---\n");
for (const [file, map] of [
  ["weapons.json", WEAPON_CN], ["armors.json", ARMOR_CN],
  ["loot.json", LOOT_CN], ["consumables.json", CONSUMABLE_CN],
  ["beastforms.json", BEASTFORM_CN], ["domain_cards.json", DOMAIN_CARD_SLUG_CN],
]) {
  const fpath = join(packDir, file);
  if (!existsSync(fpath)) continue;
  const data = JSON.parse(readFileSync(fpath, "utf8"));
  const missing = data.filter(e => !e.name_cn);
  if (missing.length > 0) {
    console.log(`${file}: ${missing.length}/${data.length} missing translations:`);
    const unique = [...new Set(missing.map(e => e.name))];
    unique.slice(0, 10).forEach(n => console.log(`  - "${n}"`));
    if (unique.length > 10) console.log(`  ... and ${unique.length - 10} more`);
  } else {
    console.log(`${file}: ALL ${data.length} translated ✓`);
  }
}

console.log("\nDone!");
