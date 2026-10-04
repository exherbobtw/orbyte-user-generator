#!/usr/bin/env python3
"""
Orbyte rare-username availability scanner (READ-ONLY).

Runs forever until you hit Ctrl+C, working through short word-like names
(real words + pronounceable ones like "helfo") instead of random gibberish.
It creates no accounts and logs in as nobody.

    GET https://api.orbyte.fun/api/usernames/check?username=<name>

Available names are printed to stdout (one per line) and appended to --out.

Usage:
    python3 orbyte_username_check.py                          # runs forever
    python3 orbyte_username_check.py --mode word --length 4   # only real 4-letter words
    python3 orbyte_username_check.py --length 4,5 --out open.txt 2>/dev/null
    python3 orbyte_username_check.py --count 500              # stop after 500 checks

Stop with Ctrl+C. Register what you like at https://orbyte.fun/ -> "Create an account".
"""

import argparse
import json
import random
import string
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.orbyte.fun"
CHECK_PATH = "/api/usernames/check"
DEFAULT_OUT = "orbyte_available.txt"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Real short words to seed the search. Kept mild on purpose: whatever gets
# claimed ends up on a public profile.
WORDS = """
able acid aged also area army away baby back bake ball band bank bare bark barn base
bath bead beam bean bear beat been bell belt bend best bias bird bite blue boat body boil
bold bolt bomb bond bone book boom boot bore born both bowl brag bran brim brow buck bulb
bulk burn bush cage cake calm came camp card care cart case cash cast cave cell chat chef
chew chin chip chop city clad clam clap claw clay clip club coal coat code coil coin cold
colt comb come cone cook cool cope cord core cork corn cost cove crab crew crib crop crow
cube cult curb cure curl cute dame damp dare dark darn dart dash data date dawn deaf deal
dean dear deck deep deer desk dial dice diet dime dine dish dock does dome done doom door
dose dove down doze drag draw drum duck duel duet duke dull duly dumb dump dune dusk duty
each earn ease east easy echo edit envy epic even ever evil exam exit eye face fact fade
fail fair fake fall fame fang fare farm fast fate fawn fear feat feed feel fell felt fend
fern feud file fill film find fine fire firm fish fist five flag flap flat flaw flea fled
flee flew flex flip flit flow flue flux foal foil fold folk fond font food fool foot ford
fore fork form fort foul four fowl free fret frog from fuel full fume fund fury fuss gain
gait gale gall game gang gape gate gave gaze gear gene germ gift gild gill girl gist give
glad glee glen glow glue gnat goal goat goes gold golf gone gong good gore gown grab gram
gray grew grey grid grim grin grip grit grow gulf gull gulp guru gust guts hack hail hair
half hall halo halt hand hang hard hare harp hash hate haul have hawk haze head heal heap
hear heat heed heel heir held helm help hemp herb herd here hero hers hide high hike hill
hilt hind hint hire hiss hive hold hole holy home hone hood hoof hook hoop hope horn hose
host hour howl huge hull hump hung hunt hurl hurt hush hymn icon idea idle inch iota iris
iron isle itch item jade jail jazz jeer jest join joke jolt jury just keel keen keep kelp
kept kick kiln kilt kind king kiss kite knee kneel knelt knob knot know lace lack lady laid
lake lamb lame lamp land lane lash last late laud lava lawn lazy lead leaf lean leap left
lend lens less lest levy liar lice lick lied life lift like limb lime limo line link lint
lion list live load loaf loan lobe lock loft logo lone long look loom loop lord lore lose
loss lost loud love luck lung lure lush lute made mail maim main make male mall malt mane
many mare mark mars mask mass mast mate math maze meal mean meat meet meld melt memo mend
menu mere mesh mess mild mile milk mill mind mine mint mire miss mist moan mock mode mold
mole molt monk mood moon moor more moss most moth move much mule mull mute myth nail name
navy near neat neck need neon nest news newt next nice nick nine node none noon norm nose
note noun nurse oath obey oboe odds odor ogre oily okay omen omit once only onto onus onyx
ooze open oral over owed owner pace pack pact page paid pail pain pair pale palm pane pant
park part pass past pate path pave pawn peak peal pear peat peck peek peel peer pelt perk
pest pick pier pile pill pine pink pint pipe pity plan play plea pled plod plot plow ploy
plug plum plus poem poet poke pole poll pond pool poor pope pore pork port pose posh post
pour pout pray prep prey prim prod prom prop prow puck puff pull pulp pump punk pure push
quiz rack raft rage raid rail rain rake ramp rang rank rant rare rash rate rave read real
ream reap rear redo reed reef reek reel rein rely rend rent rest rice rich ride rift rile
rind ring rink riot ripe rise risk rite road roam roar robe rock rode role roll roof rook
room root rope rose rosy rout rove ruby rude ruin rule rung runt ruse rush rust sack safe
saga sage said sail sake salt same sand sane sang sank sash save scam scan scar seal seam
sear seat sect seed seek seem seen seep self sell semi send sent shed shin ship shop shot
show shun shut sick side sift sigh sign silk sill silo silt sing sink sire site size skew
skid skim skin skip slab slam slap sled slew slid slim slip slot slow slug slum slur smog
smug snag snap snip snob snow snub snug soak soap soar sock soft soil sold sole solo some
song soon soot sore sort soul soup sour span spar spat sped spin spit spot spud spun spur
stab stag star stay stem step stew stir stop stow stub stud stun such suit sulk sung sunk
sure surf swab swam swan swap swat sway swim swum tack tact tail take tale talk tall tame
tang tank tape tart task taut taxi teal team tear tell tend tent term test text than that
thaw thee them then they thin this thud thug thus tick tide tidy tier tile till tilt time
tint tiny tire toad toga toil told toll tomb tone took tool tore torn tote tour tout town
tram trap tray tree trek trim trio trip trod trot true tuba tube tuck tuft tuna tune turf
turn tusk twig twin type ugly undo unit unto upon urge used user vain vale vane vase vast
veal veer veil vein vent verb very vest veto vial vibe vice view vine visa void volt vote
wade wage wail wait wake walk wall wand wane want ward ware warm warn warp wart wary wash
wasp watt wave wavy waxy weak wean wear weed week weep weld well welt went wept were west
what when whim whip whir whiz whom wick wide wife wild will wilt wind wine wing wink wipe
wire wise wish wisp with woke wolf womb word wore work worm worn wrap wren yard yarn yawn
yeah year yell yelp yoga yoke yolk your zeal zinc zing zone zoom
""".split()

