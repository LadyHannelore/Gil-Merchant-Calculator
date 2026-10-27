"""Pure game rules for the Lion Merchant game (no pygame dependency)."""
import random
from dataclasses import dataclass

COINS = [
    ("Lion", 1),
    ("Small Copper", 10),
    ("Medium Copper", 100),
    ("Large Copper", 1_000),
    ("Small Silver", 10_000),
    ("Large Silver", 100_000),
    ("Small Gold", 1_000_000),
    ("Large Gold", 10_000_000),
]
COIN_VALUES = [v for _, v in COINS]


def short(n: int) -> str:
    if n >= 1_000_000 and n % 1_000_000 == 0:
        return f"{n // 1_000_000}M"
    if n >= 1_000 and n % 1_000 == 0:
        return f"{n // 1_000}K"
    return str(n)


def coin_name(value: int) -> str:
    return dict((v, n) for n, v in COINS)[value]


def minimal_coins(amount: int) -> dict:
    """Fewest-coin breakdown of an amount, as {coin value: count}."""
    out = {}
    for v in reversed(COIN_VALUES):
        n, amount = divmod(amount, v)
        if n:
            out[v] = n
    return out


@dataclass
class Order:
    kind: str  # "change", "exchange", "quote", "margin"
    lines: list
    answer: int = 0            # numeric answer for typed orders
    target_total: int = 0      # lion total for coin-tray orders
    only_coin: int = 0         # if set, the tray may only hold this coin
    unit: str = ""             # hint shown beside typed answers
    cost: int = 0              # haggle: what the item cost the shop
    offer: int = 0             # haggle: customer's current offer
    budget: int = 0            # haggle: most the customer will really pay
    rounds: int = 0            # haggle: counter-offers made so far

    @property
    def uses_tray(self) -> bool:
        return self.kind in ("change", "exchange")


MIN_PROFIT_PCT = 15
MAX_HAGGLE_ROUNDS = 3


def haggle_min(cost: int) -> int:
    """Lowest price the shop accepts (cost plus the minimum profit)."""
    return cost * (100 + MIN_PROFIT_PCT) // 100


def haggle_lines(order: Order) -> list:
    return [
        f"Cost {order.cost:,}. Min profit {MIN_PROFIT_PCT}%.",
        f"I offer {order.offer:,} lion.",
        "Accept, or type a counter!",
    ]


def make_haggle(level: int, rng=random) -> Order:
    cost = rng.randrange(5, 20 + 20 * min(level, 4)) * 1000
    low = haggle_min(cost)
    step = cost // 20
    if rng.random() < 0.8:
        budget = low + rng.randrange(0, 5) * step
    else:
        budget = low - rng.randrange(1, 4) * step
    offer = max(100, (cost * rng.randrange(60, 100) // 100) // 100 * 100)
    order = Order(
        "haggle", [], unit="lion", cost=cost, offer=offer, budget=budget)
    order.lines = haggle_lines(order)
    return order


def haggle_accept(order: Order):
    """Player accepts the current offer. Returns (status, message)."""
    if order.offer >= haggle_min(order.cost):
        return "sold", f"Sold for {order.offer:,}!"
    return "bad_deal", f"Too low! Min was {haggle_min(order.cost):,}"


def haggle_counter(order: Order, counter: int):
    """Player counters. Returns (status, message); may update order.offer."""
    low = haggle_min(order.cost)
    if counter < low:
        return "bad_deal", f"Too low! Min was {low:,}"
    if counter <= max(order.budget, order.offer):
        order.offer = counter
        return "sold", f"Sold for {counter:,}!"
    order.rounds += 1
    if order.rounds >= MAX_HAGGLE_ROUNDS:
        return "walked", "Customer walked away."
    order.offer = max(order.offer, (order.offer + counter) // 2 // 100 * 100)
    order.lines = haggle_lines(order)
    return "new_offer", f"Hmm... how about {order.offer:,}?"


def make_order(level: int, rng=random) -> Order:
    kind = rng.choice(
        ["change", "exchange", "quote", "margin", "haggle", "haggle"])
    tier = min(level, 4)
    if kind == "haggle":
        return make_haggle(level, rng)

    if kind == "change":
        price = rng.randrange(1, 30 + 40 * tier) * 10
        paid_with = next(v for v in COIN_VALUES if v > price and v >= 100)
        if rng.random() < 0.5:
            nxt = [v for v in COIN_VALUES if v > paid_with]
            paid_with = nxt[0] if nxt else paid_with
        return Order(
            "change",
            [
                f"Item costs {price:,} lion.",
                f"I pay 1 {coin_name(paid_with)}",
                f"({paid_with:,} lion). My change?",
            ],
            target_total=paid_with - price,
        )

    if kind == "exchange":
        src_i = rng.randrange(3, 8)
        src = COIN_VALUES[src_i]
        # one denomination down keeps the coin count clickable (10 coins)
        dst = COIN_VALUES[src_i - 1]
        return Order(
            "exchange",
            [
                f"Swap my {coin_name(src)}",
                f"into {coin_name(dst)} coins,",
                "please!",
            ],
            target_total=src,
            only_coin=dst,
        )

    if kind == "quote":
        cost = rng.randrange(1, 20 + 30 * tier) * 100
        markup = rng.choice([10, 20, 25, 50])
        return Order(
            "quote",
            [
                f"Cost: {cost:,} lion.",
                f"Add {markup}% markup.",
                "Selling price?",
            ],
            answer=cost * (100 + markup) // 100,
            unit="lion",
        )

    price = rng.randrange(1, 20 + 30 * tier) * 100
    margin = rng.choice([10, 20, 25, 40, 50])
    profit = price * margin // 100
    return Order(
        "margin",
        [
            f"Sold {price:,}, cost {price - profit:,}.",
            "Profit margin on",
            "the price? (%)",
        ],
        answer=margin,
        unit="%",
    )


def tray_total(tray: dict) -> int:
    return sum(v * n for v, n in tray.items())


def check_order(order: Order, tray: dict, typed: str):
    """Return (correct, message)."""
    if order.uses_tray:
        total = tray_total(tray)
        wrong_coin = any(
            v != order.only_coin and n for v, n in tray.items())
        if order.only_coin and wrong_coin:
            return False, f"Only {coin_name(order.only_coin)} coins!"
        if total == order.target_total:
            return True, "Perfect!"
        return False, f"Needed {order.target_total:,}, got {total:,}"
    if typed.isdigit() and int(typed) == order.answer:
        return True, "Perfect!"
    return False, f"Answer was {order.answer:,}"
