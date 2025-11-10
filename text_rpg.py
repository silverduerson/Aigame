#!/usr/bin/env python3
"""
text_rpg.py

A text-based roleplaying game inspired by classic interactive fiction (Zork, Colossal Cave).
Players choose a class, explore multiple areas, manage inventory, and engage in turn-based combat.
Multiple endings are supported based on decisions and performance.

Run: python3 text_rpg.py
"""

import random
import sys
import textwrap

# -----------------------------
# Utility helpers
# -----------------------------

def wrap(text, width=78):
    """Wrap long text for nicer terminal display."""
    return "\n".join(textwrap.wrap(text, width=width))

def prompt(msg="> "):
    """Get input from the player, handle EOF gracefully."""
    try:
        return input(msg).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")
        sys.exit(0)

def choose_from(prompt_text, choices):
    """
    Present numbered choices and return the selected key.
    choices: list of tuples (key, description)
    """
    print(wrap(prompt_text))
    for i, (key, desc) in enumerate(choices, 1):
        print(f"  {i}) {desc}")
    while True:
        ans = prompt("> ")
        if ans.isdigit():
            idx = int(ans) - 1
            if 0 <= idx < len(choices):
                return choices[idx][0]
        # allow direct key match (case-insensitive)
        for key, desc in choices:
            if ans.lower() == key.lower():
                return key
        print("That's not a valid command. Please choose a number or option name.")

# -----------------------------
# Data models: Items, Player, Enemy
# -----------------------------

class Item:
    def __init__(self, name, description="", effect=None, consumable=True):
        self.name = name
        self.description = description
        self.effect = effect  # function(player, target) or None
        self.consumable = consumable

    def use(self, user, target=None):
        """Apply the item's effect. Return True if item consumed."""
        if callable(self.effect):
            return self.effect(user, target)
        return False

class Enemy:
    def __init__(self, name, hp, attack, defense, magic=0, special=None, loot=None):
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.attack = attack
        self.defense = defense
        self.magic = magic
        self.special = special  # function(enemy, player) or None
        self.loot = loot or []

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, dmg):
        self.hp = max(self.hp - dmg, 0)

    def perform_special(self, player):
        if callable(self.special):
            return self.special(self, player)
        return None

class Player:
    def __init__(self, name, role, stats, abilities):
        self.name = name
        self.role = role
        self.level = 1
        self.exp = 0
        self.stats = stats  # dict: Strength, Agility, Magic, Endurance
        self.abilities = abilities  # dict of special abilities and descriptions
        self.max_hp = 10 + stats.get("Endurance", 0) * 2
        self.hp = self.max_hp
        self.inventory = []
        self.equipped = None
        self.alive = True
        self.path_flags = {}  # track decision flags for endings

    def is_alive(self):
        return self.hp > 0

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp

    def take_damage(self, dmg):
        self.hp = max(self.hp - dmg, 0)
        if self.hp == 0:
            self.alive = False

    def add_item(self, item):
        self.inventory.append(item)

    def remove_item(self, item_name):
        for i, it in enumerate(self.inventory):
            if it.name.lower() == item_name.lower():
                return self.inventory.pop(i)
        return None

    def list_inventory(self):
        if not self.inventory:
            print("Your inventory is empty.")
            return
        print("Inventory:")
        for i, it in enumerate(self.inventory, 1):
            print(f"  {i}) {it.name} - {it.description}")

    def get_item(self, name):
        for it in self.inventory:
            if it.name.lower() == name.lower():
                return it
        return None

    def equip_weapon(self, weapon):
        self.equipped = weapon

    def attack_damage(self):
        base = self.stats.get("Strength", 1)
        weapon_bonus = 0
        if self.equipped and hasattr(self.equipped, "attack_bonus"):
            weapon_bonus = getattr(self.equipped, "attack_bonus", 0)
        # damage includes small randomness
        return max(1, base + weapon_bonus + random.randint(0, self.stats.get("Agility", 0)))

# -----------------------------
# Items and effects definitions
# -----------------------------

def potion_effect(player, _target=None):
    amt = 6 + player.stats.get("Magic", 0) // 2
    healed = min(player.max_hp - player.hp, amt)
    player.heal(amt)
    print(f"You drink the potion and recover {healed} HP (now {player.hp}/{player.max_hp}).")
    return True  # consumed

def elixir_effect(player, _target=None):
    # Full heal, rare
    player.hp = player.max_hp
    print(f"A warm glow fills you. You are fully healed ({player.hp}/{player.max_hp}).")
    return True