VOWELS = "aeiou"

# Syllable pieces. A name is built as onset+vowel+coda, repeated, which is what
# makes the output read like a word (hel-fo, bra-ko, stra-mi) instead of noise.
ONSET_BY_LEN = {
    1: "bcdfghjklmnprstvwyz",
    2: ["bl", "br", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "pl", "pr", "sc",
        "sk", "sl", "sm", "sn", "sp", "st", "sw", "tr", "tw", "wh", "ch", "sh",
        "th", "qu"],
    3: ["str", "spr", "scr"],
}
CODA_BY_LEN = {
    1: ["l", "n", "r", "s", "t", "m", "p", "b", "d", "g", "k", "f", "x", "z"],
    2: ["ck", "ng", "st", "nt", "nd", "lt", "mp", "sh", "th", "rn", "rt", "rd",
        "ll", "ss", "ld", "nk", "ft", "pt"],
}

# Auto-generated names occasionally land on a slur; don't hand those to a
# profile. Pass --no-filter to disable.
BLOCKLIST = {
    "nazi", "rape", "rapist", "kike", "spic", "wop", "fag", "fags", "phag", "dyke",
    "trann", "retard", "nigg", "coon", "gook", "cunt", "fuck", "fuk", "fuc", "shit",
    "bitch", "whore", "slut", "penis", "pussy", "vagina", "vagin", "dick", "homo",
    "lesbo", "jizz", "testic", "anus", "semen", "titt", "boob", "cumm", "porn",
    "sexc", "nude", "piss", "lynch", "kkk",
}


