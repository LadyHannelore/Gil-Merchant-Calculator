# Gil Merchant Calculator

## Lion Merchant (Python game)

An 8-bit shop game: customers walk in and you serve them using lion currency.

```
pip install pygame
python main.py
```

Order types:
- **Change**: customer pays with a big coin; click coins to build the exact change.
- **Exchange**: swap one coin for smaller coins of a requested type.
- **Quote**: cost plus markup % gives the selling price (type it).
- **Margin**: work out the profit margin % from price and cost.
- **Haggle**: customer offers less than you want. Accept (only if it covers cost + 15%), or type a counter. Too greedy and they counter back or walk away (3 rounds); accepting/countering below the minimum costs a life.

Controls: left/right click coins to add/remove, digits to type, Enter to serve/counter, `C` clears the tray. 3 mistakes ends the day.

Game rules live in `game_logic.py`; rendering is in `main.py`. The original web version is `index.html`.