# Special weapon item class with attack bonus
class Weapon(Item):
    def __init__(self, name, description, attack_bonus=0):
        super().__init__(name, description, effect=None, consumable=False)
        self.attack_bonus = attack_bonus

# Predefined items
HEAL_POTION = Item("Potion", "Restores a moderate amount of HP.", potion_effect, consumable=True)
ELIXIR = Item("Elixir", "Fully restores HP. Very rare.", elixir_effect, consumable=True)
SHORT_SWORD = Weapon("Short Sword", "A basic sword. +2 attack.", attack_bonus=2)
WOODEN_SHIELD = Item("Wooden Shield", "Small shield that can be used to Defend (flavor).", consumable=False)
DRAGON_AMULET = Item("Dragon Amulet", "An old amulet pulsing with dragon magic.")

# -----------------------------
# Combat system
# -----------------------------

def combat(player, enemy):
    """Turn-based combat. Returns True if player wins, False if player dies or flees unsuccessfully."""
    print(wrap(f"A {enemy.name} stands before you! (HP: {enemy.hp}/{enemy.max_hp})"))
    while player.is_alive() and enemy.is_alive():
        print("\nYour turn.")
        print(f"  HP: {player.hp}/{player.max_hp} | Enemy HP: {enemy.hp}/{enemy.max_hp}")
        actions = [("attack", "Attack the enemy"),
                   ("defend", "Brace to reduce incoming damage this turn"),
                   ("use", "Use item from inventory"),
                   ("run", "Attempt to flee")]
        # Add magic/special if player has abilities
        if player.abilities:
            actions.append(("ability", "Use a class ability"))
        choice = choose_from("Choose an action:", actions)
        defended = False
        if choice == "attack":
            dmg = player.attack_damage()
            # enemy defense reduces damage
            net = max(0, dmg - enemy.defense)
            # small crit chance based on agility
            crit_roll = random.randint(1, 20)
            if crit_roll <= max(2, player.stats.get("Agility", 1) // 2):
                net += 3
                print("Critical strike!")
            enemy.take_damage(net)
            print(f"You strike the {enemy.name} for {net} damage.")
        elif choice == "defend":
            defended = True
            print("You take a defensive stance. Incoming damage will be reduced.")
        elif choice == "use":
            if not player.inventory:
                print("Your inventory is empty.")
            else:
                player.list_inventory()
                print("Type the name or number of the item to use, or blank to cancel.")
                ans = prompt("> ")
                if ans == "":
                    pass
                elif ans.isdigit():
                    idx = int(ans) - 1
                    if 0 <= idx < len(player.inventory):
                        item = player.inventory[idx]
                        consumed = item.use(player, enemy)
                        if consumed:
                            player.inventory.pop(idx)
                    else:
                        print("Invalid item number.")
                else:
                    item = player.get_item(ans)
                    if item:
                        consumed = item.use(player, enemy)
                        if consumed:
                            player.remove_item(item.name)
                    else:
                        print("You don't have that item.")
        elif choice == "ability":
            # simplistic ability handling: each ability has a name and function
            if not player.abilities:
                print("You have no abilities.")
            else:
                keys = list(player.abilities.keys())
                choices = [(k, f"{k} - {player.abilities[k]['desc']}") for k in keys]
                ability_key = choose_from("Choose an ability to use:", choices)
                ability = player.abilities.get(ability_key)
                if ability and callable(ability.get("func")):
                    # ability function returns message or effects
                    ability["func"](player, enemy)
        elif choice == "run":
            # flee chance depends on agility vs enemy attack
            flee_chance = 50 + (player.stats.get("Agility", 0) - enemy.attack) * 5
            roll = random.randint(1, 100)
            if roll <= max(10, min(90, flee_chance)):
                print("You successfully fled the battle.")
                return False  # not a win, but survived
            else:
                print("You fail to escape!")

        # Enemy's turn if still alive
        if enemy.is_alive():
            if enemy.special and random.random() < 0.2:  # 20% chance of special
                enemy.perform_special(player)
            else:
                # base enemy damage with randomness and player's defense if defending
                dmg = max(0, enemy.attack + random.randint(-1, 2) - (player.stats.get("Endurance", 0) // 2))
                # if player defended, reduce
                if 'defended' in locals() and defended:
                    dmg = max(0, dmg // 2)
                player.take_damage(dmg)
                print(f"The {enemy.name} hits you for {dmg} damage. (HP: {player.hp}/{player.max_hp})")

    if player.is_alive():
        print(f"You defeated the {enemy.name}!")
        # loot drop
        for it in enemy.loot:
            print(f"You found: {it.name} - {it.description}")
            player.add_item(it)
        return True
    else:
        print("You have fallen in battle...")
        return False

# -----------------------------
# Enemy specials
# -----------------------------

def bandit_special(enemy, player):
    # bandit tries to steal an item
    if player.inventory and random.random() < 0.4:
        stolen = random.choice(player.inventory)
        player.remove_item(stolen.name)
        print(f"The {enemy.name} deftly steals your {stolen.name}!")
    else:
        # regular hit
        dmg = max(1, enemy.attack + random.randint(0, 2))
        player.take_damage(dmg)
        print(f"The {enemy.name} slashes you for {dmg} damage.")

def dragon_breath(enemy, player):
    dmg = 8 + random.randint(0, 6)
    player.take_damage(dmg)
    print(wrap(f"The {enemy.name} breathes fire! You take {dmg} fire damage."))

# -----------------------------
# Areas and Encounters
# -----------------------------

def haunted_forest(player):
    print(wrap("You enter the Haunted Forest. Fog curls between twisted trees; soft whispers brush your ears."))
    # small encounter: wolves or find potion
    event_roll = random.randint(1, 100)
    if event_roll <= 40:
        wolf = Enemy("Dire Wolf", hp=12, attack=4, defense=1, loot=[HEAL_POTION])
        combat(player, wolf)
    elif event_roll <= 75:
        print("You find an old satchel near a tree stump containing a Potion.")
        player.add_item(HEAL_POTION)
    else:
        print("A ghost appears and offers to test your heart. You feel strangely wiser.")
        player.stats["Magic"] += 1
        print("Your Magic increases by 1.")

def enchanted_castle(player):
    print(wrap("You approach the Enchanted Castle: banners flutter though there is no wind."))
    # Decision point with branching path
    choice = choose_from("At the gate a spectral knight asks your intent. How do you respond?",
                         [("fight", "Declare you intend to conquer the castle"),
                          ("peace", "Tell the knight you seek peace and knowledge"),
                          ("trick", "Attempt to trick the knight")]
                         )
    if choice == "fight":
        knight = Enemy("Spectral Knight", hp=20, attack=6, defense=2, loot=[SHORT_SWORD])
        combat(player, knight)
        # flag for ending influence
        player.path_flags["castle_blooded"] = True
    elif choice == "peace":
        print("The knight smiles and escorts you into the library where you learn an arcane secret.")
        player.stats["Magic"] += 2
        player.path_flags["castle_scholar"] = True
    else:
        print("You attempt to trick the knight. The knight sees through you and laughs, but grants a test of wit.")
        # puzzle-like random chance
        if random.random() < 0.6 + player.stats.get("Agility", 0) * 0.02:
            print("You solved the test! A minor artifact is yours.")
            player.add_item(Item("Runestone", "A small runestone that hums with energy."))
            player.path_flags["castle_clever"] = True
        else:
            print("You fail the test and the knight ushers you away.")
            player.take_damage(3)

def bandit_lair(player):
    print(wrap("You find the Bandit's Lair — torches, crude flags, and the clink of coins."))
    # Multiple enemies with varying difficulties
    bandit1 = Enemy("Bandit Thug", hp=10, attack=3, defense=0, special=bandit_special, loot=[HEAL_POTION])
    bandit2 = Enemy("Bandit Captain", hp=14, attack=5, defense=1, loot=[WOODEN_SHIELD])
    # optional stealth approach
    approach = choose_from("Do you sneak in or barge into the lair?",
                           [("sneak", "Sneak in quietly (higher chance to avoid combat)"),
                            ("barge", "Barge in and fight")]
                           )
    if approach == "sneak":
        success = random.random() < 0.5 + (player.stats.get("Agility", 0) * 0.05)
        if success:
            print("You slip past sentries and steal a small sack of coins and a Potion.")
            player.add_item(HEAL_POTION)
            player.path_flags["bandit_sneak"] = True
            return
        else:
            print("You're spotted!")
    # If not sneaking successfully, fight both
    if combat(player, bandit1):
        combat(player, bandit2)

def dragon_cavern(player):
    print(wrap("The cavern smells of sulfur. A massive dragon stirs, its eyes rolling open."))
    # Decision: fight, befriend, or sneak steal amulet
    choice = choose_from("The dragon awakes. What do you do?",
                         [("fight", "Draw weapon and attack the dragon"),
                          ("befriend", "Attempt to befriend or parley with the dragon"),
                          ("steal", "Try to steal the amulet while it's still waking")]
                         )
    if choice == "steal":
        chance = 30 + player.stats.get("Agility", 0) * 5
        if random.randint(1, 100) <= chance:
            print("You quietly take the Dragon Amulet from a nearby pedestal without waking the dragon!")
            player.add_item(DRAGON_AMULET)
            player.path_flags["amulet_stolen"] = True
            return "stole_amulet"
        else:
            print("The amulet slips and clatters! The dragon is alerted.")
            # continue to fight
    if choice == "befriend":
        # Use charisma-ish logic via Magic or Agility
        charm = player.stats.get("Magic", 0) + player.stats.get("Agility", 0)
        if random.randint(1, 100) <= 30 + charm * 5:
            print(wrap("Your words and actions calm the dragon. It regards you with ancient curiosity."))
            player.path_flags["dragon_friend"] = True
            # dragon gives a quest and leaves you with a boon
            player.add_item(Item("Dragon's Mark", "A small token of the dragon's favor."))
            return "befriended"
        else:
            print("The dragon is unimpressed. It prepares to strike.")
    # If choose fight or failed befriending/steal
    dragon = Enemy("Ancient Dragon", hp=40, attack=8, defense=3, special=dragon_breath,
                   loot=[DRAGON_AMULET, ELIXIR])
    won = combat(player, dragon)
    if won:
        player.path_flags["dragon_slain"] = True
        return "slain"
    else:
        return "died"

# -----------------------------
# Character creation & abilities
# -----------------------------

def warrior_shout(player, enemy):
    # simple warrior ability: powerful attack reducing enemy defense for turn
    print("You shout a battle cry, bolstering your strike!")
    dmg = player.attack_damage() + 3
    enemy.take_damage(dmg)
    print(f"You strike for {dmg} damage with your battle cry.")

def mage_bolt(player, enemy):
    # mage ability: magic bolt ignoring some defense
    dmg = 4 + player.stats.get("Magic", 0) + random.randint(0, 4)
    enemy.take_damage(dmg)
    print(f"You cast a crackling bolt of magic for {dmg} damage.")

def rogue_trick(player, enemy):
    # rogue ability: chance to stun (skip enemy turn)
    print("You perform a quick feint.")
    if random.random() < 0.4 + player.stats.get("Agility", 0) * 0.02:
        print("You surprise the enemy and strike while they're stunned!")
        dmg = player.attack_damage() + 2
        enemy.take_damage(dmg)
        print(f"You deal {dmg} damage.")
    else:
        print("The feint fails. No extra effect.")

CLASS_OPTIONS = {
    "Warrior": {
        "stats": {"Strength": 6, "Agility": 3, "Magic": 1, "Endurance": 5},
        "abilities": {"Battle Cry": {"desc": "A powerful attack that deals bonus damage.", "func": warrior_shout}}
    },
    "Mage": {
        "stats": {"Strength": 2, "Agility": 3, "Magic": 7, "Endurance": 3},
        "abilities": {"Magic Bolt": {"desc": "A ranged magic attack that ignores some defense.", "func": mage_bolt}}
    },
    "Rogue": {
        "stats": {"Strength": 4, "Agility": 7, "Magic": 2, "Endurance": 3},
        "abilities": {"Trick": {"desc": "A deceptive strike that may stun or deal extra damage.", "func": rogue_trick}}
    }
}

# -----------------------------
# Main storyline flow and endings
# -----------------------------

def prologue():
    print(wrap("Welcome to 'Echoes of Ember' — a short text-based RPG."))
    name = prompt("What is your name, adventurer? ")
    # choose class
    print("Choose your class:")
    for i, cls in enumerate(CLASS_OPTIONS.keys(), 1):
        print(f"  {i}) {cls}")
    while True:
        ans = prompt("> ")
        if ans.isdigit():
            idx = int(ans) - 1
            if 0 <= idx < len(CLASS_OPTIONS):
                role = list(CLASS_OPTIONS.keys())[idx]
                break
        elif ans.title() in CLASS_OPTIONS:
            role = ans.title()
            break
        print("That's not a valid command. Type the class name or number.")

    data = CLASS_OPTIONS[role]
    player = Player(name=name or "Nameless", role=role, stats=data["stats"].copy(), abilities=data["abilities"].copy())
    print(wrap(f"You are {player.name}, the {player.role}. Your adventure begins."))
    # starting items
    player.add_item(HEAL_POTION)
    player.add_item(SHORT_SWORD)
    player.equip_weapon(SHORT_SWORD)
    return player

def chapter_one(player):
    print(wrap("CHAPTER 1: The Road and the Fork"))
    print(wrap("You travel a winding road and come to a fork leading to three destinations:"))
    choice = choose_from("Where do you go?",
                         [("forest", "Haunted Forest"),
                          ("castle", "Enchanted Castle"),
                          ("bandits", "Bandit's Lair")]
                         )
    if choice == "forest":
        haunted_forest(player)
    elif choice == "castle":
        enchanted_castle(player)
    elif choice == "bandits":
        bandit_lair(player)

def chapter_two(player):
    print(wrap("CHAPTER 2: The Cavern of Echoes"))
    result = dragon_cavern(player)
    return result

def epilogue(player):
    print("\n" + "="*60)
    print("EPILOGUE: Consequences of your choices".center(60))
    print("="*60 + "\n")
    # Determine endings: At least three distinct endings
    # Ending A: Befriended dragon + scholar -> "Dragon's Protector" ending
    if player.path_flags.get("dragon_friend") and player.path_flags.get("castle_scholar"):
        print(wrap("With knowledge from the castle and the dragon's trust, you become a protector of ancient lore. The kingdom thrives under your guidance."))
        ending = "Protector"
    # Ending B: Slain dragon + castle_blooded -> "Hero's Victory"
    elif player.path_flags.get("dragon_slain") and player.path_flags.get("castle_blooded"):
        print(wrap("Having bathed in the dragon's blood and proven your strength at the castle, ballads are sung of your deeds. You are a celebrated hero."))
        ending = "Hero"
    # Ending C: Stole amulet and fled -> "Wanted Outlaw"
    elif player.path_flags.get("amulet_stolen"):
        print(wrap("You escaped with the Dragon Amulet. Richer and notorious, you live a life on the run — wealthy but hunted."))
        ending = "Outlaw"
    # Ending D: You died or failed crucial fights -> "Fallen"
    elif not player.is_alive():
        print(wrap("Your journey ends in darkness. Your story becomes a cautionary tale told in hushed whispers."))
        ending = "Fallen"
    # Ending E: Neutral endings based on other flags
    else:
        print(wrap("Your path was uneven — some choices bore fruit, others cost you dearly. The road ahead remains open; your story continues in whispered possibilities."))
        ending = "Open"
    print(f"\nEnding achieved: {ending}")
    print("\nThank you for playing Echoes of Ember.")

# -----------------------------
# Commands utility (inventory management and help)
# -----------------------------

def show_help():
    print(wrap("Available commands while not in combat:"))
    print("  inventory  - list items")
    print("  use <name> - use an item by name (e.g., 'use potion')")
    print("  drop <name> - discard an item")
    print("  stats - show character stats")
    print("  explore - continue with next chapter/action")
    print("  quit - exit game")

def main_loop(player):
    print("\nType 'help' at any time for commands.\n")
    chapter_one(player)
    # small hub commands before chapter two
    while player.is_alive():
        cmd = prompt("> ").strip().lower()
        if cmd == "help":
            show_help()
        elif cmd == "inventory":
            player.list_inventory()
        elif cmd.startswith("use "):
            name = cmd[4:].strip()
            item = player.get_item(name)
            if item:
                consumed = item.use(player)
                if consumed:
                    player.remove_item(item.name)
            else:
                print("You don't have that item.")
        elif cmd.startswith("drop "):
            name = cmd[5:].strip()
            removed = player.remove_item(name)
            if removed:
                print(f"You dropped: {removed.name}")
            else:
                print("You don't have that item to drop.")
        elif cmd == "stats":
            print("Stats:")
            for k, v in player.stats.items():
                print(f"  {k}: {v}")
            print(f"HP: {player.hp}/{player.max_hp} | Class: {player.role}")
        elif cmd == "explore":
            res = chapter_two(player)
            # epilogue after cavern
            break
        elif cmd == "quit":
            print("Farewell, adventurer.")
            sys.exit(0)
        else:
            print("That's not a valid command. Type 'help' for available commands.")
    epilogue(player)

# -----------------------------
# Entry point
# -----------------------------

def main():
    player = prologue()
    main_loop(player)

if __name__ == "__main__":
    main()