def filtered(name: str) -> bool:
    low = name.lower()
    return not any(bad in low for bad in BLOCKLIST)


def looks_natural(s: str) -> bool:
    """Cheap aesthetic filter: no triple repeats, no vowel soup, no consonant wall."""
    n = len(s)
    if n < 3:
        return s.isalpha()
    # no letter three times in a row
    if any(s[i] == s[i + 1] == s[i + 2] for i in range(n - 2)):
        return False
    is_vowel = [c in VOWELS for c in s]
    # no three vowels in a row
    if any(all(is_vowel[i : i + 3]) for i in range(n - 2)):
        return False
    # no four consonants in a row (keeps it pronounceable; "str"/"spr" onsets are fine)
    if any(all(not x for x in is_vowel[i : i + 4]) for i in range(n - 3)):
        return False
    # don't end on a vowel pair like "hae"
    if n >= 2 and is_vowel[-1] and is_vowel[-2]:
        return False
    return s.isalpha()


def pronounceable(rng: random.Random, length: int) -> str:
    """Build a word-shaped name of exactly `length` letters, e.g. helfo, brint, skope.

    The name is assembled syllable by syllable (onset + vowel + optional coda),
    which is what keeps the endings readable: helfo, bra-ko, stra-mi.
    """
    for _ in range(400):
        # 1 syllable needs >= 2 chars, at most 6; same bound scaled for more.
        counts = [n for n in (1, 2, 3) if 2 * n <= length <= 6 * n]
        if not counts:
            break
        n = rng.choice(counts)
        onsets = [1] * n
        codas = [0] * n

        # Hand out the spare letters to onset clusters and codas, two slots each.
        budget = length - 2 * n
        slots = [(kind, i) for i in range(n) for kind in ("O", "C") for _ in range(2)]
        rng.shuffle(slots)
        for kind, i in slots:
            if budget == 0:
                break
            if kind == "O":
                onsets[i] += 1
            else:
                codas[i] += 1
            budget -= 1
        if budget:
            continue

        s = ""
        for i in range(n):
            s += rng.choice(ONSET_BY_LEN[onsets[i]]) + rng.choice(VOWELS)
            if codas[i]:
                s += rng.choice(CODA_BY_LEN[codas[i]])

        if len(s) == length and looks_natural(s) and filtered(s):
            return s

    # Give up on style rather than stall the loop.
    return "".join(rng.choice(string.ascii_lowercase) for _ in range(length))


def candidate_stream(mode: str, lengths: list[int], rng: random.Random):
    """Endless stream of candidate names. Never runs dry."""
    pool = [w for w in rng.sample(WORDS, len(WORDS)) if len(w) in lengths]
    idx = 0
    i = 0
    while True:
        i += 1
        want_word = idx < len(pool) and (
            mode == "word" or (mode == "mix" and i % 2 == 1)
        )
        if want_word:
            yield pool[idx]
            idx += 1
        else:
            yield pronounceable(rng, rng.choice(lengths))


def make_opener() -> urllib.request.OpenerDirector:
    opener = urllib.request.build_opener()
    opener.addheaders = [
        ("Accept", "application/json"),
        ("Origin", "https://orbyte.fun"),
        ("User-Agent", USER_AGENT),
    ]
    return opener


