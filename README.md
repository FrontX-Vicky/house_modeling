# House Modeling

Builder-ready 2D floor plans for the house, kept as editable JSON and rendered to SVG drawing sheets.

- Plot: **26'-0" wide × 82'-0" deep** (2,132 sq ft), **East-facing** (road on the East)
- Floors: **Ground Floor**, **First Floor** (Hall + Bedroom as one space, gallery over Padavi, cement-sheet roof over the rear)
- Construction: load-bearing 9" brick walls, external and internal

## Files

```
plans/ground_floor.json   # the plan: edit this
plans/first_floor.json
render.py                 # plans/*.json -> out/*.svg + out/index.html
out/                      # generated sheets, view out/index.html
```

## Render

```sh
python3 render.py
```

No dependencies, only Python 3. After editing a plan, run it again and refresh `out/index.html`.

The viewer opens on the ground floor. The **First Floor** switch in the top-right corner swaps in the first floor sheet; switch it off to go back. The choice is remembered in the browser.

## What the sheet shows

- Walls drawn at real thickness (hatched), with rooms as clear inside spaces
- Doors with swing, windows and ventilators, each tagged with a code (D1, W1, V1, O1)
- Dimension chains on all four sides, room by room, including every 9" wall
- Plot gap chains (front, rear, left, right), calculated from the building outline
- Kitchen platform, sink, Indian and western WC, basin, floor traps (a staircase can be drawn with `stairs`)
- Area statement, room schedule, door/window schedule with counts, notes and legend

## Coordinates

All values are in **feet** (use decimals: 9" = 0.75, 4½" = 0.375).
Origin `(0, 0)` is the **front-left corner of the plot** (road side, drawn at the bottom).
`x` goes right and `y` goes toward the rear.

Wall layout on the ground floor:

| Line | Position |
|------|----------|
| External walls | 9", outside face is the building outline |
| Internal walls | 9", centred on the original room lines (each room gave up 4½") |
| Padavi / Hall-Bedroom wall | y 39.375 – 40.125 |
| Hall / Bedroom wall | x 14.75 – 15.5 (Hall 11'-0", Bedroom 8'-9") |
| Hall-Bedroom / Kitchen wall | y 54.625 – 55.375 |
| Kitchen rear wall | y 63.625 – 64.375 (external for now; the Store will be built behind it later) |
| Kitchen / Bath-Toilet wall | y 58.25 – 59.0 (bathroom and toilet 6'-0" deep, passage 2'-10½") |

## Plan format

### Top level

| Key | Meaning |
|-----|---------|
| `name`, `subtitle` | Sheet title and the line under it |
| `plot` | `{ "width": 26, "depth": 82 }` |
| `front_side` | Compass direction the road side faces (`east`). Sets the north arrow and the side labels: bottom = East, top = West, right = North, left = South |
| `wall_thickness` | Default wall thickness in feet (0.75 = 9") |
| `visible` | `false` hides the floor in the viewer (it is still rendered to its SVG) |

### `building.outline`

Corner points of the **outside face of the external walls**, in order. The area inside is drawn as wall,
and the rooms are drawn on top of it, so whatever is not a room shows as wall. Built-up area and plot gaps
come from this outline.

### `building.covered`

Open areas under a slab with no walls (for example Padavi). Each one is `{ "name", "x", "y", "w", "h" }` or `points`.
They are drawn with a dashed slab edge, counted as covered area (not built-up enclosed, not carpet), and included in the plot-gap chains.

### `roofs`

Sheet roofs over single-storey parts, drawn with corrugation lines and a slope arrow.

```json
{ "name": "Cement sheet roof", "points": [[3,55.375],[25,55.375],...], "slope": "+y",
  "arrow_at": [8.75, 66], "label": "CEMENT ROOFING SHEETS\nover Kitchen, Bath, Toilet", "label_at": [8.75, 60.2] }
```

- `slope`: direction the roof falls (`+y` = toward the rear). Use `points` or `x, y, w, h`.
- `label` can have several lines separated by `\n`.

### `railings`

MS railings: `{ "points": [[x1, y1], [x2, y2], ...], "note" }`, drawn as a line with balusters.

### `columns`

RCC pillars, drawn solid: `{ "x", "y", "w", "h", "note" }`. Padavi has six 9"×9" pillars: 4 along the front and 2 at the back corners against the house.

### `rooms`

Clear inside spaces (wall face to wall face).

```json
{ "name": "Hall", "x": 3.75, "y": 40.375, "w": 11, "h": 14.25, "color": "#dce8f0" }
{ "name": "Kitchen", "points": [[3.75,55.375],[24.25,55.375],...], "dims_text": "11'-6\" × 8'-3\" + passage" }
```

- Use `x, y, w, h` for rectangles or `points` for L-shapes.
- `label_x`, `label_y`: optional label position.
- `dims_text`: optional size text instead of the automatic `W × D`.
- `show_dims: false`: label shows only the name and area (for small, crowded rooms). The size is still in the room schedule.
- `label_font`: optional `[name size, detail size]` in points, to shrink a label in a tight room.
- `area_text`: optional text instead of the automatic area line (for example `"107.25 + passage 20.25 = 127.5 sq ft"`).
- `parts`: optional named zones inside a room, listed under it in the room schedule. Each is `{ "name", "w", "h", "boundary": [[[x1, y1], [x2, y2]], ...] }`; the boundary lines are drawn dashed.
- `open: true`: the room is an open space (Padavi). It is listed in the room schedule but left out of carpet area.
- Carpet area is the sum of all enclosed room areas.

### `openings`

Placed on the **centre line of the wall**. `x, y` is where the opening starts, and `length` runs along the wall.

```json
{ "code": "D1", "type": "door", "x": 9.0, "y": 40, "length": 3.5, "orientation": "h", "swing": 1, "hinge": "start", "note": "Hall (main)" }
```

| Key | Meaning |
|-----|---------|
| `type` | `door`, `window`, `ventilator`, or `opening` (no shutter) |
| `orientation` | `h` = wall runs left-right, `v` = wall runs front-rear |
| `swing` | Doors only: `1` opens toward +y (or +x on a `v` wall), `-1` the other way |
| `hinge` | Doors only: `start` or `end` of the opening |
| `tag_side` | Side where the code tag goes (`1` / `-1`). Doors default to the side opposite the swing |
| `thickness` | Optional, defaults to `wall_thickness` |
| `note` | Location shown in the schedule |

### `schedule`

One entry per opening code. The sheet counts how many openings use each code and lists their locations.

```json
{ "code": "W1", "width": 4, "height": 4, "sill": 3, "spec": "Aluminium/UPVC sliding, MS safety grill" }
```

### `stairs`

```json
{ "flights":  [{ "x": 14.583, "y": 33.625, "w": 6.667, "h": 3, "treads": 8, "dir": "+x" }],
  "landings": [{ "x": 21.25, "y": 33.625, "w": 3, "h": 6 }],
  "arrow": [[14.8, 35.125], [22.75, 35.125]], "label": "UP", "label_at": [14.4, 34.85] }
```

### `fixtures`

| `type` | Fields |
|--------|--------|
| `counter`, `shelf` | `x, y, w, h` (or `points` for an L-shaped counter with `label_x`, `label_y`), optional `label`, `label_y` |
| `sink`, `basin` | `x, y, w, h` |
| `wc` | Western WC (EWC). `x, y, w, h`, `facing` = direction the bowl points (`-y`, `+y`, `-x`, `+x`); the cistern sits on the opposite side |
| `indian_wc` | Indian pan (IWC). `x, y, w, h`, `facing`: `-y` (footrests toward the front) or `+y` |
| `trap` | `x, y` (floor trap); `"label": false` hides the FT text |

### `dimensions`

Dimension chains. Each segment between two positions is labelled in feet-inches.

```json
{ "axis": "x", "at": 73, "pos": [3, 3.75, 15.25, 16], "from": 64.375 }
```

- `axis: "x"` is a horizontal chain drawn at `y = at`. `axis: "y"` is a vertical chain drawn at `x = at`.
- `from`: optional, where the extension lines start (one number, or one per position).
- Plot gap chains are added automatically, so don't add them by hand.

### `notes`

A list of strings, printed as numbered notes on the sheet.

## Ground floor decisions

- Inside walls are 9", taken out of the rooms.
- Overall house width is **22'-0"** outside the walls (x 3.0 – 25.0): left gap 3'-0", right gap 1'-0" (the right gap is never reduced). Hall is kept at 11'-0"; the Bedroom took the reduction.
- Padavi is open with no walls, 22'-0" × 10'-0" to the slab edge: an RCC slab on 6 pillars (4 front with 6'-4" clear bays, 2 at the back corners).
- Load-bearing masonry with RCC plinth and lintel bands; no columns.
- Dog-legged staircase inside Padavi against the north side: 3'-0" flights, 17 risers, arriving on the first-floor gallery.
- **Store (future phase):** removed from both floors for now. Its full definition (room, door, ventilator, shelves, outline, dimensions, roof) is saved in `plans/ground_floor.json` under `future.store`.
- The bathroom/toilet block sticks out 1'-0" past the kitchen's back wall. There is no building behind it.
- Plinth +1'-6", floor-to-floor 10'-0" and lintel 7'-0" are **assumed** until the engineer confirms them.

## First floor decisions

- Same plot coordinates as the ground floor. The enclosed room sits directly over the ground-floor Hall and Bedroom (y 39.375 – 55.375).
- Hall + Bedroom is one open space, 20'-6" × 14'-6".
- Gallery over Padavi: open, MS railing on front and sides, and the 6 pillars continue up to carry its roof (assumed).
- Kitchen, Bathroom and Toilet stay single storey under a lean-to cement-sheet roof sloping to the rear.

## Open items for the first floor

Decide these when the first floor is planned:

- **Staircase:** decided, inside Padavi, arriving on the gallery.
- **Hall + Bedroom space:** one open room for now; partitions, a toilet and terrace access are still to decide.
- **Floor heights:** confirm plinth, floor-to-floor and lintel levels with the engineer.
- **Load-bearing walls:** first-floor walls should sit on the ground-floor 9" walls below.