def check(opener, username: str, retries: int = 3) -> dict:
    url = f"{API_BASE}{CHECK_PATH}?{urllib.parse.urlencode({'username': username})}"
    for attempt in range(retries + 1):
        try:
            with opener.open(url, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                time.sleep(min(30, 5 * (attempt + 1)))
                continue
            if exc.code in (500, 502, 503, 504) and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            return {"error": f"HTTP {exc.code}"}
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            return {"error": str(exc)}
    return {"error": "unreachable"}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Scan Orbyte for available usernames. Read-only; creates no accounts. "
        "Runs until Ctrl+C unless --count is given."
    )
    ap.add_argument("--mode", choices=["word", "pseudo", "mix"], default="mix",
                    help="word=real short words, pseudo=made-up but pronounceable, "
                         "mix=alternate (default)")
    ap.add_argument("--length", default="4,5",
                    help="comma-separated name lengths to accept (default '4,5')")
    ap.add_argument("--count", type=int, default=0,
                    help="stop after N checks; 0 = never stop (default)")
    ap.add_argument("--delay", type=float, default=1.0,
                    help="seconds between requests (default 1.0)")
    ap.add_argument("--out", default=DEFAULT_OUT,
                    help=f"append available names here (default {DEFAULT_OUT})")
    ap.add_argument("--no-filter", action="store_true", help="disable the blocklist")
    ap.add_argument("--quiet", action="store_true",
                    help="don't print progress to stderr")
    ap.add_argument("--seed", type=int, help="seed the name generator for repeatable runs")
    args = ap.parse_args()

    if args.no_filter:
        global BLOCKLIST
        BLOCKLIST = set()

    try:
        lengths = sorted({int(x) for x in args.length.split(",") if x.strip()})
    except ValueError:
        raise SystemExit("--length must be comma-separated integers, e.g. '4,5'")
    if not lengths or min(lengths) < 2 or max(lengths) > 24:
        raise SystemExit("--length values must be between 2 and 24 (Orbyte's limit)")

    rng = random.Random(args.seed)
    stream = candidate_stream(args.mode, lengths, rng)
    opener = make_opener()

    total_words = len({w for w in WORDS if len(w) in lengths})
    if not args.quiet:
        print(
            f"mode={args.mode} lengths={lengths} ({total_words} real words available) "
            f"-> {API_BASE}{CHECK_PATH} every {args.delay}s. "
            f"Ctrl+C to stop.",
            file=sys.stderr,
        )

    seen: set[str] = set()
    checked = available = taken = errors = skipped = 0
    out_fh = open(args.out, "a", encoding="utf-8") if args.out else None
    start = time.monotonic()
    stop_reason = "count reached"

    try:
        for name in stream:
            if name in seen:
                skipped += 1
                continue
            seen.add(name)
            checked += 1

            result = check(opener, name)

            if "error" in result:
                errors += 1
                if not args.quiet:
                    print(f"  ! {name}: {result['error']}", file=sys.stderr)
            elif result.get("valid") and not result.get("taken"):
                available += 1
                print(name, flush=True)
                if out_fh:
                    out_fh.write(name + "\n")
                    out_fh.flush()
            else:
                taken += 1

            if not args.quiet and checked % 25 == 0:
                rate = checked / max(time.monotonic() - start, 1e-9)
                print(
                    f"  .. {checked} checked, {available} available, {taken} taken, "
                    f"{errors} errors, {rate:.1f}/s",
                    file=sys.stderr,
                )

            if args.count and checked >= args.count:
                stop_reason = "count reached"
                break
            time.sleep(args.delay)
    except KeyboardInterrupt:
        stop_reason = "Ctrl+C"
    finally:
        if out_fh:
            out_fh.close()

    mins = (time.monotonic() - start) / 60
    print(
        f"\nstopped ({stop_reason}) after {checked} checks in {mins:.1f} min: "
        f"{available} available, {taken} taken, {errors} errors, "
        f"{skipped} duplicates skipped",
        file=sys.stderr,
    )
    if args.out and available:
        print(f"available names appended to {args.out}", file=sys.stderr)

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
